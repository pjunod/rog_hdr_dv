/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "mapper.h"
#include "source-lease-private.h"
#include "native-input-formats.h"
#include "stream.h"
#include "gstdovipicture.h"
#include <gst/video/gstvideodovirpumeta.h>
#include <gst/base/gstbasetransform.h>
#define TYPE_GTK_DOVI_MAP (gtk_dovi_map_get_type ())
typedef struct { GstBaseTransform parent; GMutex lock; GstGtkDoviTarget target;
  guint64 target_serial, source_revision, source_selection_serial;
  guint destination_kind;
  gboolean require_clear_source, source_blocked;
  gchar *stream_id;
  GHashTable *clear_sources;
  GstGtkDoviSourceLease *source_lease;
  gboolean known_stream; GstVideoInfo info, output_info; GstGtkDoviMapper *mapper; } GtkDoviMap;
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
/* Source proof belongs to one original demuxer stream and one monotonically
 * increasing browser load revision. A late callback cannot reopen a revoked
 * CDM/source revision. Existing GTK clients do not opt into this policy. */
static void revoke_source_locked (GtkDoviMap *s)
{
  gst_gtk_dovi_source_lease_revoke (s->source_lease);
  gst_gtk_dovi_source_lease_unref (s->source_lease);
  s->source_lease = NULL; s->target_serial++;
}
static void select_source_locked (GtkDoviMap *s)
{
  GstCaps *coded = s->stream_id ? g_hash_table_lookup (s->clear_sources, s->stream_id) : NULL;
  if (!s->source_blocked && coded && gst_gtk_dovi_source_lease_matches (
          s->source_lease, s->stream_id, coded)) return;
  revoke_source_locked (s);
  if (!s->source_blocked && coded && s->source_selection_serial != G_MAXUINT64)
    s->source_lease = _gst_gtk_dovi_source_lease_new_selected (coded, s->stream_id,
        s->source_revision, ++s->source_selection_serial);
}
typedef struct { guint64 revision, selection; } SourceSelection;
static SourceSelection source_selection_locked (GtkDoviMap *s)
{
  SourceSelection state = {s->source_revision,
      _gst_gtk_dovi_source_lease_selection (s->source_lease)};
  return state;
}
static void emit_selection_change (GtkDoviMap *s, SourceSelection old, SourceSelection current)
{
  if (old.revision == current.revision && old.selection == current.selection) return;
  if (old.selection)
    g_signal_emit_by_name (s, "source-selection-revoked", old.revision, old.selection);
  if (current.selection)
    g_signal_emit_by_name (s, "source-selection-activated", current.revision, current.selection);
}
static gboolean qualified_structure (GtkDoviMap *s, const GstStructure *st)
{
  if (!gtk_dovi_stream_profile (st)) return FALSE;
  if (!s->require_clear_source) return TRUE;
  GstCaps *caps = gst_caps_new_empty ();
  gst_caps_append_structure (caps, gst_structure_copy (st));
  g_mutex_lock (&s->lock);
  gboolean qualified = !s->source_blocked && gst_gtk_dovi_source_lease_matches (
      s->source_lease, s->stream_id, caps);
  g_mutex_unlock (&s->lock);
  gst_caps_unref (caps); return qualified;
}
static void update_source_context (GtkDoviMap *s, const GstStructure *st)
{
  guint64 revision = 0;
  gboolean blocked = FALSE;
  if (!gst_structure_get_uint64 (st, "source-revision", &revision) || !revision) return;
  gst_structure_get_boolean (st, "blocked", &blocked);
  const gchar *id = gst_structure_get_string (st, "stream-id");
  const GValue *value = gst_structure_get_value (st, "clear-coded-caps");
  const GstCaps *coded = value && GST_VALUE_HOLDS_CAPS (value) ? gst_value_get_caps (value) : NULL;
  GstGtkDoviSourceLease *proof = coded ? gst_gtk_dovi_source_lease_new (coded, id, revision) : NULL;
  g_mutex_lock (&s->lock);
  SourceSelection old = source_selection_locked (s);
  if (revision >= s->source_revision) {
    if (revision > s->source_revision) {
      revoke_source_locked (s); g_hash_table_remove_all (s->clear_sources);
      g_clear_pointer (&s->stream_id, g_free);
      s->source_revision = revision; s->source_blocked = FALSE;
    }
    if (blocked) {
      s->source_blocked = TRUE;
      revoke_source_locked (s); g_hash_table_remove_all (s->clear_sources);
    } else if (!s->source_blocked && id && *id) {
      if (proof) g_hash_table_replace (s->clear_sources, g_strdup (id), gst_caps_ref ((GstCaps *) coded));
      else g_hash_table_remove (s->clear_sources, id);
      if (!g_strcmp0 (id, s->stream_id)) select_source_locked (s);
    }
  }
  SourceSelection current = source_selection_locked (s);
  g_mutex_unlock (&s->lock);
  gst_gtk_dovi_source_lease_unref (proof);
  emit_selection_change (s, old, current);
  gst_base_transform_reconfigure_sink (GST_BASE_TRANSFORM (s));
  gst_base_transform_reconfigure_src (GST_BASE_TRANSFORM (s));
}
static void set_context (GstElement *element, GstContext *context)
{
  GtkDoviMap *s = (GtkDoviMap *) element;
  if (gst_context_has_context_type (context, "gst.gtk.dovi.target.v1")) {
    GstGtkDoviTarget target;
    gst_gtk_dovi_target_from_context (context, &target);
    g_mutex_lock (&s->lock); s->target = target; s->target_serial++; g_mutex_unlock (&s->lock);
  }
  if (s->require_clear_source && gst_context_has_context_type (context, "gst.webkit.dovi.source.v1"))
    update_source_context (s, gst_context_get_structure (context));
  GST_ELEMENT_CLASS (gtk_dovi_map_parent_class)->set_context (element, context);
}
static GstCaps *native_format_caps (gboolean accelerator_only)
{
  GstCaps *caps = gst_caps_new_empty_simple ("video/x-raw");
  GValue formats = G_VALUE_INIT;
  g_value_init (&formats, GST_TYPE_LIST);
#define CAPS_FORMAT(gst, av, accelerator) G_STMT_START { \
  if (!accelerator_only || accelerator) { \
    GValue format = G_VALUE_INIT; \
    g_value_init (&format, G_TYPE_STRING); \
    g_value_set_static_string (&format, gst_video_format_to_string (GST_VIDEO_FORMAT_##gst)); \
    gst_value_list_append_value (&formats, &format); \
    g_value_unset (&format); \
  } \
} G_STMT_END;
  GTK_DOVI_NATIVE_INPUT_FORMATS (CAPS_FORMAT)
#undef CAPS_FORMAT
  gst_structure_set_value (gst_caps_get_structure (caps, 0), "format", &formats);
  g_value_unset (&formats);
  return caps;
}
static GstCaps *native_input_caps (void)
{
  GstCaps *caps = native_format_caps (FALSE);
  const gchar *features[] = {GTK_DOVI_CUDA_MEMORY_FEATURE,
      GTK_DOVI_VA_MEMORY_FEATURE};
  for (guint i = 0; i < G_N_ELEMENTS (features); i++) {
    GstCaps *accelerator = native_format_caps (TRUE);
    gst_caps_set_features (accelerator, 0,
        gst_caps_features_new (features[i], NULL));
    gst_caps_append (caps, accelerator);
  }
  return caps;
}
static gboolean native_input_memory (const GstCapsFeatures *features)
{
  return gst_caps_features_is_equal (features, GST_CAPS_FEATURES_MEMORY_SYSTEM_MEMORY) ||
      (gst_caps_features_get_size (features) == 1 &&
      (gst_caps_features_contains (features, GTK_DOVI_CUDA_MEMORY_FEATURE) ||
       gst_caps_features_contains (features, GTK_DOVI_VA_MEMORY_FEATURE)));
}
static GstCaps *graded_output_caps (GtkDoviMap *self)
{
  GstVideoColorimetry pq = {GST_VIDEO_COLOR_RANGE_0_255, GST_VIDEO_COLOR_MATRIX_RGB,
      GST_VIDEO_TRANSFER_SMPTE2084, GST_VIDEO_COLOR_PRIMARIES_BT2020};
  gboolean sdr = self->destination_kind == GST_GTK_DOVI_DESTINATION_STANDARD_SDR_SRGB;
  if (sdr) {
    pq.transfer = GST_VIDEO_TRANSFER_SRGB;
    pq.primaries = GST_VIDEO_COLOR_PRIMARIES_BT709;
  }
  gchar *color = gst_video_colorimetry_to_string (&pq);
  GstCaps *caps = gst_caps_new_simple ("video/x-raw", "format", G_TYPE_STRING,
      sdr ? "RGBA" : "RGBA64_LE", "colorimetry", G_TYPE_STRING, color,
      "gtk-dovi-preconverted", G_TYPE_BOOLEAN, TRUE, NULL);
  g_free (color);
  return caps;
}
static GstCaps *transform_caps (GstBaseTransform *base, GstPadDirection direction,
    GstCaps *caps, GstCaps *filter);

/* A peer can normalize away stream-only fields from a filtered output answer.
 * Invert each marked input candidate through its own real graded output before
 * intersecting it with the peer. An unmarked identity answer must never acquire
 * a Dolby marker merely because the caller supplied a marked input filter. */
static GstCaps *marked_filter_preimage (GstBaseTransform *base,
    GstCaps *peer_output, GstCaps *filter)
{
  GstCaps *result = gst_caps_new_empty ();
  GstCaps *identity = NULL;
  for (guint i = 0; i < gst_caps_get_size (filter); i++) {
    GstCaps *input = gst_caps_copy_nth (filter, i);
    if (!qualified_structure ((GtkDoviMap *) base, gst_caps_get_structure (input, 0))) {
      if (!identity)
        identity = transform_caps (base, GST_PAD_SRC, peer_output, NULL);
      GstCaps *plain = gst_caps_intersect_full (input, identity,
          GST_CAPS_INTERSECT_FIRST);
      gst_caps_append (result, plain);
    } else {
      GstCaps *native = native_input_caps ();
      GstCaps *allowed = gst_caps_intersect_full (input, native,
          GST_CAPS_INTERSECT_FIRST);
      GstCaps *graded = transform_caps (base, GST_PAD_SINK, allowed, NULL);
      GstCaps *actual = gst_caps_intersect_full (graded, peer_output,
          GST_CAPS_INTERSECT_FIRST);
      GstCaps *reverse = transform_caps (base, GST_PAD_SRC, actual, NULL);
      GstCaps *accepted = gst_caps_intersect_full (allowed, reverse,
          GST_CAPS_INTERSECT_FIRST);
      gst_caps_append (result, accepted);
      gst_caps_unref (reverse);
      gst_caps_unref (actual);
      gst_caps_unref (graded);
      gst_caps_unref (allowed);
      gst_caps_unref (native);
    }
    gst_caps_unref (input);
  }
  gst_clear_caps (&identity);
  return result;
}
static GstCaps *transform_caps (GstBaseTransform *base, GstPadDirection direction,
    GstCaps *caps, GstCaps *filter)
{
  if (direction == GST_PAD_SRC && filter) {
    for (guint i = 0; i < gst_caps_get_size (filter); i++) {
      if (qualified_structure ((GtkDoviMap *) base, gst_caps_get_structure (filter, i)))
        return marked_filter_preimage (base, caps, filter);
    }
  }
  GstCaps *result = gst_caps_is_any (caps) ? gst_caps_copy (caps) : gst_caps_new_empty ();
  GtkDoviMap *self = (GtkDoviMap *) base;
  for (guint i = 0; i < gst_caps_get_size (caps); i++) {
    const GstStructure *st = gst_caps_get_structure (caps, i);
    if (!qualified_structure (self, st)) {
      gst_caps_append_structure_full (result, gst_structure_copy (st),
          gst_caps_features_copy (gst_caps_get_features (caps, i)));
      continue;
    }
    GstCaps *one = gst_caps_copy_nth (caps, i);
    GstCaps *constraint = direction == GST_PAD_SINK ? native_input_caps () : graded_output_caps (self);
    GstCaps *allowed = gst_caps_intersect_full (one, constraint, GST_CAPS_INTERSECT_FIRST);
    gst_caps_unref (one);
    gst_caps_unref (constraint);
    for (guint j = 0; j < gst_caps_get_size (allowed); j++) {
      GstStructure *mapped = gst_caps_get_structure (allowed, j);
      gst_structure_remove_fields (mapped, "colorimetry", "format",
          "gtk-dovi-preconverted", "chroma-site", NULL);
      /* Import may read concrete accelerator allocations, but mapped output
       * is newly allocated system memory. Reverse queries expose only the
       * explicitly listed host-mappable input domains, never arbitrary memory. */
      gst_caps_set_features (allowed, j, direction == GST_PAD_SINK ?
          gst_caps_features_new_empty () : gst_caps_features_new_any ());
    }
    constraint = direction == GST_PAD_SINK ? graded_output_caps (self) : native_input_caps ();
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
  gboolean sdr = s->destination_kind == GST_GTK_DOVI_DESTINATION_STANDARD_SDR_SRGB;
  if (s->require_clear_source) {
    g_mutex_lock (&s->lock);
    SourceSelection old = source_selection_locked (s);
    if (!s->stream_id) {
      GstEvent *start = gst_pad_get_sticky_event (GST_BASE_TRANSFORM_SINK_PAD (base), GST_EVENT_STREAM_START, 0);
      if (start) {
        const gchar *id = NULL; gst_event_parse_stream_start (start, &id);
        s->stream_id = g_strdup (id); gst_event_unref (start);
        select_source_locked (s);
      }
    }
    SourceSelection current = source_selection_locked (s);
    g_mutex_unlock (&s->lock);
    emit_selection_change (s, old, current);
  }
  guint profile = 0;
  for (guint i = 0; i < gst_caps_get_size (input) && !profile; i++)
    if (qualified_structure (s, gst_caps_get_structure (input, i)))
      profile = gtk_dovi_stream_profile (gst_caps_get_structure (input, i));
  gboolean known = profile != 0;
  if (known) {
    if (!gst_caps_is_fixed (input) || !gst_caps_is_fixed (output) ||
        gst_caps_get_size (input) != 1 || gst_caps_get_size (output) != 1 ||
        !native_input_memory (gst_caps_get_features (input, 0)) ||
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
        GST_VIDEO_INFO_FORMAT (&output_info) != (sdr ? GST_VIDEO_FORMAT_RGBA : GST_VIDEO_FORMAT_RGBA64_LE) ||
        output_info.colorimetry.transfer != (sdr ? GST_VIDEO_TRANSFER_SRGB : GST_VIDEO_TRANSFER_SMPTE2084) ||
        output_info.colorimetry.primaries != (sdr ? GST_VIDEO_COLOR_PRIMARIES_BT709 : GST_VIDEO_COLOR_PRIMARIES_BT2020) ||
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
static gboolean sink_event (GstBaseTransform *base, GstEvent *event)
{
  GtkDoviMap *s = (GtkDoviMap *) base;
  if (s->require_clear_source) {
    g_mutex_lock (&s->lock);
    SourceSelection old = source_selection_locked (s);
    switch (GST_EVENT_TYPE (event)) {
    case GST_EVENT_STREAM_START: {
      const gchar *id = NULL; gst_event_parse_stream_start (event, &id);
      revoke_source_locked (s);
      g_free (s->stream_id); s->stream_id = g_strdup (id);
      select_source_locked (s); break;
    }
    case GST_EVENT_FLUSH_START:
      revoke_source_locked (s); break;
    case GST_EVENT_FLUSH_STOP: {
      GstEvent *start = gst_pad_get_sticky_event (GST_BASE_TRANSFORM_SINK_PAD (base), GST_EVENT_STREAM_START, 0);
      if (start) {
        const gchar *id = NULL; gst_event_parse_stream_start (start, &id);
        g_free (s->stream_id); s->stream_id = g_strdup (id);
        gst_event_unref (start);
      }
      select_source_locked (s); break;
    }
    default: break;
    }
    SourceSelection current = source_selection_locked (s);
    g_mutex_unlock (&s->lock);
    emit_selection_change (s, old, current);
    if (GST_EVENT_TYPE (event) == GST_EVENT_STREAM_START || GST_EVENT_TYPE (event) == GST_EVENT_FLUSH_STOP) {
      gst_base_transform_reconfigure_sink (base); gst_base_transform_reconfigure_src (base);
    }
  }
  return GST_BASE_TRANSFORM_CLASS (gtk_dovi_map_parent_class)->sink_event (base, event);
}
static gboolean stop (GstBaseTransform *base)
{
  GtkDoviMap *s = (GtkDoviMap *) base;
  g_mutex_lock (&s->lock);
  SourceSelection old = source_selection_locked (s);
  revoke_source_locked (s); g_hash_table_remove_all (s->clear_sources);
  g_clear_pointer (&s->stream_id, g_free);
  SourceSelection current = source_selection_locked (s);
  g_mutex_unlock (&s->lock);
  emit_selection_change (s, old, current);
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
  g_mutex_lock (&s->lock); target = s->target; serial = s->target_serial;
  GstGtkDoviSourceLease *lease = gst_gtk_dovi_source_lease_ref (s->source_lease);
  gboolean require_clear = s->require_clear_source;
  g_mutex_unlock (&s->lock);
  *output = NULL;
  gboolean live = gst_gtk_dovi_source_lease_is_valid (lease);
  gboolean marked = FALSE, matching = FALSE;
  if (require_clear && (live || s->known_stream)) {
    GstCaps *caps = gst_pad_get_current_caps (GST_BASE_TRANSFORM_SINK_PAD (base));
    if (caps && gst_caps_get_size (caps) == 1) {
      marked = gtk_dovi_stream_profile (gst_caps_get_structure (caps, 0)) != 0;
      g_mutex_lock (&s->lock);
      matching = lease == s->source_lease && gst_gtk_dovi_source_lease_matches (
          lease, s->stream_id, caps);
      g_mutex_unlock (&s->lock);
    }
    gst_clear_caps (&caps);
  }
  /* STREAM_START can qualify a new lease while the previous identity caps
   * are still current. A marked raw picture must wait for graded set_caps;
   * an established graded contract must also match the exact live lease. */
  if (require_clear && ((!s->known_stream && live && marked) ||
          (s->known_stream && (!live || !matching)))) {
    gst_gtk_dovi_source_lease_unref (lease); return GST_BASE_TRANSFORM_FLOW_DROPPED;
  }
  if (!s->known_stream || gst_buffer_n_memory (input) == 0) {
    gst_gtk_dovi_source_lease_unref (lease); *output = gst_buffer_ref (input); return GST_FLOW_OK;
  }
  /* Before the composition/HDR witness is ready, re-encode the ordinary
   * baseline. Private mapping requires both witnesses inside the shared core. */
  GstVideoInfo result_info = s->output_info;
  GError *error = NULL;
  int result = gst_gtk_dovi_mapper_render_destination (s->mapper, input, &s->info,
      s->destination_kind, &target, output, &result_info, &error);
  if (result < 1 || !*output) {
    GST_ELEMENT_ERROR (s, STREAM, FAILED, ("%s", error ? error->message : "Dolby map failed"), (NULL));
    g_clear_error (&error); gst_gtk_dovi_source_lease_unref (lease); return GST_FLOW_ERROR;
  }
  g_mutex_lock (&s->lock);
  gboolean current = serial == s->target_serial;
  g_mutex_unlock (&s->lock);
  if (result && (!current || (require_clear && !gst_gtk_dovi_source_lease_is_valid (lease)))) {
    gst_clear_buffer (output); gst_gtk_dovi_source_lease_unref (lease); return GST_BASE_TRANSFORM_FLOW_DROPPED;
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
  gboolean attached = gst_gtk_dovi_native_frame_attach_source (*output, input,
      &s->info, &result_info, target.generation, require_clear ? lease : NULL);
  gboolean revoked = require_clear && !gst_gtk_dovi_source_lease_is_valid (lease);
  gst_gtk_dovi_source_lease_unref (lease);
  if (!attached) {
    gst_clear_buffer (output);
    return revoked ? GST_BASE_TRANSFORM_FLOW_DROPPED : GST_FLOW_ERROR;
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
  gst_gtk_dovi_source_lease_revoke (s->source_lease);
  gst_gtk_dovi_source_lease_unref (s->source_lease);
  g_hash_table_unref (s->clear_sources); g_free (s->stream_id);
  gst_gtk_dovi_mapper_free (s->mapper); g_mutex_clear (&s->lock);
  G_OBJECT_CLASS (gtk_dovi_map_parent_class)->finalize (object);
}
static void set_property (GObject *object, guint property,
    const GValue *value, GParamSpec *spec)
{
  GtkDoviMap *self = (GtkDoviMap *) object;
  if (property != 1 && property != 3) {
    G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property, spec); return;
  }
  GST_STATE_LOCK (self);
  if (GST_STATE (self) <= GST_STATE_READY) {
    if (property == 3) self->require_clear_source = g_value_get_boolean (value);
    else self->destination_kind = g_value_get_uint (value);
  }
  else
    GST_WARNING_OBJECT (self, "Destination can only change before PAUSED");
  GST_STATE_UNLOCK (self);
}
static void get_property (GObject *object, guint property,
    GValue *value, GParamSpec *spec)
{
  GtkDoviMap *self = (GtkDoviMap *) object;
  if (property == 5 || property == 6) {
    g_mutex_lock (&self->lock);
    SourceSelection state = source_selection_locked (self);
    g_value_set_uint64 (value, property == 5 ? state.revision : state.selection);
    g_mutex_unlock (&self->lock); return;
  }
  if (property == 3) { g_value_set_boolean (value, self->require_clear_source); return; }
  if (property == 4) { g_value_set_uint (value, GST_GTK_DOVI_SOURCE_LEASE_ABI); return; }
  if (property == 2) {
    g_value_set_uint (value, GST_GTK_DOVI_DESTINATION_ABI); return;
  }
  if (property != 1) {
    G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property, spec); return;
  }
  g_value_set_uint (value, self->destination_kind);
}
static void gtk_dovi_map_class_init (GtkDoviMapClass *klass)
{
  GstElementClass *element = GST_ELEMENT_CLASS (klass);
  GstBaseTransformClass *base = GST_BASE_TRANSFORM_CLASS (klass);
  G_OBJECT_CLASS (klass)->finalize = finalize;
  G_OBJECT_CLASS (klass)->set_property = set_property;
  G_OBJECT_CLASS (klass)->get_property = get_property;
  g_object_class_install_property (G_OBJECT_CLASS (klass), 1,
      g_param_spec_uint ("destination-kind", "Destination kind",
        "0: witnessed native display PQ;1: logical100nit BT709 standard SDR sRGB",
        0, 1, 0, G_PARAM_READWRITE | GST_PARAM_MUTABLE_READY | G_PARAM_STATIC_STRINGS));
  g_object_class_install_property (G_OBJECT_CLASS (klass), 2,
      g_param_spec_uint ("destination-abi", "Destination ABI",
        "Explicit destination-kind contract version",
        GST_GTK_DOVI_DESTINATION_ABI, GST_GTK_DOVI_DESTINATION_ABI,
        GST_GTK_DOVI_DESTINATION_ABI, G_PARAM_READABLE | G_PARAM_STATIC_STRINGS));
  g_object_class_install_property (G_OBJECT_CLASS (klass), 3,
      g_param_spec_boolean ("require-clear-source", "Require clear coded source",
        "Browser source/id/configuration qualification before grading or retention",
        FALSE, G_PARAM_READWRITE | GST_PARAM_MUTABLE_READY | G_PARAM_STATIC_STRINGS));
  g_object_class_install_property (G_OBJECT_CLASS (klass), 4,
      g_param_spec_uint ("source-policy-abi", "Source policy ABI",
        "Revision-fenced selected clear source contract", 2, 2, 2,
        G_PARAM_READABLE | G_PARAM_STATIC_STRINGS));
  g_object_class_install_property (G_OBJECT_CLASS (klass), 5,
      g_param_spec_uint64 ("active-source-revision", "Active source revision",
        "Current origin source revision", 0, G_MAXUINT64, 0, G_PARAM_READABLE | G_PARAM_STATIC_STRINGS));
  g_object_class_install_property (G_OBJECT_CLASS (klass), 6,
      g_param_spec_uint64 ("active-source-selection", "Active source selection",
        "Current live selected lease serial, zero when revoked", 0, G_MAXUINT64, 0,
        G_PARAM_READABLE | G_PARAM_STATIC_STRINGS));
  g_signal_new ("source-selection-revoked", G_TYPE_FROM_CLASS (klass), G_SIGNAL_RUN_LAST,
      0, NULL, NULL, NULL, G_TYPE_NONE, 2, G_TYPE_UINT64, G_TYPE_UINT64);
  g_signal_new ("source-selection-activated", G_TYPE_FROM_CLASS (klass), G_SIGNAL_RUN_LAST,
      0, NULL, NULL, NULL, G_TYPE_NONE, 2, G_TYPE_UINT64, G_TYPE_UINT64);
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
  base->sink_event = sink_event; base->stop = stop; base->set_caps = set_caps; base->transform_caps = transform_caps; base->prepare_output_buffer = prepare;
  base->transform = transform; base->transform_meta = transform_meta;
  base->passthrough_on_same_caps = FALSE;
}
static void gtk_dovi_map_init (GtkDoviMap *s)
{
  g_mutex_init (&s->lock);
  s->clear_sources = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, (GDestroyNotify) gst_caps_unref);
  s->mapper = gst_gtk_dovi_mapper_new ();
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
