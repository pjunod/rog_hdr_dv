/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "mapper.h"
#include "native-input-formats.h"
#include "stream.h"
#include "gstdovipicture.h"
#include <gst/video/gstvideodovirpumeta.h>
#include <gst/base/gstbasetransform.h>
#define TYPE_GTK_DOVI_MAP (gtk_dovi_map_get_type ())
typedef struct { GstBaseTransform parent; GMutex lock; GstGtkDoviTarget target;
  guint64 target_serial; gboolean known_stream; GstVideoInfo info, output_info; GstGtkDoviMapper *mapper; } GtkDoviMap;
typedef struct { GstBaseTransformClass parent; } GtkDoviMapClass;
G_DEFINE_TYPE (GtkDoviMap, gtk_dovi_map, GST_TYPE_BASE_TRANSFORM)
/* Copy a caller-owned Structure natively into one immutable Context. Python
 * need not mutate a borrowed context structure; both instances receive the
 * exact same owned rendering context. */
static gboolean copy_field (GQuark field, const GValue *value, gpointer data)
{ gst_structure_id_set_value (data, field, value); return TRUE; }
static GstContext *create_target_context (GtkDoviMap *self, GstStructure *structure)
{
  (void) self;
  if (!structure || !gst_structure_has_name (structure, "gst.gtk.dovi.target.v1")) return NULL;
  gchar *witness = gst_structure_to_string (structure);
  GST_INFO_OBJECT (self, "surface rendering witness %s", witness);
  g_free (witness);
  GstContext *context = gst_context_new ("gst.gtk.dovi.target.v1", FALSE);
  gst_structure_foreach (structure, copy_field, gst_context_writable_structure (context));
  return context;
}
static void set_context (GstElement *element, GstContext *context)
{
  GtkDoviMap *s = (GtkDoviMap *) element;
  if (gst_context_has_context_type (context, "gst.gtk.dovi.target.v1")) {
    GstGtkDoviTarget target;
    gst_gtk_dovi_target_from_context (context, &target);
    g_mutex_lock (&s->lock); s->target = target; s->target_serial++; g_mutex_unlock (&s->lock);
  }
  GST_ELEMENT_CLASS (gtk_dovi_map_parent_class)->set_context (element, context);
}
static GstCaps *native_input_caps (void)
{
  GstCaps *caps = gst_caps_new_empty_simple ("video/x-raw");
  GValue formats = G_VALUE_INIT;
  g_value_init (&formats, GST_TYPE_LIST);
#define CAPS_FORMAT(gst, av) G_STMT_START { \
  GValue format = G_VALUE_INIT; \
  g_value_init (&format, G_TYPE_STRING); \
  g_value_set_static_string (&format, gst_video_format_to_string (GST_VIDEO_FORMAT_##gst)); \
  gst_value_list_append_value (&formats, &format); \
  g_value_unset (&format); \
} G_STMT_END;
  GTK_DOVI_NATIVE_INPUT_FORMATS (CAPS_FORMAT)
#undef CAPS_FORMAT
  gst_structure_set_value (gst_caps_get_structure (caps, 0), "format", &formats);
  g_value_unset (&formats);
  return caps;
}
static GstCaps *graded_output_caps (void)
{
  GstVideoColorimetry pq = {GST_VIDEO_COLOR_RANGE_0_255, GST_VIDEO_COLOR_MATRIX_RGB,
      GST_VIDEO_TRANSFER_SMPTE2084, GST_VIDEO_COLOR_PRIMARIES_BT2020};
  gchar *color = gst_video_colorimetry_to_string (&pq);
  GstCaps *caps = gst_caps_new_simple ("video/x-raw", "format", G_TYPE_STRING,
      "RGBA64_LE", "colorimetry", G_TYPE_STRING, color,
      "gtk-dovi-preconverted", G_TYPE_BOOLEAN, TRUE, NULL);
  g_free (color);
  return caps;
}
static GstCaps *transform_caps (GstBaseTransform *base, GstPadDirection direction,
    GstCaps *caps, GstCaps *filter)
{
  GstCaps *result = gst_caps_is_any (caps) ? gst_caps_copy (caps) : gst_caps_new_empty ();
  (void) base;
  for (guint i = 0; i < gst_caps_get_size (caps); i++) {
    const GstStructure *st = gst_caps_get_structure (caps, i);
    if (!gtk_dovi_stream_profile (st)) {
      gst_caps_append_structure_full (result, gst_structure_copy (st),
          gst_caps_features_copy (gst_caps_get_features (caps, i)));
      continue;
    }
    GstCaps *one = gst_caps_copy_nth (caps, i);
    GstCaps *constraint = direction == GST_PAD_SINK ? native_input_caps () : graded_output_caps ();
    GstCaps *allowed = gst_caps_intersect_full (one, constraint, GST_CAPS_INTERSECT_FIRST);
    gst_caps_unref (one);
    gst_caps_unref (constraint);
    for (guint j = 0; j < gst_caps_get_size (allowed); j++) {
      GstStructure *mapped = gst_caps_get_structure (allowed, j);
      gst_structure_remove_fields (mapped, "colorimetry", "format",
          "gtk-dovi-preconverted", "chroma-site", NULL);
    }
    constraint = direction == GST_PAD_SINK ? graded_output_caps () : native_input_caps ();
    one = gst_caps_intersect_full (allowed, constraint, GST_CAPS_INTERSECT_FIRST);
    gst_caps_unref (allowed);
    gst_caps_unref (constraint);
    gst_caps_append (result, one);
  }
  if (filter) {
    GstCaps *intersection = gst_caps_intersect_full (filter, result, GST_CAPS_INTERSECT_FIRST);
    gst_caps_unref (result); result = intersection;
  }
  return result;
}
static gboolean set_caps (GstBaseTransform *base, GstCaps *input, GstCaps *output)
{
  GtkDoviMap *s = (GtkDoviMap *) base;
  guint profile = 0;
  for (guint i = 0; i < gst_caps_get_size (input) && !profile; i++)
    profile = gtk_dovi_stream_profile (gst_caps_get_structure (input, i));
  gboolean known = profile != 0;
  if (known) {
    if (!gst_caps_is_fixed (input) || !gst_caps_is_fixed (output) ||
        gst_caps_get_size (input) != 1 || gst_caps_get_size (output) != 1 ||
        !gst_caps_features_is_equal (gst_caps_get_features (input, 0),
            GST_CAPS_FEATURES_MEMORY_SYSTEM_MEMORY) ||
        !gst_caps_features_is_equal (gst_caps_get_features (output, 0),
            GST_CAPS_FEATURES_MEMORY_SYSTEM_MEMORY))
      return FALSE;
    GstCaps *allowed = native_input_caps ();
    gboolean supported = gst_caps_is_subset (input, allowed);
    gst_caps_unref (allowed);
    if (!supported) return FALSE;
    /* Derive the final output from the same forward contract: identity fields
     * and authoritative stream configuration cannot silently change here. */
    allowed = transform_caps (base, GST_PAD_SINK, input, NULL);
    supported = gst_caps_is_subset (output, allowed);
    gst_caps_unref (allowed);
    if (!supported) return FALSE;
    GstVideoInfo info, output_info;
    if (!gst_video_info_from_caps (&info, input) ||
        !gst_video_info_from_caps (&output_info, output) ||
        GST_VIDEO_INFO_WIDTH (&info) != GST_VIDEO_INFO_WIDTH (&output_info) ||
        GST_VIDEO_INFO_HEIGHT (&info) != GST_VIDEO_INFO_HEIGHT (&output_info) ||
        GST_VIDEO_INFO_FORMAT (&output_info) != GST_VIDEO_FORMAT_RGBA64_LE ||
        output_info.colorimetry.transfer != GST_VIDEO_TRANSFER_SMPTE2084 ||
        output_info.colorimetry.primaries != GST_VIDEO_COLOR_PRIMARIES_BT2020 ||
        output_info.colorimetry.matrix != GST_VIDEO_COLOR_MATRIX_RGB ||
        output_info.colorimetry.range != GST_VIDEO_COLOR_RANGE_0_255)
      return FALSE;
    s->info = info;
    s->output_info = output_info;
  } else if (!gst_caps_is_equal (input, output)) return FALSE;
  if (s->known_stream != known) {
    s->known_stream = known;
    gst_element_post_message (GST_ELEMENT (s), gst_message_new_element (GST_OBJECT (s),
        gst_structure_new ("gtk-dovi-stream-selected", "dolby", G_TYPE_BOOLEAN, known,
            "profile", G_TYPE_UINT, profile, NULL)));
  }
  return TRUE;
}
static gboolean stop (GstBaseTransform *base)
{
  GtkDoviMap *s = (GtkDoviMap *) base;
  if (s->known_stream) {
    s->known_stream = FALSE;
    gst_element_post_message (GST_ELEMENT (s), gst_message_new_element (GST_OBJECT (s),
        gst_structure_new ("gtk-dovi-stream-selected", "dolby", G_TYPE_BOOLEAN, FALSE,
            "profile", G_TYPE_UINT, 0, NULL)));
  }
  return TRUE;
}
static GstFlowReturn prepare (GstBaseTransform *base, GstBuffer *input, GstBuffer **output)
{
  GtkDoviMap *s = (GtkDoviMap *) base;
  GstGtkDoviTarget target; guint64 serial;
  g_mutex_lock (&s->lock); target = s->target; serial = s->target_serial; g_mutex_unlock (&s->lock);
  if (!s->known_stream || gst_buffer_n_memory (input) == 0) { *output = gst_buffer_ref (input); return GST_FLOW_OK; }
  /* Before the composition/HDR witness is ready, re-encode the ordinary
   * baseline. Private mapping requires both witnesses inside the shared core. */
  GstVideoInfo result_info = s->output_info;
  GError *error = NULL;
  int result = gst_gtk_dovi_mapper_render (s->mapper, input, &s->info,
      &target, output, &result_info, &error);
  if (result < 1 || !*output) {
    GST_ELEMENT_ERROR (s, STREAM, FAILED, ("%s", error ? error->message : "Dolby map failed"), (NULL));
    g_clear_error (&error); return GST_FLOW_ERROR;
  }
  g_mutex_lock (&s->lock);
  gboolean current = serial == s->target_serial;
  g_mutex_unlock (&s->lock);
  if (result && !current) {
    gst_clear_buffer (output); return GST_BASE_TRANSFORM_FLOW_DROPPED;
  }
  guint64 epoch = 0, picture_id = 0;
  GstDoviPictureMeta *meta = gst_buffer_get_dovi_picture_meta (input);
  if (meta && meta->picture) gst_dovi_picture_get_identity (meta->picture, &epoch, &picture_id);
  GST_LOG_OBJECT (s, "result=%s pts=%" GST_TIME_FORMAT " epoch=%" G_GUINT64_FORMAT
      " picture=%" G_GUINT64_FORMAT " target-generation=%" G_GUINT64_FORMAT
      " physical=%.9g..%.9g reference=%.9g native-hdr-ready=%d output=RGBA64_LE",
      result == 1 ? "mapped" : "baseline-reencoded", GST_TIME_ARGS (GST_BUFFER_PTS (input)),
      epoch, picture_id, target.generation, target.min_nits, target.max_nits,
      target.reference_nits, target.render_ready);
  if (!gst_gtk_dovi_native_frame_attach (*output, input, &s->info, &result_info, target.generation)) {
    gst_clear_buffer (output); return GST_FLOW_ERROR;
  }
  GstBaseTransformClass *klass = GST_BASE_TRANSFORM_GET_CLASS (base);
  if (!klass->copy_metadata (base, input, *output)) {
    gst_clear_buffer (output); return GST_FLOW_ERROR;
  }
  return GST_FLOW_OK;
}
static GstFlowReturn transform (GstBaseTransform *s, GstBuffer *in, GstBuffer *out)
{ (void) s; (void) in; (void) out; return GST_FLOW_OK; }
static gboolean transform_meta (GstBaseTransform *base, GstBuffer *out,
    GstMeta *meta, GstBuffer *in)
{
  if (meta->info->api == GST_DOVI_PICTURE_META_API_TYPE ||
      meta->info->api == GST_VIDEO_DOVI_RPU_META_API_TYPE ||
      meta->info->api == GST_VIDEO_META_API_TYPE) return FALSE;
  if (meta->info->api == GST_VIDEO_CROP_META_API_TYPE) return FALSE; /* materialized active output */
  if (meta->info->api == GST_VIDEO_OVERLAY_COMPOSITION_META_API_TYPE) {
    GstVideoOverlayCompositionMeta *overlay = (GstVideoOverlayCompositionMeta *) meta;
    gst_buffer_add_video_overlay_composition_meta (out, overlay->overlay);
    return FALSE;
  }
  return GST_BASE_TRANSFORM_CLASS (gtk_dovi_map_parent_class)->transform_meta (base, out, meta, in);
}
static void finalize (GObject *object)
{
  GtkDoviMap *s = (GtkDoviMap *) object;
  gst_gtk_dovi_mapper_free (s->mapper); g_mutex_clear (&s->lock);
  G_OBJECT_CLASS (gtk_dovi_map_parent_class)->finalize (object);
}
static void gtk_dovi_map_class_init (GtkDoviMapClass *klass)
{
  GstElementClass *element = GST_ELEMENT_CLASS (klass);
  GstBaseTransformClass *base = GST_BASE_TRANSFORM_CLASS (klass);
  G_OBJECT_CLASS (klass)->finalize = finalize;
  element->set_context = set_context;
  g_signal_new_class_handler ("create-target-context", G_TYPE_FROM_CLASS (klass),
      G_SIGNAL_RUN_LAST | G_SIGNAL_ACTION, G_CALLBACK (create_target_context),
      NULL, NULL, NULL, GST_TYPE_CONTEXT, 1, GST_TYPE_STRUCTURE);
  gst_element_class_set_static_metadata (element, "GTK surface Dolby pre-conversion",
      "Filter/Video", "Maps resolved native pictures before ordinary color conversion", "ROG HDR contributors");
  GstCaps *caps = gst_caps_from_string ("video/x-raw(ANY)");
  gst_element_class_add_pad_template (element, gst_pad_template_new ("sink", GST_PAD_SINK, GST_PAD_ALWAYS, caps));
  gst_element_class_add_pad_template (element, gst_pad_template_new ("src", GST_PAD_SRC, GST_PAD_ALWAYS, caps));
  gst_caps_unref (caps);
  base->stop = stop; base->set_caps = set_caps; base->transform_caps = transform_caps; base->prepare_output_buffer = prepare;
  base->transform = transform; base->transform_meta = transform_meta;
  base->passthrough_on_same_caps = FALSE;
}
static void gtk_dovi_map_init (GtkDoviMap *s)
{
  g_mutex_init (&s->lock); s->mapper = gst_gtk_dovi_mapper_new ();
  gst_base_transform_set_in_place (GST_BASE_TRANSFORM (s), FALSE);
}
static gboolean plugin_init (GstPlugin *plugin)
{
  if (gst_gtk_dovi_core_abi () != GST_GTK_DOVI_CORE_ABI) return FALSE;
  gst_gtk_dovi_debug_init ();
  return gst_element_register (plugin, "gtkdovimap", GST_RANK_NONE, TYPE_GTK_DOVI_MAP);
}
#ifndef PACKAGE
#define PACKAGE "gtk-dovi-map"
#endif
GST_PLUGIN_DEFINE (GST_VERSION_MAJOR, GST_VERSION_MINOR, gtkdovimap,
    "GTK surface Dolby pre-conversion", plugin_init, "1.0", "LGPL", PACKAGE, "https://example.invalid")
