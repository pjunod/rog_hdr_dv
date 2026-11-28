/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Decode picture N of a clear Dolby Vision MP4 with FFmpeg, map it through
 * librog-dovi-map and write the output rows to a new file.
 *
 * usage: core-map-dump ROUTE INPUT_NODE OUTPUT_NODE FILE N pq|sdr PEAK MIN REF OUT
 *   ROUTE       dmabuf (VA-API picture as DRM-PRIME planes), host-p010 (the
 *               VA-API picture copied to host memory) or software (FFmpeg's
 *               software decoder, host planes)
 *   INPUT_NODE  /dev/dri/renderD* or "none"; the VA-API decode device too
 *   OUTPUT_NODE /dev/dri/renderD* (core-allocated linear DMABuf output) or
 *               "none" (host output in the caller's memory)
 * Output rows: RGBA64LE-ordered ABGR16161616 for pq, ABGR8888 (RGBA bytes)
 * for sdr. PROBE_FOURCC=2101010 renders DRM_FORMAT_ABGR2101010 instead and
 * writes its 32-bit words. PROBE_KEEP=1 creates the mappers with
 * ROG_DOVI_MAPPER_KEEP_DEVICE; PROBE_NO_PROFILES=1 skips the profile query. */
#define _GNU_SOURCE
#include "rog-dovi-map.h"
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/hwcontext.h>
#include <libavutil/hwcontext_drm.h>
#include <libavutil/dovi_meta.h>
#include <libavutil/pixdesc.h>
#include <drm_fourcc.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

static enum AVPixelFormat pick_vaapi (AVCodecContext *c, const enum AVPixelFormat *f)
{
  (void) c;
  for (; *f != AV_PIX_FMT_NONE; f++) if (*f == AV_PIX_FMT_VAAPI) return *f;
  return AV_PIX_FMT_NONE;
}
static uint64_t node_of (const char *path)
{
  struct stat st;
  return strcmp (path, "none") && !stat (path, &st) ? (uint64_t) st.st_rdev : 0;
}
static void log_cb (void *user, int level, const char *message)
{
  (void) user;
  fprintf (stderr, "[core %d] %s\n", level, message);
}
static uint8_t *host_rows;
static int32_t host_stride;
static int acquire (void *user, void **data, int32_t *stride)
{
  (void) user; *data = host_rows; *stride = host_stride; return 1;
}

int main (int argc, char **argv)
{
  if (argc != 11) { fprintf (stderr, "usage: see source\n"); return 2; }
  const char *route = argv[1], *outpath = argv[10];
  bool sdr = !strcmp (argv[6], "sdr");
  int want = atoi (argv[5]);
  if (rog_dovi_map_abi () != ROG_DOVI_MAP_ABI) { fprintf (stderr, "core ABI mismatch\n"); return 2; }
  rog_dovi_map_set_log (log_cb, NULL, getenv ("PROBE_LOG") ? atoi (getenv ("PROBE_LOG")) : ROG_DOVI_LOG_INFO);
  AVFormatContext *fmt = NULL;
  if (avformat_open_input (&fmt, argv[4], NULL, NULL) < 0 || avformat_find_stream_info (fmt, NULL) < 0) return 3;
  int si = av_find_best_stream (fmt, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
  AVStream *st = fmt->streams[si];
  const AVPacketSideData *conf = av_packet_side_data_get (st->codecpar->coded_side_data,
      st->codecpar->nb_coded_side_data, AV_PKT_DATA_DOVI_CONF);
  if (!conf) { fprintf (stderr, "no Dolby configuration\n"); return 4; }
  const AVDOVIDecoderConfigurationRecord *cfg = (const void *) conf->data;
  const AVCodec *codec = avcodec_find_decoder (st->codecpar->codec_id);
  AVCodecContext *dec = avcodec_alloc_context3 (codec);
  avcodec_parameters_to_context (dec, st->codecpar);
  bool vaapi = strcmp (route, "software");
  if (vaapi) {
    AVBufferRef *hw = NULL;
    if (av_hwdevice_ctx_create (&hw, AV_HWDEVICE_TYPE_VAAPI, argv[2], NULL, 0) < 0) return 5;
    dec->hw_device_ctx = hw;
    dec->get_format = pick_vaapi;
  }
  if (avcodec_open2 (dec, codec, NULL) < 0) return 6;
  AVPacket *pkt = av_packet_alloc ();
  AVFrame *frame = av_frame_alloc ();
  int n = 0, got = 0;
  while (!got && av_read_frame (fmt, pkt) >= 0) {
    if (pkt->stream_index == si && avcodec_send_packet (dec, pkt) >= 0)
      while (!got && avcodec_receive_frame (dec, frame) >= 0) { if (n++ == want) got = 1; else av_frame_unref (frame); }
    av_packet_unref (pkt);
  }
  if (!got) { avcodec_send_packet (dec, NULL);
    while (!got && avcodec_receive_frame (dec, frame) >= 0) { if (n++ == want) got = 1; else av_frame_unref (frame); } }
  if (!got) return 7;
  AVFrameSideData *rpu = av_frame_get_side_data (frame, AV_FRAME_DATA_DOVI_RPU_BUFFER);
  AVFrameSideData *meta = av_frame_get_side_data (frame, AV_FRAME_DATA_DOVI_METADATA);
  if (!rpu || !meta) { fprintf (stderr, "picture has no Dolby side data\n"); return 8; }
  struct rog_dovi_picture pic = {.struct_size = sizeof (pic), .libavutil_version = LIBAVUTIL_VERSION_INT,
    .rpu = rpu->data, .rpu_size = rpu->size, .metadata = meta->data, .metadata_size = meta->size,
    .has_config = 1, .config = {
      .version_major = cfg->dv_version_major, .version_minor = cfg->dv_version_minor,
      .profile = cfg->dv_profile, .level = cfg->dv_level, .rpu_present = cfg->rpu_present_flag,
      .el_present = cfg->el_present_flag, .bl_present = cfg->bl_present_flag,
      .bl_signal_compatibility_id = cfg->dv_bl_signal_compatibility_id,
      .md_compression = cfg->dv_md_compression},
    .profile = cfg->dv_profile, .enhancement = ROG_DOVI_ENHANCEMENT_NOT_REQUIRED,
    .width = frame->width, .height = frame->height, .has_geometry = 1,
    .geometry = {frame->width, frame->height, 0, 0, frame->width, frame->height}};
  struct rog_dovi_mapper_params params = {.struct_size = sizeof (params),
    .flags = getenv ("PROBE_KEEP") ? ROG_DOVI_MAPPER_KEEP_DEVICE : 0,
    .input_node = node_of (argv[2]), .output_node = node_of (argv[3])};
  if (!getenv ("PROBE_NO_PROFILES"))
    fprintf (stderr, "profiles mask 0x%x\n", rog_dovi_map_profiles (&params));
  struct rog_dovi_target t = {.struct_size = sizeof (t),
    .flags = ROG_DOVI_TARGET_VALID | ROG_DOVI_TARGET_COMPOSED | ROG_DOVI_TARGET_RENDER_READY,
    .generation = 1, .primaries = {0.708, 0.292, 0.170, 0.797, 0.131, 0.046, 0.3127, 0.3290},
    .max_nits = atof (argv[7]), .min_nits = atof (argv[8]), .reference_nits = atof (argv[9]),
    .encoding_reference_nits = 203, .encoding_max_nits = 10000};
  bool ten = getenv ("PROBE_FOURCC") && !strcmp (getenv ("PROBE_FOURCC"), "2101010");
  uint32_t pixel = sdr || ten ? 4 : 8;
  uint64_t linear = DRM_FORMAT_MOD_LINEAR;
  struct rog_dovi_output out = {.struct_size = sizeof (out), .width = frame->width, .height = frame->height};
  if (params.output_node) {
    out.kind = ROG_DOVI_OUTPUT_DMABUF;
    out.drm_fourcc = ten ? DRM_FORMAT_ABGR2101010 : sdr ? DRM_FORMAT_ABGR8888 : DRM_FORMAT_ABGR16161616;
    out.modifiers = &linear; out.num_modifiers = 1;
  } else {
    out.kind = ROG_DOVI_OUTPUT_HOST;
    out.host_format = sdr ? ROG_DOVI_FORMAT_RGBA : ROG_DOVI_FORMAT_RGBA64LE;
    out.color_range = AVCOL_RANGE_JPEG;
    out.acquire = acquire;
    host_stride = frame->width * pixel;
    host_rows = calloc ((size_t) host_stride, frame->height);
  }
  rog_dovi_mapper *m = rog_dovi_mapper_new (&params);
  const char *err = NULL;
  int r = -1;
  AVFrame *host = NULL, *drm = NULL;
  if (!strcmp (route, "dmabuf")) {
    drm = av_frame_alloc (); drm->format = AV_PIX_FMT_DRM_PRIME;
    if (av_hwframe_map (drm, frame, AV_HWFRAME_MAP_READ) < 0) return 9;
    const AVDRMFrameDescriptor *d = (const void *) drm->data[0];
    struct rog_dovi_dmabuf in = {.struct_size = sizeof (in), .width = frame->width, .height = frame->height,
      .color_range = frame->color_range, .colorspace = frame->colorspace,
      .color_primaries = frame->color_primaries, .color_trc = frame->color_trc,
      .chroma_location = frame->chroma_location};
    for (int l = 0; l < d->nb_layers; l++)
      for (int p = 0; p < d->layers[l].nb_planes && in.num_planes < 4; p++, in.num_planes++) {
        const AVDRMPlaneDescriptor *pd = &d->layers[l].planes[p];
        in.planes[in.num_planes] = (struct rog_dovi_dmabuf_plane) {d->objects[pd->object_index].fd,
            (uint32_t) pd->offset, (uint32_t) pd->pitch};
        in.modifier = d->objects[pd->object_index].format_modifier;
      }
    in.drm_fourcc = d->nb_layers == 1 ? d->layers[0].format :
        (d->layers[0].format == DRM_FORMAT_R16 ? DRM_FORMAT_P010 : DRM_FORMAT_NV12);
    fprintf (stderr, "dmabuf %ux%u %.4s modifier 0x%llx planes %u\n", in.width, in.height,
        (char *) &in.drm_fourcc, (unsigned long long) in.modifier, in.num_planes);
    r = rog_dovi_map_dmabuf (m, &in, NULL, &pic, sdr ? ROG_DOVI_DESTINATION_STANDARD_SDR_SRGB :
        ROG_DOVI_DESTINATION_DISPLAY_PQ, &t, &out, 0, &err);
  } else {
    const AVFrame *planes_frame = frame;
    if (vaapi) {
      host = av_frame_alloc ();
      if (av_hwframe_transfer_data (host, frame, 0) < 0 || av_frame_copy_props (host, frame) < 0) return 10;
      planes_frame = host;
    }
    uint32_t f = planes_frame->format == AV_PIX_FMT_P010LE ? ROG_DOVI_FORMAT_P010LE :
        planes_frame->format == AV_PIX_FMT_YUV420P10LE ? ROG_DOVI_FORMAT_YUV420P10LE :
        planes_frame->format == AV_PIX_FMT_NV12 ? ROG_DOVI_FORMAT_NV12 :
        planes_frame->format == AV_PIX_FMT_YUV420P ? ROG_DOVI_FORMAT_YUV420P : ROG_DOVI_FORMAT_NONE;
    struct rog_dovi_planes in = {.struct_size = sizeof (in), .format = f,
      .storage_width = planes_frame->width, .storage_height = planes_frame->height,
      .width = planes_frame->width, .height = planes_frame->height,
      .color_range = frame->color_range, .colorspace = frame->colorspace,
      .color_primaries = frame->color_primaries, .color_trc = frame->color_trc,
      .chroma_location = frame->chroma_location,
      .sar_num = frame->sample_aspect_ratio.num, .sar_den = frame->sample_aspect_ratio.den};
    for (int i = 0; i < 4; i++) { in.data[i] = planes_frame->data[i]; in.stride[i] = planes_frame->linesize[i]; }
    fprintf (stderr, "planes %s %ux%u\n", av_get_pix_fmt_name (planes_frame->format), in.width, in.height);
    r = rog_dovi_map_planes (m, &in, NULL, &pic, sdr ? ROG_DOVI_DESTINATION_STANDARD_SDR_SRGB :
        ROG_DOVI_DESTINATION_DISPLAY_PQ, &t, &out, 0, &err);
  }
  uint32_t declined = rog_dovi_map_last_decline (m);
  fprintf (stderr, "route %s map result %d declined 0x%x%s%s\n", route, r, declined,
      err ? ": " : "", err ? err : "");
  for (uint32_t bit = 1; bit <= 1024; bit <<= 1)
    if (declined & bit) fprintf (stderr, "  decline: %s\n", rog_dovi_map_decline_reason (bit));
  if (r != 1) return 12;
  FILE *o = fopen (outpath, "wbx");
  if (!o) return 14;
  if (out.kind == ROG_DOVI_OUTPUT_DMABUF) {
    fprintf (stderr, "output modifier 0x%llx pitch %u offset %u\n", (unsigned long long) out.modifier,
        out.planes[0].pitch, out.planes[0].offset);
    if (out.modifier != DRM_FORMAT_MOD_LINEAR) return 13;
    size_t size = (size_t) out.planes[0].pitch * out.height + out.planes[0].offset;
    uint8_t *px = mmap (NULL, size, PROT_READ, MAP_SHARED, out.planes[0].fd, 0);
    if (px == MAP_FAILED) return 13;
    for (uint32_t y = 0; y < out.height; y++)
      fwrite (px + out.planes[0].offset + (size_t) y * out.planes[0].pitch, pixel, out.width, o);
    munmap (px, size);
    close (out.planes[0].fd);
  } else {
    for (uint32_t y = 0; y < out.height; y++)
      fwrite (host_rows + (size_t) y * host_stride, pixel, out.width, o);
  }
  fclose (o);
  rog_dovi_mapper_reset (m);
  rog_dovi_mapper_free (m);
  printf ("{\"width\": %u, \"height\": %u, \"result\": %d}\n", out.width, out.height, r);
  av_frame_free (&host); av_frame_free (&drm); av_frame_free (&frame);
  av_packet_free (&pkt); avcodec_free_context (&dec); avformat_close_input (&fmt);
  free (host_rows);
  return 0;
}
