/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* CPU-only storage regression; the included implementation is section-GC'd so
 * this executable links only GStreamer video and libavutil, not a GPU backend. */
#include "../mapper.c"

static GstVideoInfo layout (GstVideoFormat format, gint stride, gsize offset, gsize size)
{
  GstVideoInfo info;
  gst_video_info_set_format (&info, format, 4, 3);
  info.stride[0] = stride; info.offset[0] = offset; info.size = size;
  return info;
}
static void checked_spans (void)
{
  GstVideoInfo info = layout (GST_VIDEO_FORMAT_RGBA64_LE, 32, 0, 96);
  g_assert_true (valid_output_span (&info));
  info = layout (GST_VIDEO_FORMAT_RGBA64_LE, 40, 8, 120);
  g_assert_true (valid_output_span (&info));
  info.size = 119;
  g_assert_false (valid_output_span (&info));
  info = layout (GST_VIDEO_FORMAT_RGBA64_LE, -32, 64, 96);
  g_assert_true (valid_output_span (&info));
  info.offset[0] = 63;
  g_assert_false (valid_output_span (&info));
  info = layout (GST_VIDEO_FORMAT_RGBA64_LE, 24, 0, 96);
  g_assert_false (valid_output_span (&info));
  info = layout (GST_VIDEO_FORMAT_RGBA64_LE, G_MININT, 0, 96);
  g_assert_false (valid_output_span (&info));
  info = layout (GST_VIDEO_FORMAT_RGBA64_LE, 32, G_MAXSIZE, 96);
  g_assert_false (valid_output_span (&info));
  info = layout (GST_VIDEO_FORMAT_RGBA64_LE, G_MAXINT, 0, G_MAXUINT);
  info.height = G_MAXINT;
  g_assert_false (valid_output_span (&info));
  info = layout (GST_VIDEO_FORMAT_RGBA, 16, 0, 48);
  g_assert_true (valid_output_span (&info));
}
static void gpu_pitch_selection (void)
{
  g_assert_true (download_row_pitch_ok (32, 8, 32));
  g_assert_true (download_row_pitch_ok (40, 8, 32));
  g_assert_false (download_row_pitch_ok (36, 8, 32));
  g_assert_false (download_row_pitch_ok (-32, 8, 32));
  g_assert_false (download_row_pitch_ok (0, 8, 32));
  g_assert_false (download_row_pitch_ok (16, 8, 32));
  g_assert_false (download_row_pitch_ok (32, 0, 32));
  g_assert_true (download_row_pitch_ok (16, 4, 16));
}
static void fallback_pixels (void)
{
  AVFrame *source = av_frame_alloc ();
  g_assert_nonnull (source);
  source->format = AV_PIX_FMT_RGBA64LE; source->width = 4; source->height = 3;
  g_assert_cmpint (av_frame_get_buffer (source, 32), >=, 0);
  for (gint y = 0; y < 3; y++)
    for (gint x = 0; x < 32; x++) source->data[0][y * source->linesize[0] + x] = y * 41 + x;
  GstGtkDoviMapper mapper = {0};
  GstVideoInfo variants[] = {
    layout (GST_VIDEO_FORMAT_RGBA64_LE, 32, 0, 96),
    layout (GST_VIDEO_FORMAT_RGBA64_LE, 40, 8, 120),
    layout (GST_VIDEO_FORMAT_RGBA64_LE, 36, 0, 108),
    layout (GST_VIDEO_FORMAT_RGBA64_LE, -32, 64, 96),
  };
  for (guint n = 0; n < G_N_ELEMENTS (variants); n++) {
    GstBuffer *buffer = acquire_output_buffer (&mapper, &variants[n]);
    g_assert_nonnull (buffer);
    gst_buffer_memset (buffer, 0, 0xcd, variants[n].size);
    GstVideoFrame frame = {0};
    g_assert_true (gst_video_frame_map (&frame, &variants[n], buffer, GST_MAP_WRITE));
    uint8_t *planes[4] = {GST_VIDEO_FRAME_PLANE_DATA (&frame, 0)};
    int strides[4] = {GST_VIDEO_FRAME_PLANE_STRIDE (&frame, 0)};
    av_image_copy (planes, strides, (const uint8_t **) source->data, source->linesize,
        AV_PIX_FMT_RGBA64LE, 4, 3);
    for (gint y = 0; y < 3; y++)
      g_assert_cmpmem (planes[0] + y * strides[0], 32,
          source->data[0] + y * source->linesize[0], 32);
    gst_video_frame_unmap (&frame); gst_buffer_unref (buffer);
  }
  clear_output_pool (&mapper); av_frame_free (&source);
}
static void destination_memory_flag (void)
{
  GstBuffer *source = gst_buffer_new (), *destination = gst_buffer_new ();
  GST_BUFFER_FLAG_SET (destination, GST_BUFFER_FLAG_TAG_MEMORY);
  g_assert_true (gst_buffer_copy_into (destination, source, GST_BUFFER_COPY_FLAGS, 0, -1));
  g_assert_true (GST_BUFFER_FLAG_IS_SET (destination, GST_BUFFER_FLAG_TAG_MEMORY));
  GST_BUFFER_FLAG_UNSET (destination, GST_BUFFER_FLAG_TAG_MEMORY);
  GST_BUFFER_FLAG_SET (source, GST_BUFFER_FLAG_TAG_MEMORY);
  g_assert_true (gst_buffer_copy_into (destination, source, GST_BUFFER_COPY_FLAGS, 0, -1));
  g_assert_false (GST_BUFFER_FLAG_IS_SET (destination, GST_BUFFER_FLAG_TAG_MEMORY));
  gst_buffer_unref (source); gst_buffer_unref (destination);
}
int main (int argc, char **argv)
{
  gst_init (&argc, &argv); g_test_init (&argc, &argv, NULL);
  g_test_add_func ("/output/checked-spans", checked_spans);
  g_test_add_func ("/output/gpu-pitch-selection", gpu_pitch_selection);
  g_test_add_func ("/output/fallback-pixels", fallback_pixels);
  g_test_add_func ("/output/destination-memory-flag", destination_memory_flag);
  return g_test_run ();
}
