/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "mapper.h"
#include "gstdovipicture.h"
struct GstGtkDoviNativeFrame {
  gint refs;
  GstBuffer *source;
  GstVideoInfo input_info, output_info;
};
typedef struct { GstMeta meta; GstGtkDoviNativeFrame *frame; guint64 generation; } NativeMeta;
static const GstMetaInfo *native_meta_info (void);
static GType native_meta_api (void)
{
  static gsize type;
  static const gchar *tags[] = {GST_META_TAG_VIDEO_STR, GST_META_TAG_VIDEO_SIZE_STR,
      GST_META_TAG_VIDEO_COLORSPACE_STR, NULL};
  if (g_once_init_enter (&type)) {
    GType registered = gst_meta_api_type_register ("GstGtkDoviNativeFrameMetaAPI", tags);
    g_once_init_leave (&type, registered);
  }
  return type;
}
GstGtkDoviNativeFrame *gst_gtk_dovi_native_frame_ref (GstGtkDoviNativeFrame *f)
{ g_atomic_int_inc (&f->refs); return f; }
void gst_gtk_dovi_native_frame_unref (GstGtkDoviNativeFrame *f)
{ if (f && g_atomic_int_dec_and_test (&f->refs)) { gst_buffer_unref (f->source); g_free (f); } }
static gboolean meta_init (GstMeta *meta, gpointer params, GstBuffer *buffer)
{ (void) params; (void) buffer; ((NativeMeta *) meta)->frame = NULL; return TRUE; }
static void meta_free (GstMeta *meta, GstBuffer *buffer)
{ (void) buffer; gst_gtk_dovi_native_frame_unref (((NativeMeta *) meta)->frame); }
static gboolean attach (GstBuffer *buffer, GstGtkDoviNativeFrame *frame, guint64 generation)
{
  NativeMeta *meta = (NativeMeta *) gst_buffer_add_meta (buffer, native_meta_info (), NULL);
  if (!meta) return FALSE;
  meta->frame = gst_gtk_dovi_native_frame_ref (frame); meta->generation = generation;
  return TRUE;
}
static gboolean meta_transform (GstBuffer *dest, GstMeta *meta, GstBuffer *source,
    GQuark type, gpointer data)
{
  (void) source;
  if (!GST_META_TRANSFORM_IS_COPY (type) || !data || ((GstMetaTransformCopy *) data)->region)
    return FALSE;
  NativeMeta *native = (NativeMeta *) meta;
  return attach (dest, native->frame, native->generation);
}
static const GstMetaInfo *native_meta_info (void)
{
  static gsize info;
  if (g_once_init_enter (&info)) {
    const GstMetaInfo *registered = gst_meta_register (native_meta_api (),
        "GstGtkDoviNativeFrameMeta", sizeof (NativeMeta), meta_init, meta_free, meta_transform);
    g_once_init_leave (&info, (gsize) registered);
  }
  return (const GstMetaInfo *) info;
}
GstGtkDoviNativeFrame *gst_gtk_dovi_native_frame_from_buffer (GstBuffer *buffer, guint64 *generation)
{
  NativeMeta *meta = (NativeMeta *) gst_buffer_get_meta (buffer, native_meta_api ());
  if (generation) *generation = meta ? meta->generation : 0;
  return meta && meta->frame ? gst_gtk_dovi_native_frame_ref (meta->frame) : NULL;
}
gboolean gst_gtk_dovi_native_frame_attach (GstBuffer *output, GstBuffer *input,
    const GstVideoInfo *input_info, const GstVideoInfo *output_info, guint64 generation)
{
  g_return_val_if_fail (output != input && gst_buffer_is_writable (output), FALSE);
  GstGtkDoviNativeFrame *frame = gst_gtk_dovi_native_frame_from_buffer (input, NULL);
  if (!frame) {
    frame = g_new0 (GstGtkDoviNativeFrame, 1); frame->refs = 1;
    frame->source = gst_buffer_ref (input);
    frame->input_info = *input_info; frame->output_info = *output_info;
  }
  gboolean success = attach (output, frame, generation);
  gst_gtk_dovi_native_frame_unref (frame); return success;
}
gboolean gst_gtk_dovi_target_from_context (const GstContext *context, GstGtkDoviTarget *target)
{
  *target = (GstGtkDoviTarget) {0};
  if (!context || !gst_context_has_context_type (context, "gst.gtk.dovi.target.v1")) return FALSE;
  const GstStructure *st = gst_context_get_structure (context);
  gboolean valid = FALSE;
  gst_structure_get_boolean (st, "valid", &valid);
  gboolean complete = gst_structure_get_uint64 (st, "generation", &target->generation) &&
      gst_structure_get_double (st, "min-nits", &target->min_nits) &&
      gst_structure_get_double (st, "max-nits", &target->max_nits) &&
      gst_structure_get_double (st, "reference-nits", &target->reference_nits);
  static const gchar *names[] = {"primary-r-x", "primary-r-y", "primary-g-x", "primary-g-y",
      "primary-b-x", "primary-b-y", "white-x", "white-y"};
  for (guint i = 0; i < 8; i++) complete &= gst_structure_get_double (st, names[i], &target->primaries[i]);
  target->valid = valid && complete;
  gst_structure_get_boolean (st, "composed", &target->composed);
  gst_structure_get_boolean (st, "hdr-ready", &target->render_ready);
  gst_structure_get_double (st, "encoding-reference-nits", &target->encoding_reference_nits);
  gst_structure_get_double (st, "encoding-max-nits", &target->encoding_max_nits);
  return TRUE;
}
int gst_gtk_dovi_native_frame_render (GstGtkDoviNativeFrame *frame, GstGtkDoviMapper *mapper,
    const GstContext *context, GstBuffer **output, GstVideoInfo *output_info, GError **error)
{
  GstGtkDoviTarget target;
  *output = NULL;
  if (!gst_gtk_dovi_target_from_context (context, &target) || !target.composed) return 0;
  *output_info = frame->output_info;
  int result = gst_gtk_dovi_mapper_render (mapper, frame->source,
      &frame->input_info, &target, output, output_info, error);
  if (result > 0) {
    GstVideoOverlayCompositionMeta *overlay = gst_buffer_get_video_overlay_composition_meta (frame->source);
    if (overlay) gst_buffer_add_video_overlay_composition_meta (*output, overlay->overlay);
    if (gst_debug_category_get_threshold (gtk_dovi_map_debug) >= GST_LEVEL_LOG) {
      GstDoviPictureMeta *picture = gst_buffer_get_dovi_picture_meta (frame->source);
      guint64 epoch = 0, id = 0;
      if (picture && picture->picture) gst_dovi_picture_get_identity (picture->picture, &epoch, &id);
      GstMapInfo pixels;
      if (gst_buffer_map (*output, &pixels, GST_MAP_READ)) {
        gchar *sha = g_compute_checksum_for_data (G_CHECKSUM_SHA256, pixels.data, pixels.size);
        guint rgb_min = 65535, rgb_max = 0, alpha_min = 65535, alpha_max = 0;
        for (gsize i = 0; i + 7 < pixels.size; i += 8) {
          for (guint c = 0; c < 4; c++) {
            guint v = GST_READ_UINT16_LE (pixels.data + i + c * 2);
            if (c == 3) { alpha_min = MIN (alpha_min, v); alpha_max = MAX (alpha_max, v); }
            else { rgb_min = MIN (rgb_min, v); rgb_max = MAX (rgb_max, v); }
          }
        }
        GST_LOG ("native pixels rgb=%u..%u alpha=%u..%u", rgb_min, rgb_max, alpha_min, alpha_max);
        GST_LOG ("visible native redraw result=%s pts=%" GST_TIME_FORMAT " epoch=%" G_GUINT64_FORMAT
            " picture=%" G_GUINT64_FORMAT " target-generation=%" G_GUINT64_FORMAT
            " peak=%.9g reference=%.9g rgba64-sha256=%s",
            result == 1 ? "mapped" : "baseline-reencoded", GST_TIME_ARGS (GST_BUFFER_PTS (frame->source)),
            epoch, id, target.generation, target.max_nits, target.reference_nits, sha);
        g_free (sha); gst_buffer_unmap (*output, &pixels);
      }
    }
    if (!attach (*output, frame, target.generation)) {
      gst_clear_buffer (output); return -1;
    }
  }
  return result;
}
