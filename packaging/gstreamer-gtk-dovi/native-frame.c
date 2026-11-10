/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "mapper.h"
#include "source-lease-private.h"
#include "gstdovipicture.h"
#include "render-preconditions.h"
struct GstGtkDoviSourceLease {
  gint refs, revoked;
  guint64 revision, selection;
  gchar *stream_id;
  GBytes *configuration;
  AVDOVIDecoderConfigurationRecord stream_configuration;
};
GstGtkDoviSourceLease *_gst_gtk_dovi_source_lease_new_selected (const GstCaps *caps,
    const gchar *stream_id, guint64 revision, guint64 selection)
{
  AVDOVIDecoderConfigurationRecord config;
  GBytes *bytes = NULL;
  if (!caps || !gst_caps_is_fixed (caps) || gst_caps_get_size (caps) != 1 ||
      !stream_id || !*stream_id || !revision || !selection) return NULL;
  const GstStructure *st = gst_caps_get_structure (caps, 0);
  gboolean known = gst_structure_has_name (st, "video/x-h265") &&
      !gst_structure_has_field (st, "protection-system") &&
      gst_dovi_caps_get_stream_config (caps, &config, &bytes);
  if (!known || !bytes || g_bytes_get_size (bytes) != 24 ||
      config.dv_version_major != 1 || config.dv_version_minor != 0 ||
      !config.rpu_present_flag || !config.bl_present_flag ||
      config.dv_md_compression != AV_DOVI_COMPRESSION_NONE ||
      !((!config.el_present_flag && config.dv_profile == 5 &&
          config.dv_bl_signal_compatibility_id == 0) ||
        (!config.el_present_flag && config.dv_profile == 8 &&
          config.dv_bl_signal_compatibility_id == 1) ||
        (config.el_present_flag && config.dv_profile == 7 &&
          config.dv_bl_signal_compatibility_id == 6))) {
    g_clear_pointer (&bytes, g_bytes_unref); return NULL;
  }
  GstGtkDoviSourceLease *lease = g_new0 (GstGtkDoviSourceLease, 1);
  lease->refs = 1; lease->revision = revision; lease->selection = selection;
  lease->stream_id = g_strdup (stream_id); lease->configuration = bytes;
  lease->stream_configuration = config;
  return lease;
}
GstGtkDoviSourceLease *gst_gtk_dovi_source_lease_new (const GstCaps *caps,
    const gchar *stream_id, guint64 revision)
{ return _gst_gtk_dovi_source_lease_new_selected (caps, stream_id, revision, 1); }
guint64 _gst_gtk_dovi_source_lease_selection (const GstGtkDoviSourceLease *lease)
{ return gst_gtk_dovi_source_lease_is_valid (lease) ? lease->selection : 0; }
GstGtkDoviSourceLease *gst_gtk_dovi_source_lease_ref (GstGtkDoviSourceLease *lease)
{ if (lease) g_atomic_int_inc (&lease->refs); return lease; }
void gst_gtk_dovi_source_lease_unref (GstGtkDoviSourceLease *lease)
{
  if (lease && g_atomic_int_dec_and_test (&lease->refs)) {
    g_free (lease->stream_id); g_bytes_unref (lease->configuration); g_free (lease);
  }
}
void gst_gtk_dovi_source_lease_revoke (GstGtkDoviSourceLease *lease)
{ if (lease) g_atomic_int_set (&lease->revoked, TRUE); }
gboolean gst_gtk_dovi_source_lease_is_valid (const GstGtkDoviSourceLease *lease)
{ return lease && !g_atomic_int_get (&lease->revoked); }
gboolean gst_gtk_dovi_source_lease_matches (const GstGtkDoviSourceLease *lease,
    const gchar *stream_id, const GstCaps *caps)
{
  if (!caps || !gst_gtk_dovi_source_lease_is_valid (lease) || !stream_id ||
      g_strcmp0 (lease->stream_id, stream_id)) return FALSE;
  AVDOVIDecoderConfigurationRecord config;
  GBytes *bytes = NULL;
  gboolean known = gst_dovi_caps_get_stream_config (caps, &config, &bytes);
  gboolean same = known && bytes && g_bytes_equal (bytes, lease->configuration);
  g_clear_pointer (&bytes, g_bytes_unref); return same;
}
struct GstGtkDoviNativeFrame {
  gint refs;
  GstBuffer *source;
  GstVideoInfo input_info, output_info;
  GstGtkDoviSourceLease *lease;
  AVDOVIDecoderConfigurationRecord required_configuration;
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
{ if (f && g_atomic_int_dec_and_test (&f->refs)) { gst_buffer_unref (f->source); gst_gtk_dovi_source_lease_unref (f->lease); g_free (f); } }
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
guint64 gst_gtk_dovi_native_frame_source_revision (GstGtkDoviNativeFrame *frame)
{ return frame && gst_gtk_dovi_source_lease_is_valid (frame->lease) ? frame->lease->revision : 0; }
guint64 gst_gtk_dovi_native_frame_source_selection (GstGtkDoviNativeFrame *frame)
{ return frame ? _gst_gtk_dovi_source_lease_selection (frame->lease) : 0; }
gboolean gst_gtk_dovi_native_frame_attach_source (GstBuffer *output, GstBuffer *input,
    const GstVideoInfo *input_info, const GstVideoInfo *output_info, guint64 generation,
    GstGtkDoviSourceLease *lease)
{
  g_return_val_if_fail (output != input && gst_buffer_is_writable (output), FALSE);
  if (lease && !gst_gtk_dovi_source_lease_is_valid (lease)) return FALSE;
  GstGtkDoviNativeFrame *frame = gst_gtk_dovi_native_frame_from_buffer (input, NULL);
  if (frame && ((lease && frame->lease != lease) ||
      (frame->lease && !gst_gtk_dovi_source_lease_is_valid (frame->lease)))) {
    gst_gtk_dovi_native_frame_unref (frame); return FALSE;
  }
  if (!frame) {
    GstDoviPictureMeta *picture = gst_buffer_get_dovi_picture_meta (input);
    const AVDOVIDecoderConfigurationRecord *required = lease ? &lease->stream_configuration :
        (picture && picture->picture ? gst_dovi_picture_get_stream_config (picture->picture) : NULL);
    if (!gtk_dovi_profile5_picture_proved (required, input)) return FALSE;
    frame = g_new0 (GstGtkDoviNativeFrame, 1); frame->refs = 1;
    if (required) frame->required_configuration = *required;
    frame->source = gst_buffer_ref (input);
    frame->input_info = *input_info; frame->output_info = *output_info;
    frame->lease = gst_gtk_dovi_source_lease_ref (lease);
  }
  gboolean success = attach (output, frame, generation);
  gst_gtk_dovi_native_frame_unref (frame); return success;
}
gboolean gst_gtk_dovi_native_frame_attach (GstBuffer *output, GstBuffer *input,
    const GstVideoInfo *input_info, const GstVideoInfo *output_info, guint64 generation)
{
  return gst_gtk_dovi_native_frame_attach_source (output, input, input_info,
      output_info, generation, NULL);
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
int gst_gtk_dovi_native_frame_render_destination (GstGtkDoviNativeFrame *frame,
    GstGtkDoviMapper *mapper, GstGtkDoviDestinationKind kind, const GstContext *context,
    GstBuffer **output, GstVideoInfo *output_info, guint64 *epoch_out,
    guint64 *picture_id_out, GError **error)
{
  GstGtkDoviTarget target = {0};
  *output = NULL;
  gst_video_info_init (output_info);
  if (epoch_out) *epoch_out = 0;
  if (picture_id_out) *picture_id_out = 0;
  if (frame->lease && !gst_gtk_dovi_source_lease_is_valid (frame->lease)) return 0;
  if (!gtk_dovi_profile5_picture_proved (&frame->required_configuration, frame->source)) {
    g_set_error_literal (error, GST_STREAM_ERROR, GST_STREAM_ERROR_FORMAT,
        "Retained Profile 5 source lacks matching complete per-picture Dolby proof");
    return -1;
  }
  gboolean sdr = kind == GST_GTK_DOVI_DESTINATION_STANDARD_SDR_SRGB;
  if (!sdr && kind != GST_GTK_DOVI_DESTINATION_DISPLAY_PQ) {
    g_set_error_literal (error, GST_CORE_ERROR, GST_CORE_ERROR_NEGOTIATION,
        "Unknown native frame destination");
    return -1;
  }
  if (!sdr && (!gst_gtk_dovi_target_from_context (context, &target) || !target.composed))
    return 0;

  /* Retained frames own the decoder input. A prior SDR presentation may have
   * an eight-bit row layout, even when this redraw requests native HDR. */
  GstVideoFormat format = sdr ? GST_VIDEO_FORMAT_RGBA : GST_VIDEO_FORMAT_RGBA64_LE;
  GstCaps *caps = gst_video_info_to_caps (&frame->input_info);
  if (!caps) return -1;
  GstVideoColorimetry color = {GST_VIDEO_COLOR_RANGE_0_255, GST_VIDEO_COLOR_MATRIX_RGB,
      sdr ? GST_VIDEO_TRANSFER_SRGB : GST_VIDEO_TRANSFER_SMPTE2084,
      sdr ? GST_VIDEO_COLOR_PRIMARIES_BT709 : GST_VIDEO_COLOR_PRIMARIES_BT2020};
  gchar *encoded = gst_video_colorimetry_to_string (&color);
  gst_structure_remove_field (gst_caps_get_structure (caps, 0), "chroma-site");
  gst_caps_set_simple (caps, "format", G_TYPE_STRING, gst_video_format_to_string (format),
      "colorimetry", G_TYPE_STRING, encoded, NULL);
  g_free (encoded);
  GstVideoInfo dest_info;
  gboolean complete = gst_video_info_from_caps (&dest_info, caps);
  gst_caps_unref (caps);
  if (!complete) return -1;
  int result = gst_gtk_dovi_mapper_render_destination (mapper, frame->source,
      &frame->input_info, kind, &target, output, &dest_info, error);
  if (frame->lease && !gst_gtk_dovi_source_lease_is_valid (frame->lease)) {
    gst_clear_buffer (output); return 0;
  }
  if (result > 0) {
    GstVideoOverlayCompositionMeta *overlay = gst_buffer_get_video_overlay_composition_meta (frame->source);
    if (overlay) gst_buffer_add_video_overlay_composition_meta (*output, overlay->overlay);
    GstDoviPictureMeta *picture = gst_buffer_get_dovi_picture_meta (frame->source);
    guint64 epoch = 0, id = 0;
    if (picture && picture->picture)
      gst_dovi_picture_get_identity (picture->picture, &epoch, &id);
    if (!sdr && gst_debug_category_get_threshold (gtk_dovi_map_debug) >= GST_LEVEL_LOG) {
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
    if (frame->lease && !gst_gtk_dovi_source_lease_is_valid (frame->lease)) {
      gst_clear_buffer (output); return 0;
    }
    *output_info = dest_info;
    if (epoch_out) *epoch_out = epoch;
    if (picture_id_out) *picture_id_out = id;
  }
  return result;
}
int gst_gtk_dovi_native_frame_render (GstGtkDoviNativeFrame *frame, GstGtkDoviMapper *mapper,
    const GstContext *context, GstBuffer **output, GstVideoInfo *output_info, GError **error)
{
  return gst_gtk_dovi_native_frame_render_destination (frame, mapper,
      GST_GTK_DOVI_DESTINATION_DISPLAY_PQ, context, output, output_info, NULL, NULL, error);
}
