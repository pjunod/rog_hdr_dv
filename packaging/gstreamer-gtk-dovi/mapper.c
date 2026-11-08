/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "mapper.h"
#include "gstdovipicture.h"
#include <dv_provider387.h>
#include <libplacebo/vulkan.h>
#include <libplacebo/renderer.h>
#include <libplacebo/utils/libav.h>
#include <libavutil/imgutils.h>
#include <math.h>
struct GstGtkDoviMapper {
  pl_vulkan vk;
  pl_renderer renderer;
  struct dv_provider387 *provider;
  pl_tex source[4], output[4];
  int mapped;
};
static GQuark mapper_error (void) { return g_quark_from_static_string ("gtk-dovi-mapper"); }
static int provider_map (void *priv, pl_gpu gpu, const uint8_t *rpu, size_t size,
    bool composed, const struct pl_color_space *target, pl_tex master,
    pl_tex *mapped, struct pl_color_space *color)
{
  GstGtkDoviMapper *s = priv;
  s->mapped = dv_provider387_map (s->provider, gpu, rpu, size, composed,
      target, master, mapped, color);
  return s->mapped;
}
GstGtkDoviMapper *gst_gtk_dovi_mapper_new (void) { return g_new0 (GstGtkDoviMapper, 1); }
void gst_gtk_dovi_mapper_free (GstGtkDoviMapper *s)
{
  if (!s) return;
  if (s->vk) {
    dv_provider387_destroy (&s->provider);
    pl_renderer_destroy (&s->renderer);
    for (unsigned i = 0; i < 4; i++) {
      pl_tex_destroy (s->vk->gpu, &s->source[i]);
      pl_tex_destroy (s->vk->gpu, &s->output[i]);
    }
    pl_vulkan_destroy (&s->vk);
  }
  g_free (s);
}
static enum AVPixelFormat input_format (GstVideoFormat f)
{
  switch (f) {
    case GST_VIDEO_FORMAT_NV12: return AV_PIX_FMT_NV12;
    case GST_VIDEO_FORMAT_P010_10LE: return AV_PIX_FMT_P010LE;
    case GST_VIDEO_FORMAT_I420: return AV_PIX_FMT_YUV420P;
    case GST_VIDEO_FORMAT_I420_10LE: return AV_PIX_FMT_YUV420P10LE;
    default: return AV_PIX_FMT_NONE;
  }
}
int gst_gtk_dovi_mapper_render (GstGtkDoviMapper *s, GstBuffer *input,
    const GstVideoInfo *info, const GstGtkDoviTarget *t,
    GstBuffer **output, GstVideoInfo *output_info, GError **error)
{
  *output = NULL;
  GstDoviPictureMeta *meta = gst_buffer_get_dovi_picture_meta (input);
  if (!meta || !meta->picture || !t || !t->valid) return 0;
  if (gst_dovi_picture_get_enhancement (meta->picture) != GST_DOVI_ENHANCEMENT_NOT_REQUIRED)
    return 0;
  const AVDOVIMetadata *resolved = gst_dovi_picture_get_metadata (meta->picture);
  GBytes *raw = gst_dovi_picture_get_rpu (meta->picture);
  guint width, height;
  gst_dovi_picture_get_dimensions (meta->picture, &width, &height);
  enum AVPixelFormat format = input_format (GST_VIDEO_INFO_FORMAT (info));
  /* Cropped/transformed pixels are never silently called a native master. */
  if (!resolved || !raw || format == AV_PIX_FMT_NONE ||
      width != (guint) GST_VIDEO_INFO_WIDTH (info) ||
      height != (guint) GST_VIDEO_INFO_HEIGHT (info) ||
      gst_buffer_get_video_crop_meta (input)) return 0;
  guint profile = gst_dovi_picture_get_profile (meta->picture);
  if (profile != 5 && profile != 8) return 0;
  if (!isfinite (t->max_nits) || !isfinite (t->min_nits) ||
      t->max_nits <= 203 || t->min_nits < 0 || t->min_nits >= t->max_nits)
    return 0;
  GstVideoFrame mapped = {0};
  AVFrame *src = av_frame_alloc (), *dst = av_frame_alloc ();
  struct pl_frame source = {0}, destination = {0};
  gboolean uploaded = FALSE, success = FALSE;
  GstBuffer *result = NULL;
  if (!src || !dst || !gst_video_frame_map (&mapped, info, input, GST_MAP_READ)) goto done;
  src->format = format; src->width = width; src->height = height;
  src->color_range = AVCOL_RANGE_MPEG;
  if (av_frame_get_buffer (src, 32) < 0) goto done;
  const uint8_t *planes[4] = {0}; int strides[4] = {0};
  for (guint i = 0; i < GST_VIDEO_INFO_N_PLANES (info); i++) {
    planes[i] = GST_VIDEO_FRAME_PLANE_DATA (&mapped, i);
    strides[i] = GST_VIDEO_FRAME_PLANE_STRIDE (&mapped, i);
  }
  av_image_copy (src->data, src->linesize, planes, strides, format, width, height);
  if (!s->vk) {
    s->vk = pl_vulkan_create (NULL, pl_vulkan_params (.allow_software = true));
    if (!s->vk) goto done;
    s->renderer = pl_renderer_create (NULL, s->vk->gpu);
    s->provider = dv_provider387_create (s->vk->gpu, NULL);
  }
  if (!s->renderer || !s->provider) goto done;
  if (!pl_map_avframe_ex (s->vk->gpu, &source,
      pl_avframe_params (.frame = src, .tex = s->source, .map_dovi = false))) goto done;
  uploaded = TRUE;
  struct pl_dovi_metadata dovi;
  pl_map_avdovi_metadata (&source.color, &source.repr, &dovi, resolved);
  gsize raw_size;
  source.dovi_rpu = g_bytes_get_data (raw, &raw_size);
  source.dovi_rpu_size = raw_size;
  source.dovi_master_width = width; source.dovi_master_height = height;
  dst->format = AV_PIX_FMT_RGBA64LE; dst->width = width; dst->height = height;
  dst->color_range = AVCOL_RANGE_JPEG; dst->colorspace = AVCOL_SPC_RGB;
  dst->color_primaries = AVCOL_PRI_BT2020; dst->color_trc = AVCOL_TRC_SMPTE2084;
  if (av_frame_get_buffer (dst, 32) < 0 ||
      !pl_frame_recreate_from_avframe (s->vk->gpu, &destination, s->output, dst)) goto done;
  destination.color.hdr.min_luma = t->min_nits;
  destination.color.hdr.max_luma = t->max_nits;
  destination.color.hdr.prim = (struct pl_raw_primaries) {
    .red = {t->primaries[0], t->primaries[1]},
    .green = {t->primaries[2], t->primaries[3]},
    .blue = {t->primaries[4], t->primaries[5]},
    .white = {t->primaries[6], t->primaries[7]},
  };
  struct pl_render_params params = pl_render_default_params;
  params.dovi_map = provider_map; params.dovi_priv = s;
  params.dovi_signature = t->generation;
  s->mapped = 0;
  if (!pl_render_image (s->renderer, &source, &destination, &params)) goto done;
  if (s->mapped == 0) {
    /* Do not claim the stock fallback image is provider mapped. */
    success = TRUE; goto done;
  }
  if (s->mapped != 1 || !pl_download_avframe (s->vk->gpu, &destination, dst)) goto done;
  gst_video_info_set_format (output_info, GST_VIDEO_FORMAT_RGBA64_LE, width, height);
  output_info->colorimetry = (GstVideoColorimetry) {
    GST_VIDEO_COLOR_RANGE_0_255, GST_VIDEO_COLOR_MATRIX_RGB,
    GST_VIDEO_TRANSFER_SMPTE2084, GST_VIDEO_COLOR_PRIMARIES_BT2020
  };
  result = gst_buffer_new_allocate (NULL, output_info->size, NULL);
  GstVideoFrame out = {0};
  if (!result || !gst_video_frame_map (&out, output_info, result, GST_MAP_WRITE)) goto done;
  for (guint y = 0; y < height; y++)
    memcpy ((guint8 *) GST_VIDEO_FRAME_PLANE_DATA (&out, 0) + y * GST_VIDEO_FRAME_PLANE_STRIDE (&out, 0),
        dst->data[0] + y * dst->linesize[0], width * 8);
  gst_video_frame_unmap (&out);
  GST_BUFFER_PTS (result) = GST_BUFFER_PTS (input);
  GST_BUFFER_DTS (result) = GST_BUFFER_DTS (input);
  GST_BUFFER_DURATION (result) = GST_BUFFER_DURATION (input);
  *output = result; result = NULL; success = TRUE;
done:
  if (uploaded) pl_unmap_avframe (s->vk->gpu, &source);
  if (mapped.buffer) gst_video_frame_unmap (&mapped);
  gst_clear_buffer (&result); av_frame_free (&src); av_frame_free (&dst);
  if (!success) {
    g_set_error_literal (error, mapper_error (), 1, "Eligible Dolby frame normalization/mapping failed");
    return -1;
  }
  return *output ? 1 : 0;
}
