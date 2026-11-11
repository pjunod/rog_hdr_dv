/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "gstdovipicture-private.h"
#include <libavcodec/avcodec.h>
#include <string.h>

/* Allow the BL and EL DPBs (16 pictures each), plus the current AU. */
#define MAX_PENDING 33
struct _GstDoviFelDecoder {
  AVCodecContext *codec;
  GQueue ready;
};

static void drop_frame (gpointer data) {
  AVFrame *frame = data;
  av_frame_free (&frame);
}

GstDoviFelDecoder *gst_dovi_fel_decoder_new (void) {
  return g_new0 (GstDoviFelDecoder, 1);
}

void gst_dovi_fel_decoder_reset (GstDoviFelDecoder *s) {
  if (!s) return;
  avcodec_free_context (&s->codec);
  g_queue_clear_full (&s->ready, drop_frame);
}

void gst_dovi_fel_decoder_free (GstDoviFelDecoder *s) {
  gst_dovi_fel_decoder_reset (s);
  g_free (s);
}

static void release_picture (void *unused, uint8_t *data) {
  (void) unused;
  gst_dovi_picture_unref ((GstDoviPicture *) data);
}

static gboolean open_decoder (GstDoviFelDecoder *s) {
  const AVCodec *codec = avcodec_find_decoder_by_name ("hevc");
  if (!codec || !(s->codec = avcodec_alloc_context3 (codec))) return FALSE;
  s->codec->flags |= AV_CODEC_FLAG_COPY_OPAQUE;
  s->codec->err_recognition = AV_EF_EXPLODE | AV_EF_CAREFUL;
  s->codec->max_pixels = 2048 * 1088;
  s->codec->apply_cropping = 0;
  /* Frame threads add unnecessary display latency alongside NVDEC. */
  s->codec->thread_count = 2;
  s->codec->thread_type = FF_THREAD_SLICE;
  return avcodec_open2 (s->codec, codec, NULL) >= 0;
}

static gboolean supported_frame (AVFrame *frame, GstDoviPicture *picture) {
  const GstDoviGeometry *g = gst_dovi_picture_get_geometry (picture);
  /* Only the half-resolution progressive Main10 FEL layout is supported.
   * Restrict crops to right/bottom padding on both layers. */
  return !(frame->flags & (AV_FRAME_FLAG_CORRUPT | AV_FRAME_FLAG_INTERLACED |
          AV_FRAME_FLAG_DISCARD)) && !frame->decode_error_flags &&
      frame->format == AV_PIX_FMT_YUV420P10LE && !frame->crop_left && !frame->crop_top &&
      !g->x && !g->y && av_frame_apply_cropping (frame, 0) >= 0 &&
      frame->width > 0 && frame->height > 0 && !(g->width & 1) && !(g->height & 1) &&
      (guint) frame->width == g->width / 2 && (guint) frame->height == g->height / 2;
}

static gboolean receive_frames (GstDoviFelDecoder *s) {
  for (;;) {
    AVFrame *frame = av_frame_alloc ();
    if (!frame) return FALSE;
    int ret = avcodec_receive_frame (s->codec, frame);
    if (ret < 0) {
      av_frame_free (&frame);
      return ret == AVERROR (EAGAIN) || ret == AVERROR_EOF;
    }
    const AVBufferRef *token = frame->opaque_ref;
    if (!token || !supported_frame (frame, (GstDoviPicture *) token->data)) {
      av_frame_free (&frame);
      return FALSE;
    }
    if (s->ready.length == MAX_PENDING)
      drop_frame (g_queue_pop_head (&s->ready));
    g_queue_push_tail (&s->ready, frame);
  }
}

void gst_dovi_fel_decoder_submit (GstDoviFelDecoder *s, GstBuffer *au,
    const GstVideoCodecState *state, GstDoviPicture *picture) {
  if (!s) return;
  const AVDOVIDecoderConfigurationRecord *config = picture ?
      gst_dovi_picture_get_stream_config (picture) : NULL;
  const AVDOVIRpuDataHeader *h = picture ?
      av_dovi_get_header (gst_dovi_picture_get_metadata (picture)) : NULL;
  if (!config || config->dv_profile != 7 || !config->el_present_flag ||
      !h->el_spatial_resampling_filter_flag || h->disable_residual_flag ||
      h->el_bit_depth != 10 || h->bl_bit_depth != 10 || h->vdr_bit_depth != 12 ||
      GST_BUFFER_FLAG_IS_SET (au, GST_BUFFER_FLAG_CORRUPTED)) {
    gst_dovi_fel_decoder_reset (s);
    return;
  }
  gboolean irap;
  GBytes *bytes = gst_dovi_extract_fel (au, state, picture, &irap);
  AVPacket *pkt = NULL;
  gboolean ok = FALSE;
  if (!bytes || (!s->codec && (!irap || !open_decoder (s)))) goto done;
  gsize size;
  const guint8 *data = g_bytes_get_data (bytes, &size);
  pkt = av_packet_alloc ();
  if (!pkt || av_new_packet (pkt, size) < 0) goto done;
  memcpy (pkt->data, data, size);
  if (irap) pkt->flags |= AV_PKT_FLAG_KEY;
  /* Copy opaque propagates the actual access-unit identity through HEVC
   * reorder, including duplicate/missing media timestamps and seek replay. */
  pkt->opaque_ref = av_buffer_create ((guint8 *) picture, 1, release_picture, NULL,
      AV_BUFFER_FLAG_READONLY);
  if (!pkt->opaque_ref) goto done;
  gst_dovi_picture_ref (picture);
  ok = avcodec_send_packet (s->codec, pkt) >= 0 && receive_frames (s);
done:
  av_packet_free (&pkt);
  g_clear_pointer (&bytes, g_bytes_unref);
  if (!ok) gst_dovi_fel_decoder_reset (s);
}

void gst_dovi_fel_decoder_drain (GstDoviFelDecoder *s) {
  if (s && s->codec) {
    if (avcodec_send_packet (s->codec, NULL) < 0 || !receive_frames (s))
      gst_dovi_fel_decoder_reset (s);
    else
      avcodec_free_context (&s->codec);
  }
}

GstDoviPictureMeta *gst_dovi_fel_decoder_add_picture_meta (GstDoviFelDecoder *s,
    GstBuffer *buffer, GstDoviPicture *picture) {
  AVFrame *matched = NULL;
  for (GList *it = s ? s->ready.head : NULL; it; it = it->next) {
    AVFrame *frame = it->data;
    if ((GstDoviPicture *) frame->opaque_ref->data == picture) {
      g_queue_delete_link (&s->ready, it);
      av_buffer_unref (&frame->opaque_ref);
      matched = frame;
      break;
    }
  }
  return gst_dovi_add_meta_take_frame (buffer, picture, matched);
}
