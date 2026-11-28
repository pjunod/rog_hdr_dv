/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* GStreamer adapter over librog-dovi-map. The qualification, target and
 * mapping rules live in the core; this file translates a GstBuffer, its
 * picture meta and the negotiated GstVideoInfo into the core's plain picture,
 * record and output, owns the output buffer pool and reports declines and
 * failures the way the element always has. */
#include <stdlib.h>
#include "mapper.h"
#include "native-input-formats.h"
#include "render-preconditions.h"
#include "gstdovipicture.h"
#include <rog-dovi-map.h>
#include <libavutil/imgutils.h>
#include <libavutil/pixdesc.h>
#include <gst/video/gstvideopool.h>
#include <string.h>
GST_DEBUG_CATEGORY (gtk_dovi_map_debug);
void gst_gtk_dovi_debug_init (void) {
  static gsize initialized;
  if (g_once_init_enter (&initialized)) {
    GST_DEBUG_CATEGORY_INIT (gtk_dovi_map_debug, "gtkdovimap", 0, "GTK Dolby native pre-conversion");
    g_once_init_leave (&initialized, 1);
  }
}
guint gst_gtk_dovi_core_abi (void) { return GST_GTK_DOVI_CORE_ABI; }
_Static_assert (GST_DOVI_BRIDGE_ABI == 2, "Unsupported picture bridge ABI");
_Static_assert (ROG_DOVI_MAP_ABI == 1, "Unsupported mapping core ABI");
struct GstGtkDoviMapper {
  rog_dovi_mapper *core;
  GstBufferPool *output_pool;
  GstVideoInfo pool_info;
  guint warned;
};
/* Core messages under the element's category; the core forwards libplacebo
 * messages too, at their own level. */
static void core_log (void *user, int level, const char *message)
{
  (void) user;
  static const GstDebugLevel levels[] = { GST_LEVEL_NONE, GST_LEVEL_ERROR,
    GST_LEVEL_WARNING, GST_LEVEL_INFO, GST_LEVEL_DEBUG, GST_LEVEL_LOG };
  GstDebugLevel gst = level >= 1 && level <= 5 ? levels[level] : GST_LEVEL_LOG;
  GST_CAT_LEVEL_LOG (gtk_dovi_map_debug, gst, NULL, "%s", message);
}
static int core_log_level (void)
{
  GstDebugLevel t = gst_debug_category_get_threshold (gtk_dovi_map_debug);
  return t >= GST_LEVEL_LOG ? ROG_DOVI_LOG_TRACE : t >= GST_LEVEL_DEBUG ? ROG_DOVI_LOG_DEBUG :
      t >= GST_LEVEL_INFO ? ROG_DOVI_LOG_INFO : t >= GST_LEVEL_WARNING ? ROG_DOVI_LOG_WARN :
      t >= GST_LEVEL_ERROR ? ROG_DOVI_LOG_ERROR : 0;
}
static GQuark mapper_error (void) { return g_quark_from_static_string ("gtk-dovi-mapper"); }
GstGtkDoviMapper *gst_gtk_dovi_mapper_new (void)
{
  gst_gtk_dovi_debug_init ();
  if (rog_dovi_map_abi () != ROG_DOVI_MAP_ABI) {
    GST_ERROR ("mapping core ABI %u, expected %u", rog_dovi_map_abi (), ROG_DOVI_MAP_ABI);
    return NULL;
  }
  rog_dovi_map_set_log (core_log, NULL, core_log_level ());
  GstGtkDoviMapper *s = g_new0 (GstGtkDoviMapper, 1);
  /* No render node: libplacebo's default device, as this element always used.
   * The device is kept for the process. Destroying the last one let the
   * Vulkan loader unload the NVIDIA driver, whose EGL library leaves an exit
   * handler registered: a process that had created and destroyed a device
   * crashed in that unmapped handler at exit (installed rogdv12, two mappers
   * in turn, 10 of 20 runs), and the same unload once released WebKit's
   * current EGL context. A kept device is never unloaded. */
  const struct rog_dovi_mapper_params params = {.struct_size = sizeof (params),
      .flags = ROG_DOVI_MAPPER_KEEP_DEVICE};
  s->core = rog_dovi_mapper_new (&params);
  if (!s->core) { g_free (s); return NULL; }
  return s;
}
static void clear_output_pool (GstGtkDoviMapper *s)
{
  if (!s->output_pool) return;
  /* Outstanding buffers keep the retired pool alive until their final unref. */
  gst_buffer_pool_set_active (s->output_pool, FALSE);
  gst_clear_object (&s->output_pool);
  gst_video_info_init (&s->pool_info);
}
static gboolean same_output_layout (const GstVideoInfo *a, const GstVideoInfo *b)
{
  if (!gst_video_info_is_equal (a, b) || a->size != b->size) return FALSE;
  for (guint i = 0; i < GST_VIDEO_INFO_N_PLANES (a); i++)
    if (a->offset[i] != b->offset[i] || a->stride[i] != b->stride[i]) return FALSE;
  return TRUE;
}
static gboolean valid_output_span (const GstVideoInfo *info)
{
  /* The supported outputs are packed RGBA; custom padding and bottom-up rows
   * are valid, but every active byte must remain inside the owned buffer. */
  gint width = GST_VIDEO_INFO_WIDTH (info), height = GST_VIDEO_INFO_HEIGHT (info);
  if (width <= 0 || height <= 0 || GST_VIDEO_INFO_N_PLANES (info) != 1 ||
      !info->size || info->size > G_MAXUINT) return FALSE;
  guint pixel_stride = GST_VIDEO_INFO_COMP_PSTRIDE (info, 0);
  if (!pixel_stride || (gsize) width > G_MAXSIZE / pixel_stride) return FALSE;
  gsize row_bytes = (gsize) width * pixel_stride;
  gint64 stride = info->stride[0];
  guint64 step = stride < 0 ? -stride : stride;
  gsize rows = height - 1;
  if (step < row_bytes || (rows && step > G_MAXSIZE / rows)) return FALSE;
  gsize span = rows * step, offset = info->offset[0];
  if (offset > info->size || row_bytes > info->size - offset) return FALSE;
  if (stride < 0) return span <= offset;
  return span <= info->size - offset - row_bytes;
}
static GstBuffer *acquire_output_buffer (GstGtkDoviMapper *s, const GstVideoInfo *info)
{
  if (!valid_output_span (info)) return NULL;
  if (s->output_pool && !same_output_layout (&s->pool_info, info))
    clear_output_pool (s);
  if (!s->output_pool) {
    GstCaps *caps = gst_video_info_to_caps (info);
    if (!caps) return NULL;
    GstBufferPool *pool = gst_video_buffer_pool_new ();
    GstStructure *config = gst_buffer_pool_get_config (pool);
    /* No maximum: a held consumer buffer must never stall the view thread.
     * This pool owns one output layout and grows only with outstanding refs. */
    gst_buffer_pool_config_set_params (config, caps, info->size, 2, 0);
    gst_caps_unref (caps);
    if (!gst_buffer_pool_set_config (pool, config) ||
        !gst_buffer_pool_set_active (pool, TRUE)) {
      gst_object_unref (pool);
      return NULL;
    }
    s->output_pool = pool;
    s->pool_info = *info;
  }
  GstBuffer *buffer = NULL;
  if (gst_buffer_pool_acquire_buffer (s->output_pool, &buffer, NULL) != GST_FLOW_OK)
    return NULL;
  /* Caps do not describe custom strides. Keep the pool's inferred VideoMeta
   * disabled and publish the exact negotiated layout on each acquired buffer.
   * Normal pool reset removes this and the picture's other transient metas. */
  gsize offsets[GST_VIDEO_MAX_PLANES] = {0};
  gint strides[GST_VIDEO_MAX_PLANES] = {0};
  for (guint i = 0; i < GST_VIDEO_INFO_N_PLANES (info); i++) {
    offsets[i] = info->offset[i]; strides[i] = info->stride[i];
  }
  if (!gst_buffer_add_video_meta_full (buffer, GST_VIDEO_FRAME_FLAG_NONE,
          GST_VIDEO_INFO_FORMAT (info), GST_VIDEO_INFO_WIDTH (info),
          GST_VIDEO_INFO_HEIGHT (info), GST_VIDEO_INFO_N_PLANES (info), offsets, strides)) {
    gst_buffer_unref (buffer);
    return NULL;
  }
  return buffer;
}
void gst_gtk_dovi_mapper_free (GstGtkDoviMapper *s)
{
  if (!s) return;
  clear_output_pool (s);
  rog_dovi_mapper_free (s->core);
  g_free (s);
}
static enum AVPixelFormat input_format (GstVideoFormat f)
{
  switch (f) {
#define IMPORT_FORMAT(gst, av, accelerator) case GST_VIDEO_FORMAT_##gst: return AV_PIX_FMT_##av;
    GTK_DOVI_NATIVE_INPUT_FORMATS (IMPORT_FORMAT)
#undef IMPORT_FORMAT
    default: return AV_PIX_FMT_NONE;
  }
}
static uint32_t core_format (enum AVPixelFormat f)
{
  switch (f) {
#define CORE_FORMAT(gst, av, accelerator) case AV_PIX_FMT_##av: return ROG_DOVI_FORMAT_##av;
    GTK_DOVI_NATIVE_INPUT_FORMATS (CORE_FORMAT)
#undef CORE_FORMAT
    default: return ROG_DOVI_FORMAT_NONE;
  }
}
/* av_dovi_metadata_alloc's layout size, which the bridge's copies use. */
static size_t metadata_blob_size (void)
{
  static gsize size;
  if (g_once_init_enter (&size)) {
    size_t n = 0;
    AVDOVIMetadata *probe = av_dovi_metadata_alloc (&n);
    av_free (probe);
    g_once_init_leave (&size, n ? n : 1);
  }
  return size;
}
/* The picture's own record from its meta, never a previous picture's. */
static gboolean picture_record (GstDoviPictureMeta *meta, struct rog_dovi_picture *record)
{
  *record = (struct rog_dovi_picture) {.struct_size = sizeof (*record),
      .libavutil_version = LIBAVUTIL_VERSION_INT};
  if (!meta || !meta->picture) return FALSE;
  const AVDOVIMetadata *resolved = gst_dovi_picture_get_metadata (meta->picture);
  if (resolved) { record->metadata = resolved; record->metadata_size = metadata_blob_size (); }
  GBytes *raw = gst_dovi_picture_get_rpu (meta->picture);
  if (raw) {
    gsize size;
    record->rpu = g_bytes_get_data (raw, &size);
    record->rpu_size = size;
  }
  const AVDOVIDecoderConfigurationRecord *config = gst_dovi_picture_get_stream_config (meta->picture);
  if (config) { record->has_config = 1; record->config = gtk_dovi_core_config (config); }
  record->profile = gst_dovi_picture_get_profile (meta->picture);
  record->enhancement = gst_dovi_picture_get_enhancement (meta->picture);
  guint width = 0, height = 0;
  gst_dovi_picture_get_dimensions (meta->picture, &width, &height);
  record->width = width; record->height = height;
  const GstDoviGeometry *g = gst_dovi_picture_get_geometry (meta->picture);
  if (g) {
    record->has_geometry = 1;
    record->geometry = (struct rog_dovi_geometry) {g->coded_width, g->coded_height,
        g->x, g->y, g->width, g->height};
  }
  return TRUE;
}
/* The bridge's decoded enhancement layer as borrowed host planes. */
static gboolean enhancement_planes (const AVFrame *fel, struct rog_dovi_planes *out)
{
  if (!fel) return FALSE;
  *out = (struct rog_dovi_planes) {.struct_size = sizeof (*out),
      .format = core_format ((enum AVPixelFormat) fel->format),
      .storage_width = fel->width, .storage_height = fel->height,
      .width = fel->width, .height = fel->height,
      .color_range = fel->color_range, .colorspace = fel->colorspace,
      .color_primaries = fel->color_primaries, .color_trc = fel->color_trc,
      .chroma_location = fel->chroma_location,
      .sar_num = fel->sample_aspect_ratio.num, .sar_den = fel->sample_aspect_ratio.den};
  for (guint i = 0; i < 4; i++) { out->data[i] = fel->data[i]; out->stride[i] = fel->linesize[i]; }
  return TRUE;
}
typedef struct {
  GstGtkDoviMapper *mapper;
  const GstVideoInfo *info;
  GstBuffer *result;
  GstVideoFrame out;
  gboolean mapped;
} OutputTarget;
/* Called by the core exactly where the element used to acquire its output. */
static int acquire_output (void *user, void **data, int32_t *stride)
{
  OutputTarget *o = user;
  if (!o->result) {
    o->result = acquire_output_buffer (o->mapper, o->info);
    if (!o->result || !gst_video_frame_map (&o->out, o->info, o->result, GST_MAP_WRITE)) return 0;
    o->mapped = TRUE;
  }
  if (!o->mapped) return 0;
  *data = GST_VIDEO_FRAME_PLANE_DATA (&o->out, 0);
  *stride = GST_VIDEO_FRAME_PLANE_STRIDE (&o->out, 0);
  return 1;
}
static void report_declines (GstGtkDoviMapper *s)
{
  /* The element never named an ineligible picture or destination: that is
   * the ordinary route for pictures without a qualified record. */
  guint declined = rog_dovi_map_last_decline (s->core) & ~ROG_DOVI_DECLINE_NOT_ELIGIBLE;
  for (guint bit = 1; declined; bit <<= 1) {
    if (!(declined & bit)) continue;
    declined &= ~bit;
    if (!(s->warned & bit)) {
      GST_WARNING ("GTK Dolby mapping declined: %s", rog_dovi_map_decline_reason (bit));
      s->warned |= bit;
    }
  }
}
static int render_destination (GstGtkDoviMapper *s, GstBuffer *input,
    const GstVideoInfo *info, const GstGtkDoviTarget *t,
    GstBuffer **output, GstVideoInfo *output_info, GError **error, gboolean sdr)
{
  *output = NULL;
  GstDoviPictureMeta *meta = gst_buffer_get_dovi_picture_meta (input);
  struct rog_dovi_picture record;
  gboolean has_record = picture_record (meta, &record);
  struct rog_dovi_planes fel;
  gboolean has_fel = enhancement_planes (gst_dovi_picture_meta_get_fel (meta), &fel);
  enum AVPixelFormat format = input_format (GST_VIDEO_INFO_FORMAT (info));
  struct rog_dovi_planes picture = {.struct_size = sizeof (picture),
      .format = core_format (format),
      .width = GST_VIDEO_INFO_WIDTH (info), .height = GST_VIDEO_INFO_HEIGHT (info)};
  GstVideoFrame mapped = {0};
  /* An unsupported format is left to the core, which names it. */
  if (format != AV_PIX_FMT_NONE) {
    if (!gst_video_frame_map (&mapped, info, input, GST_MAP_READ)) {
      g_set_error_literal (error, mapper_error (), 1, "Eligible Dolby frame normalization/mapping failed");
      return -1;
    }
    picture.storage_width = GST_VIDEO_FRAME_WIDTH (&mapped);
    picture.storage_height = GST_VIDEO_FRAME_HEIGHT (&mapped);
    for (guint i = 0; i < GST_VIDEO_INFO_N_PLANES (info); i++) {
      picture.data[i] = GST_VIDEO_FRAME_PLANE_DATA (&mapped, i);
      picture.stride[i] = GST_VIDEO_FRAME_PLANE_STRIDE (&mapped, i);
    }
    GstVideoCropMeta *crop = gst_buffer_get_video_crop_meta (input);
    if (crop) {
      picture.has_crop = 1;
      picture.crop_x = crop->x; picture.crop_y = crop->y;
      picture.crop_width = crop->width; picture.crop_height = crop->height;
    }
    picture.color_range = info->colorimetry.range == GST_VIDEO_COLOR_RANGE_0_255 ? AVCOL_RANGE_JPEG : AVCOL_RANGE_MPEG;
    picture.color_primaries = gst_video_color_primaries_to_iso (info->colorimetry.primaries);
    picture.color_trc = gst_video_transfer_function_to_iso (info->colorimetry.transfer);
    picture.colorspace = gst_video_color_matrix_to_iso (info->colorimetry.matrix);
    gboolean rgb = av_pix_fmt_desc_get (format)->flags & AV_PIX_FMT_FLAG_RGB;
    if (info->colorimetry.primaries == GST_VIDEO_COLOR_PRIMARIES_UNKNOWN) picture.color_primaries = AVCOL_PRI_BT709;
    if (info->colorimetry.transfer == GST_VIDEO_TRANSFER_UNKNOWN) picture.color_trc = rgb ? AVCOL_TRC_IEC61966_2_1 : AVCOL_TRC_BT709;
    if (info->colorimetry.matrix == GST_VIDEO_COLOR_MATRIX_UNKNOWN) picture.colorspace = rgb ? AVCOL_SPC_RGB : AVCOL_SPC_BT709;
    if (info->colorimetry.range == GST_VIDEO_COLOR_RANGE_UNKNOWN) picture.color_range = rgb ? AVCOL_RANGE_JPEG : AVCOL_RANGE_MPEG;
    switch (info->chroma_site) {
      case GST_VIDEO_CHROMA_SITE_JPEG: picture.chroma_location = AVCHROMA_LOC_CENTER; break;
      case GST_VIDEO_CHROMA_SITE_MPEG2: picture.chroma_location = AVCHROMA_LOC_LEFT; break;
      case GST_VIDEO_CHROMA_SITE_COSITED: picture.chroma_location = AVCHROMA_LOC_TOPLEFT; break;
      case GST_VIDEO_CHROMA_SITE_V_COSITED: picture.chroma_location = AVCHROMA_LOC_TOP; break;
      default: picture.chroma_location = AVCHROMA_LOC_UNSPECIFIED; break;
    }
    picture.sar_num = GST_VIDEO_INFO_PAR_N (info);
    picture.sar_den = GST_VIDEO_INFO_PAR_D (info);
    if (GST_VIDEO_INFO_INTERLACE_MODE (info) != GST_VIDEO_INTERLACE_MODE_PROGRESSIVE ||
        GST_BUFFER_FLAG_IS_SET (input, GST_VIDEO_BUFFER_FLAG_INTERLACED))
      picture.flags |= ROG_DOVI_PICTURE_INTERLACED;
    if (GST_BUFFER_FLAG_IS_SET (input, GST_BUFFER_FLAG_CORRUPTED))
      picture.flags |= ROG_DOVI_PICTURE_CORRUPTED;
    if (info->chroma_site & GST_VIDEO_CHROMA_SITE_ALT_LINE)
      picture.flags |= ROG_DOVI_PICTURE_ALT_LINE_CHROMA;
  }
  struct rog_dovi_target target = {.struct_size = sizeof (target)};
  if (t) {
    target.flags = (t->valid ? ROG_DOVI_TARGET_VALID : 0) |
        (t->composed ? ROG_DOVI_TARGET_COMPOSED : 0) |
        (t->render_ready ? ROG_DOVI_TARGET_RENDER_READY : 0);
    target.generation = t->generation;
    memcpy (target.primaries, t->primaries, sizeof (target.primaries));
    target.min_nits = t->min_nits; target.max_nits = t->max_nits;
    target.reference_nits = t->reference_nits;
    target.encoding_reference_nits = t->encoding_reference_nits;
    target.encoding_max_nits = t->encoding_max_nits;
  }
  GstVideoFormat out_format = GST_VIDEO_INFO_FORMAT (output_info);
  OutputTarget sink = {.mapper = s, .info = output_info};
  struct rog_dovi_output out = {.struct_size = sizeof (out), .kind = ROG_DOVI_OUTPUT_HOST,
      .width = GST_VIDEO_INFO_WIDTH (output_info), .height = GST_VIDEO_INFO_HEIGHT (output_info),
      .color_range = output_info->colorimetry.range == GST_VIDEO_COLOR_RANGE_0_255 ? AVCOL_RANGE_JPEG : AVCOL_RANGE_MPEG,
      .host_format = out_format == GST_VIDEO_FORMAT_RGBA ? ROG_DOVI_FORMAT_RGBA :
          out_format == GST_VIDEO_FORMAT_RGBA64_LE ? ROG_DOVI_FORMAT_RGBA64LE : ROG_DOVI_FORMAT_NONE,
      .acquire = acquire_output, .acquire_user = &sink};
  const char *reason = NULL;
  int result = rog_dovi_map_planes (s->core, &picture, has_fel ? &fel : NULL,
      has_record ? &record : NULL,
      sdr ? ROG_DOVI_DESTINATION_STANDARD_SDR_SRGB : ROG_DOVI_DESTINATION_DISPLAY_PQ,
      t ? &target : NULL, &out, ROG_DOVI_MAP_BASELINE_ON_DECLINE, &reason);
  report_declines (s);
  if (sink.mapped) gst_video_frame_unmap (&sink.out);
  if (mapped.buffer) gst_video_frame_unmap (&mapped);
  if (result < 0 || !sink.result) {
    gst_clear_buffer (&sink.result);
    if (result >= 0 || !reason) reason = "Eligible Dolby frame normalization/mapping failed";
    if (result < 0 && rog_dovi_map_last_failure (s->core) == ROG_DOVI_FAILURE_CONTENT)
      g_set_error_literal (error, GST_STREAM_ERROR, GST_STREAM_ERROR_FORMAT, reason);
    else
      g_set_error_literal (error, mapper_error (), 1, reason);
    return -1;
  }
  gst_buffer_copy_into (sink.result, input, GST_BUFFER_COPY_FLAGS | GST_BUFFER_COPY_TIMESTAMPS, 0, -1);
  /* GST_BUFFER_COPY_FLAGS preserves destination memory tracking itself. */
  *output = sink.result;
  return result == 1 ? 1 : 2;
}

int gst_gtk_dovi_mapper_render_destination (GstGtkDoviMapper *self,
    GstBuffer *input, const GstVideoInfo *info, GstGtkDoviDestinationKind kind,
    const GstGtkDoviTarget *physical, GstBuffer **output,
    GstVideoInfo *output_info, GError **error)
{
  *output = NULL;
  gboolean sdr = kind == GST_GTK_DOVI_DESTINATION_STANDARD_SDR_SRGB;
  if (!self || (!sdr && kind != GST_GTK_DOVI_DESTINATION_DISPLAY_PQ)) {
    g_set_error_literal (error, mapper_error (), 1, "Unsupported destination kind");
    return -1;
  }
  if (sdr && (GST_VIDEO_INFO_FORMAT (output_info) != GST_VIDEO_FORMAT_RGBA ||
      output_info->colorimetry.range != GST_VIDEO_COLOR_RANGE_0_255 ||
      output_info->colorimetry.matrix != GST_VIDEO_COLOR_MATRIX_RGB ||
      output_info->colorimetry.primaries != GST_VIDEO_COLOR_PRIMARIES_BT709 ||
      output_info->colorimetry.transfer != GST_VIDEO_TRANSFER_SRGB)) {
    g_set_error_literal (error, mapper_error (), 1, "Invalid standard SDR output declaration");
    return -1;
  }
  /* The SDR destination's logical target and the renderer cache flush on a
   * destination switch belong to the core. */
  return render_destination (self, input, info, sdr ? NULL : physical, output,
      output_info, error, sdr);
}

int gst_gtk_dovi_mapper_render (GstGtkDoviMapper *self, GstBuffer *input,
    const GstVideoInfo *info, const GstGtkDoviTarget *physical,
    GstBuffer **output, GstVideoInfo *output_info, GError **error)
{
  return gst_gtk_dovi_mapper_render_destination (self, input, info,
      GST_GTK_DOVI_DESTINATION_DISPLAY_PQ, physical, output, output_info, error);
}
