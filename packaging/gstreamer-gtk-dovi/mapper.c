/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "mapper.h"
#include "native-input-formats.h"
#include "gstdovipicture.h"
#include <dv_provider387.h>
#if !defined(DV_PROVIDER387_TARGET_V2_VERSION) || DV_PROVIDER387_TARGET_V2_VERSION != 2
#error "Dolby provider target API v2 headers are required"
#endif
/* Optional additive API: binaries remain loadable with the v1 runtime. */
#pragma weak dv_provider387_map_v2
#pragma weak dv_provider387_last_target_strategy
#include <libplacebo/vulkan.h>
#include <libplacebo/renderer.h>
#include <libplacebo/dispatch.h>
#include <libplacebo/shaders/sampling.h>
#include <libplacebo/shaders/colorspace.h>
#include <libplacebo/shaders/custom.h>
#include <libplacebo/utils/libav.h>
#include <libavutil/imgutils.h>
#include <libavutil/pixdesc.h>
#include <math.h>
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
_Static_assert (DV_PROVIDER387_ABI == 1, "Unsupported provider ABI");
struct GstGtkDoviMapper {
  pl_vulkan vk;
  pl_renderer renderer;
  pl_dispatch dispatch;
  pl_tex transport;
  struct pl_color_space physical;
  float transport_gain;
  struct dv_provider387 *provider;
  pl_tex source[4], enhancement[4], output[4], sdr_output[4];
  gboolean has_destination, last_sdr_destination;
  gboolean requires_fel;
  int mapped;
  guint warned;
  guint target_strategy_witness;
};
static int decline (GstGtkDoviMapper *s, guint bit, const char *reason)
{
  if (!(s->warned & bit)) { GST_WARNING ("GTK Dolby mapping declined: %s", reason); s->warned |= bit; }
  return 0;
}
static GQuark mapper_error (void) { return g_quark_from_static_string ("gtk-dovi-mapper"); }
static int provider_map (void *priv, pl_gpu gpu, const uint8_t *rpu, size_t size,
    bool composed, const struct pl_color_space *target, pl_tex master,
    pl_tex *mapped, struct pl_color_space *color)
{
  GstGtkDoviMapper *s = priv;
  if (s->requires_fel && !composed) return s->mapped = 0;
  guint strategy = 4; /* v1 runtime: complete named mapping */
  if (dv_provider387_map_v2) {
    s->mapped = dv_provider387_map_v2 (s->provider, gpu, rpu, size, composed,
        &s->physical, master, mapped, color, NULL);
    if (dv_provider387_last_target_strategy)
      strategy = dv_provider387_last_target_strategy (s->provider);
  } else {
    s->mapped = dv_provider387_map (s->provider, gpu, rpu, size, composed,
        &s->physical, master, mapped, color);
  }
  if (s->mapped == 1 && s->target_strategy_witness != strategy + 1) {
    static const char *const names[] = { "named", "raw-xy-neutral-cm4",
      "named-creative-fallback", "named-invalid-xy-fallback", "named-v1-runtime" };
    GST_INFO ("Dolby target strategy=%s", strategy < G_N_ELEMENTS (names) ?
        names[strategy] : "unknown");
    s->target_strategy_witness = strategy + 1;
  }
  if (s->mapped != 1) return s->mapped;
  if (s->requires_fel)
    GST_LOG ("Profile 7 provider accepted composed %dx%d master",
        master->params.w, master->params.h);
  if (s->transport_gain != 1.0f) {
    pl_fmt fmt = pl_find_fmt (gpu, PL_FMT_FLOAT, 4, 32, 0,
        PL_FMT_CAP_RENDERABLE | PL_FMT_CAP_SAMPLEABLE | PL_FMT_CAP_HOST_READABLE);
    if (!fmt || !pl_tex_recreate (gpu, &s->transport, pl_tex_params (
        .w = (*mapped)->params.w, .h = (*mapped)->params.h, .format = fmt,
        .sampleable = true, .renderable = true, .host_readable = true,
        .storable = fmt->caps & PL_FMT_CAP_STORABLE))) return s->mapped = -1;
    pl_shader sh = pl_dispatch_begin (s->dispatch);
    if (!pl_shader_sample_direct (sh, pl_sample_src (.tex = *mapped))) {
      pl_dispatch_abort (s->dispatch, &sh); return s->mapped = -1;
    }
    const struct pl_color_space pq = {.primaries = PL_COLOR_PRIM_BT_2020, .transfer = PL_COLOR_TRC_PQ};
    pl_shader_linearize (sh, &pq);
    struct pl_shader_var gain = {.var = pl_var_float ("dv_physical_transport_gain"),
        .data = &s->transport_gain, .dynamic = true};
    if (!pl_shader_custom (sh, &(struct pl_custom_shader) {
        .description = "physical DV to GTK PQ reference transport",
        .body = "color.rgb *= dv_physical_transport_gain;",
        .input = PL_SHADER_SIG_COLOR, .output = PL_SHADER_SIG_COLOR,
        .variables = &gain, .num_variables = 1})) {
      pl_dispatch_abort (s->dispatch, &sh); return s->mapped = -1;
    }
    pl_shader_delinearize (sh, &pq);
    if (!pl_dispatch_finish (s->dispatch, pl_dispatch_params (.shader = &sh, .target = s->transport)))
      return s->mapped = -1;
    *mapped = s->transport;
  }
  *color = *target;
  return s->mapped;
}
GstGtkDoviMapper *gst_gtk_dovi_mapper_new (void) { gst_gtk_dovi_debug_init (); return g_new0 (GstGtkDoviMapper, 1); }
void gst_gtk_dovi_mapper_free (GstGtkDoviMapper *s)
{
  if (!s) return;
  if (s->vk) {
    dv_provider387_destroy (&s->provider);
    pl_renderer_destroy (&s->renderer);
    pl_dispatch_destroy (&s->dispatch);
    pl_tex_destroy (s->vk->gpu, &s->transport);
    for (unsigned i = 0; i < 4; i++) {
      pl_tex_destroy (s->vk->gpu, &s->source[i]);
      pl_tex_destroy (s->vk->gpu, &s->enhancement[i]);
      pl_tex_destroy (s->vk->gpu, &s->output[i]);
      pl_tex_destroy (s->vk->gpu, &s->sdr_output[i]);
    }
    pl_vulkan_destroy (&s->vk);
  }
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
static int render_destination (GstGtkDoviMapper *s, GstBuffer *input,
    const GstVideoInfo *info, const GstGtkDoviTarget *t,
    GstBuffer **output, GstVideoInfo *output_info, GError **error, gboolean sdr)
{
  *output = NULL;
  GstDoviPictureMeta *meta = gst_buffer_get_dovi_picture_meta (input);
  const AVDOVIMetadata *resolved = meta && meta->picture ?
      gst_dovi_picture_get_metadata (meta->picture) : NULL;
  GBytes *raw = meta && meta->picture ? gst_dovi_picture_get_rpu (meta->picture) : NULL;
  guint width = GST_VIDEO_INFO_WIDTH (info), height = GST_VIDEO_INFO_HEIGHT (info);
  GstVideoCropMeta *crop = gst_buffer_get_video_crop_meta (input);
  enum AVPixelFormat format = input_format (GST_VIDEO_INFO_FORMAT (info));
  if (format == AV_PIX_FMT_NONE || GST_VIDEO_INFO_FORMAT (output_info) != (sdr ? GST_VIDEO_FORMAT_RGBA : GST_VIDEO_FORMAT_RGBA64_LE)) {
    g_set_error_literal (error, mapper_error (), 1, "Unsupported native plane import"); return -1;
  }
  GstVideoFrame mapped = {0};
  AVFrame *src = av_frame_alloc (), *dst = av_frame_alloc (), *converted = NULL;
  struct pl_frame source = {0}, enhancement = {0}, destination = {0};
  const AVFrame *fel = gst_dovi_picture_meta_get_fel (meta);
  gboolean el_uploaded = FALSE;
  gboolean uploaded = FALSE, success = FALSE;
  GstBuffer *result = NULL;
  if (!src || !dst || !gst_video_frame_map (&mapped, info, input, GST_MAP_READ)) goto done;
  guint storage_width = GST_VIDEO_FRAME_WIDTH (&mapped), storage_height = GST_VIDEO_FRAME_HEIGHT (&mapped);
  if (crop && (crop->x > storage_width || crop->y > storage_height ||
      crop->width != width || crop->height != height ||
      crop->width > storage_width - crop->x || crop->height > storage_height - crop->y)) goto done;
  gboolean native_yuv = format == AV_PIX_FMT_NV12 || format == AV_PIX_FMT_P010LE ||
      format == AV_PIX_FMT_YUV420P || format == AV_PIX_FMT_YUV420P10LE;
  gboolean apply_dovi = native_yuv && resolved && raw && t &&
      (sdr || (t->valid && t->render_ready && t->composed)) &&
      GST_VIDEO_INFO_INTERLACE_MODE (info) == GST_VIDEO_INTERLACE_MODE_PROGRESSIVE &&
      !GST_BUFFER_FLAG_IS_SET (input, GST_VIDEO_BUFFER_FLAG_INTERLACED) &&
      !GST_BUFFER_FLAG_IS_SET (input, GST_BUFFER_FLAG_CORRUPTED) &&
      !(info->chroma_site & GST_VIDEO_CHROMA_SITE_ALT_LINE) &&
      GST_VIDEO_INFO_COMP_DEPTH (info, 0) == av_dovi_get_header (resolved)->bl_bit_depth;
  if (apply_dovi) {
    guint native_width, native_height;
    gst_dovi_picture_get_dimensions (meta->picture, &native_width, &native_height);
    const GstDoviGeometry *geometry = gst_dovi_picture_get_geometry (meta->picture);
    const AVPixFmtDescriptor *desc = av_pix_fmt_desc_get (format);
    gboolean geometry_ok = geometry && native_width == width && native_height == height &&
        native_width == geometry->width && native_height == geometry->height;
    if (geometry_ok && crop) {
      geometry_ok = storage_width >= geometry->coded_width && storage_height >= geometry->coded_height &&
          crop->x == geometry->x && crop->y == geometry->y &&
          crop->width == geometry->width && crop->height == geometry->height &&
          !(crop->x & ((1u << desc->log2_chroma_w) - 1)) &&
          !(crop->y & ((1u << desc->log2_chroma_h) - 1)) &&
          !(crop->width & ((1u << desc->log2_chroma_w) - 1)) &&
          !(crop->height & ((1u << desc->log2_chroma_h) - 1));
    } else if (geometry_ok) {
      geometry_ok = storage_width == width && storage_height == height;
    }
    guint profile = gst_dovi_picture_get_profile (meta->picture);
    const AVDOVIDecoderConfigurationRecord *config = gst_dovi_picture_get_stream_config (meta->picture);
    GstDoviEnhancement residual = gst_dovi_picture_get_enhancement (meta->picture);
    gboolean paired_fel = profile == 7 && config && config->el_present_flag &&
        config->dv_bl_signal_compatibility_id == 6 &&
        residual == GST_DOVI_ENHANCEMENT_UNRECONSTRUCTED && fel;
    gboolean single_layer = config && !config->el_present_flag &&
        residual == GST_DOVI_ENHANCEMENT_NOT_REQUIRED &&
        ((profile == 5 && config->dv_bl_signal_compatibility_id == 0) ||
         (profile == 8 && config->dv_bl_signal_compatibility_id == 1));
    apply_dovi = (paired_fel || single_layer) && geometry_ok && config && config->dv_version_major == 1 && config->dv_version_minor == 0 &&
        config->dv_profile == profile && config->bl_present_flag && config->rpu_present_flag &&
        config->dv_md_compression == AV_DOVI_COMPRESSION_NONE;
    if (!apply_dovi) decline (s, 2, "per-picture metadata/geometry/enhancement unqualified; baseline conversion");
  }
  if (apply_dovi && (!isfinite (t->max_nits) || !isfinite (t->min_nits) ||
      t->max_nits <= (sdr ? 0 : 203) || t->min_nits < 0 || t->min_nits >= t->max_nits)) {
    apply_dovi = FALSE; decline (s, 32, "invalid/non-HDR surface target; baseline conversion");
  }
  /* Reuse the reviewed mpv physical transport law only for an actual PQ
   * buffer declaration with the standard203cd/m2 reference and10000maximum.
   * Creative trims use the physical target, never the normalized envelope. */
  if (apply_dovi) {
    double gain = ((double) PL_COLOR_SDR_WHITE / t->reference_nits) * (t->encoding_max_nits / 10000.0);
    double peak = t->max_nits * gain, black = t->min_nits * gain;
    apply_dovi = isfinite (t->reference_nits) && t->reference_nits > 0 &&
        t->encoding_reference_nits == PL_COLOR_SDR_WHITE && t->encoding_max_nits == 10000 &&
        isfinite (gain) && gain > 0 && isfinite (peak) && peak <= 10000 &&
        isfinite (black) && (t->min_nits == 0 || (float) black > 0);
    struct pl_raw_primaries prim = {
      .red = {t->primaries[0], t->primaries[1]}, .green = {t->primaries[2], t->primaries[3]},
      .blue = {t->primaries[4], t->primaries[5]}, .white = {t->primaries[6], t->primaries[7]},
    };
    for (guint i = 0; i < 8; i++) apply_dovi &= isfinite (t->primaries[i]);
    apply_dovi &= pl_primaries_valid (&prim);
    s->transport_gain = gain;
    if (!apply_dovi) decline (s, 128, "actual HDR render declaration/transport unqualified");
  }
  gboolean active_import = apply_dovi && crop;
  guint source_width = crop && !active_import ? storage_width : width;
  guint source_height = crop && !active_import ? storage_height : height;
  src->format = format; src->width = source_width; src->height = source_height;
  src->color_range = info->colorimetry.range == GST_VIDEO_COLOR_RANGE_0_255 ? AVCOL_RANGE_JPEG : AVCOL_RANGE_MPEG;
  src->color_primaries = gst_video_color_primaries_to_iso (info->colorimetry.primaries);
  src->color_trc = gst_video_transfer_function_to_iso (info->colorimetry.transfer);
  src->colorspace = gst_video_color_matrix_to_iso (info->colorimetry.matrix);
  gboolean rgb = av_pix_fmt_desc_get (format)->flags & AV_PIX_FMT_FLAG_RGB;
  if (info->colorimetry.primaries == GST_VIDEO_COLOR_PRIMARIES_UNKNOWN) src->color_primaries = AVCOL_PRI_BT709;
  if (info->colorimetry.transfer == GST_VIDEO_TRANSFER_UNKNOWN) src->color_trc = rgb ? AVCOL_TRC_IEC61966_2_1 : AVCOL_TRC_BT709;
  if (info->colorimetry.matrix == GST_VIDEO_COLOR_MATRIX_UNKNOWN) src->colorspace = rgb ? AVCOL_SPC_RGB : AVCOL_SPC_BT709;
  if (info->colorimetry.range == GST_VIDEO_COLOR_RANGE_UNKNOWN) src->color_range = rgb ? AVCOL_RANGE_JPEG : AVCOL_RANGE_MPEG;
  switch (info->chroma_site) {
    case GST_VIDEO_CHROMA_SITE_JPEG: src->chroma_location = AVCHROMA_LOC_CENTER; break;
    case GST_VIDEO_CHROMA_SITE_MPEG2: src->chroma_location = AVCHROMA_LOC_LEFT; break;
    case GST_VIDEO_CHROMA_SITE_COSITED: src->chroma_location = AVCHROMA_LOC_TOPLEFT; break;
    case GST_VIDEO_CHROMA_SITE_V_COSITED: src->chroma_location = AVCHROMA_LOC_TOP; break;
    default: src->chroma_location = AVCHROMA_LOC_UNSPECIFIED; break;
  }
  src->sample_aspect_ratio = (AVRational) {GST_VIDEO_INFO_PAR_N (info), GST_VIDEO_INFO_PAR_D (info)};
  if (av_frame_get_buffer (src, 32) < 0) goto done;
  const uint8_t *planes[4] = {0}; int strides[4] = {0};
  for (guint i = 0; i < GST_VIDEO_INFO_N_PLANES (info); i++) {
    planes[i] = GST_VIDEO_FRAME_PLANE_DATA (&mapped, i);
    strides[i] = GST_VIDEO_FRAME_PLANE_STRIDE (&mapped, i);
    if (active_import) {
      const GstVideoFormatInfo *finfo = info->finfo;
      guint component = 0;
      while (component < GST_VIDEO_FORMAT_INFO_N_COMPONENTS (finfo) &&
          GST_VIDEO_FORMAT_INFO_PLANE (finfo, component) != i) component++;
      if (component == GST_VIDEO_FORMAT_INFO_N_COMPONENTS (finfo)) goto done;
      planes[i] += (ptrdiff_t) (crop->y >> GST_VIDEO_FORMAT_INFO_H_SUB (finfo, component)) * strides[i] +
          (crop->x >> GST_VIDEO_FORMAT_INFO_W_SUB (finfo, component)) * GST_VIDEO_FORMAT_INFO_PSTRIDE (finfo, component);
    }
  }
  av_image_copy (src->data, src->linesize, planes, strides, format, source_width, source_height);
  if (!s->vk) {
    s->vk = pl_vulkan_create (NULL, pl_vulkan_params (.allow_software = true));
    if (!s->vk) goto done;
    PFN_vkGetPhysicalDeviceProperties get_properties =
        (PFN_vkGetPhysicalDeviceProperties) s->vk->get_proc_addr (s->vk->instance, "vkGetPhysicalDeviceProperties");
    if (get_properties) {
      VkPhysicalDeviceProperties properties;
      get_properties (s->vk->phys_device, &properties);
      GST_INFO ("native mapper Vulkan device vendor=%04x device=%04x type=%u name=%s",
          properties.vendorID, properties.deviceID, properties.deviceType, properties.deviceName);
    }
    s->dispatch = pl_dispatch_create (NULL, s->vk->gpu);
    s->renderer = pl_renderer_create (NULL, s->vk->gpu);
  }
  if (!s->renderer || !s->dispatch) goto done;
  if (apply_dovi && !s->provider) s->provider = dv_provider387_create (s->vk->gpu, NULL);
  if (apply_dovi && !s->provider) goto done;
  if (!pl_map_avframe_ex (s->vk->gpu, &source,
      pl_avframe_params (.frame = src, .tex = s->source, .map_dovi = false))) goto done;
  uploaded = TRUE;
  if (crop && !active_import)
    source.crop = (struct pl_rect2df) {crop->x, crop->y, crop->x + crop->width, crop->y + crop->height};
  struct pl_frame baseline = source;
  struct pl_dovi_metadata dovi;
  if (apply_dovi) {
    pl_map_avdovi_metadata (&source.color, &source.repr, &dovi, resolved);
    if (fel) {
      if (dovi.nlq_active && pl_map_avframe_ex (s->vk->gpu, &enhancement,
          pl_avframe_params (.frame = fel, .tex = s->enhancement, .map_dovi = false))) {
        el_uploaded = TRUE;
        source.enhancement_layer = &enhancement;
      } else {
        apply_dovi = FALSE;
        source = baseline;
        decline (s, 256, "matched enhancement planes or NLQ unavailable");
      }
    }
  }
  if (apply_dovi) {
    gsize raw_size;
    source.dovi_rpu = g_bytes_get_data (raw, &raw_size);
    source.dovi_rpu_size = raw_size;
    source.dovi_master_width = width; source.dovi_master_height = height;
  }
  dst->format = AV_PIX_FMT_RGBA64LE; dst->width = GST_VIDEO_INFO_WIDTH (output_info); dst->height = GST_VIDEO_INFO_HEIGHT (output_info);
  dst->color_range = output_info->colorimetry.range == GST_VIDEO_COLOR_RANGE_0_255 ? AVCOL_RANGE_JPEG : AVCOL_RANGE_MPEG;
  dst->colorspace = AVCOL_SPC_RGB;
  dst->color_primaries = AVCOL_PRI_BT2020; dst->color_trc = AVCOL_TRC_SMPTE2084;
  if (av_frame_get_buffer (dst, 32) < 0 ||
      !pl_frame_recreate_from_avframe (s->vk->gpu, &destination, s->output, dst)) goto done;
  for (int i = 0; i < destination.num_planes; i++) {
    const float zero[4] = {0}; pl_tex_clear (s->vk->gpu, destination.planes[i].texture, zero);
  }
  struct pl_color_space baseline_destination = destination.color;
  struct pl_render_params params = pl_render_default_params;
  if (apply_dovi) {
    destination.color.hdr.min_luma = t->min_nits;
    destination.color.hdr.max_luma = t->max_nits;
    destination.color.hdr.prim = (struct pl_raw_primaries) {
      .red = {t->primaries[0], t->primaries[1]}, .green = {t->primaries[2], t->primaries[3]},
      .blue = {t->primaries[4], t->primaries[5]}, .white = {t->primaries[6], t->primaries[7]},
    };
    s->physical = destination.color;
    destination.color.hdr.min_luma *= s->transport_gain;
    destination.color.hdr.max_luma *= s->transport_gain;
    params.dovi_map = provider_map; params.dovi_priv = s;
    params.dovi_signature = t->generation;
  }
  s->requires_fel = apply_dovi && fel;
  s->mapped = 0;
  if (!pl_render_image (s->renderer, &source, &destination, &params)) goto done;
  if (apply_dovi && s->mapped == 0) {
    /* The provider can decline compressed/unqualified creative metadata.
     * Reproduce the ordinary input interpretation, then encode it as PQ;
     * do not call a normalized-but-ungraded image the stock fallback. */
    decline (s, 64, "provider declined; ordinary baseline re-encoding");
    params.dovi_map = NULL; params.dovi_priv = NULL;
    destination.color = baseline_destination;
    if (!pl_render_image (s->renderer, &baseline, &destination, &params)) goto done;
  }
  if (s->mapped < 0) goto done;
  AVFrame *final = dst;
  enum AVPixelFormat output_format = AV_PIX_FMT_RGBA64LE;
  if (sdr) {
    converted = av_frame_alloc ();
    if (!converted) goto done;
    converted->format = AV_PIX_FMT_RGBA;
    converted->width = dst->width; converted->height = dst->height;
    converted->color_range = AVCOL_RANGE_JPEG; converted->colorspace = AVCOL_SPC_RGB;
    converted->color_primaries = AVCOL_PRI_BT709;
    converted->color_trc = AVCOL_TRC_IEC61966_2_1;
    struct pl_frame sdr_destination = {0};
    if (av_frame_get_buffer (converted, 32) < 0 ||
        !pl_frame_recreate_from_avframe (s->vk->gpu, &sdr_destination,
            s->sdr_output, converted)) goto done;
    pl_shader sh = pl_dispatch_begin (s->dispatch);
    if (!pl_shader_sample_direct (sh,
        pl_sample_src (.tex = destination.planes[0].texture))) {
      pl_dispatch_abort (s->dispatch, &sh); goto done;
    }
    const struct pl_color_space pq = {
      .primaries = PL_COLOR_PRIM_BT_2020, .transfer = PL_COLOR_TRC_PQ};
    const struct pl_color_space srgb = {
      .primaries = PL_COLOR_PRIM_BT_709, .transfer = PL_COLOR_TRC_SRGB};
    /* Public D65 Rec.2020 -> Rec.709 linear matrix. The explicit100nit target
     * is normalized by the existing PQ transport law; gamut conversion occurs
     * before clipping and the sRGB transfer is applied exactly once. */
    pl_shader_linearize (sh, &pq);
    if (!pl_shader_custom (sh, &(struct pl_custom_shader) {
        .description = "explicit100nit BT709 SDR video destination",
        .body = "color.rgb = clamp(mat3(1.6604910021, -0.1245504745, -0.0181507634, "
                "-0.5876411388, 1.1328998971, -0.1005788980, "
                "-0.0728498633, -0.0083494226, 1.1187296614) * color.rgb, 0.0, 1.0);",
        .input = PL_SHADER_SIG_COLOR, .output = PL_SHADER_SIG_COLOR})) {
      pl_dispatch_abort (s->dispatch, &sh); goto done;
    }
    pl_shader_delinearize (sh, &srgb);
    if (!pl_dispatch_finish (s->dispatch, pl_dispatch_params (
        .shader = &sh, .target = sdr_destination.planes[0].texture)) ||
        !pl_download_avframe (s->vk->gpu, &sdr_destination, converted)) goto done;
    final = converted; output_format = AV_PIX_FMT_RGBA;
  } else if (!pl_download_avframe (s->vk->gpu, &destination, dst)) goto done;
  result = gst_buffer_new_allocate (NULL, output_info->size, NULL);
  GstVideoFrame out = {0};
  if (!result || !gst_video_frame_map (&out, output_info, result, GST_MAP_WRITE)) goto done;
  uint8_t *out_planes[4] = {0}; int out_strides[4] = {0};
  for (guint i = 0; i < GST_VIDEO_INFO_N_PLANES (output_info); i++) {
    out_planes[i] = GST_VIDEO_FRAME_PLANE_DATA (&out, i);
    out_strides[i] = GST_VIDEO_FRAME_PLANE_STRIDE (&out, i);
  }
  av_image_copy (out_planes, out_strides, (const uint8_t **) final->data,
      final->linesize, output_format, final->width, final->height);
  gst_video_frame_unmap (&out);
  gst_buffer_copy_into (result, input, GST_BUFFER_COPY_FLAGS | GST_BUFFER_COPY_TIMESTAMPS, 0, -1);
  *output = result; result = NULL; success = TRUE;
done:
  if (el_uploaded) pl_unmap_avframe (s->vk->gpu, &enhancement);
  if (uploaded) pl_unmap_avframe (s->vk->gpu, &source);
  if (mapped.buffer) gst_video_frame_unmap (&mapped);
  gst_clear_buffer (&result); av_frame_free (&src); av_frame_free (&dst); av_frame_free (&converted);
  if (!success) {
    g_set_error_literal (error, mapper_error (), 1, "Eligible Dolby frame normalization/mapping failed");
    return -1;
  }
  return s->mapped == 1 ? 1 : 2;
}

int gst_gtk_dovi_mapper_render_destination (GstGtkDoviMapper *self,
    GstBuffer *input, const GstVideoInfo *info, GstGtkDoviDestinationKind kind,
    const GstGtkDoviTarget *physical, GstBuffer **output,
    GstVideoInfo *output_info, GError **error)
{
  *output = NULL;
  gboolean sdr = kind == GST_GTK_DOVI_DESTINATION_STANDARD_SDR_SRGB;
  if (!sdr && kind != GST_GTK_DOVI_DESTINATION_DISPLAY_PQ) {
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
  if (self->has_destination && self->last_sdr_destination != sdr &&
      self->renderer)
    pl_renderer_flush_cache (self->renderer);
  self->has_destination = TRUE;
  self->last_sdr_destination = sdr;
  if (!sdr)
    return render_destination (self, input, info, physical, output,
        output_info, error, FALSE);
  /* An explicit logical destination, independent of native surface feedback.
   * Native validity/composition/readiness fields deliberately remain false. */
  const GstGtkDoviTarget logical = {
    .generation = 1, .primaries = {.64,.33,.30,.60,.15,.06,.3127,.3290},
    .min_nits = 0, .max_nits = 100, .reference_nits = 100,
    .encoding_reference_nits = 203, .encoding_max_nits = 10000,
  };
  return render_destination (self, input, info, &logical, output,
      output_info, error, TRUE);
}

int gst_gtk_dovi_mapper_render (GstGtkDoviMapper *self, GstBuffer *input,
    const GstVideoInfo *info, const GstGtkDoviTarget *physical,
    GstBuffer **output, GstVideoInfo *output_info, GError **error)
{
  return gst_gtk_dovi_mapper_render_destination (self, input, info,
      GST_GTK_DOVI_DESTINATION_DISPLAY_PQ, physical, output, output_info, error);
}
