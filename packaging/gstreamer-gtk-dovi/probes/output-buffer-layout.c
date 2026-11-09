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
static void single_row_stride (void)
{
  GstVideoInfo info = layout (GST_VIDEO_FORMAT_RGBA64_LE, 0, 0, 32);
  info.height = 1;
  g_assert_false (valid_output_span (&info));
  info.stride[0] = 16;
  g_assert_false (valid_output_span (&info));
  info.stride[0] = 32;
  g_assert_true (valid_output_span (&info));
  info.stride[0] = -32;
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
static void pool_destroyed (gpointer data, GObject *object)
{
  (void) object; *(gboolean *) data = TRUE;
}
static void assert_pattern (GstBuffer *buffer, guint8 value)
{
  GstMapInfo map;
  g_assert_true (gst_buffer_map (buffer, &map, GST_MAP_READ));
  for (gsize i = 0; i < map.size; i++) g_assert_cmpuint (map.data[i], ==, value);
  gst_buffer_unmap (buffer, &map);
}
static void held_buffers_and_layout_switch (void)
{
  GstGtkDoviMapper mapper = {0};
  GstVideoInfo info = layout (GST_VIDEO_FORMAT_RGBA64_LE, 32, 0, 96);
  GstBuffer *a = acquire_output_buffer (&mapper, &info);
  GstBuffer *b = acquire_output_buffer (&mapper, &info);
  GstBuffer *c = acquire_output_buffer (&mapper, &info);
  g_assert_nonnull (a); g_assert_nonnull (b); g_assert_nonnull (c);
  g_assert_true (a != b && a != c && b != c);
  gst_buffer_memset (a, 0, 0x11, info.size);
  gst_buffer_memset (b, 0, 0x22, info.size);
  gst_buffer_memset (c, 0, 0x33, info.size);
  GstBuffer *released = b;
  gst_buffer_add_video_crop_meta (b);
  gst_buffer_unref (b);
  b = acquire_output_buffer (&mapper, &info);
  g_assert_true (b == released);
  g_assert_null (gst_buffer_get_video_crop_meta (b));
  gst_buffer_memset (b, 0, 0x44, info.size);
  assert_pattern (a, 0x11); assert_pattern (c, 0x33);
  gboolean first_retired = FALSE, second_retired = FALSE, final_retired = FALSE;
  g_object_weak_ref (G_OBJECT (mapper.output_pool), pool_destroyed, &first_retired);
  info = layout (GST_VIDEO_FORMAT_RGBA64_LE, 40, 8, 120);
  GstBuffer *d = acquire_output_buffer (&mapper, &info);
  g_assert_nonnull (d); g_assert_false (first_retired);
  g_assert_cmpint (gst_buffer_get_video_meta (d)->stride[0], ==, 40);
  g_assert_cmpuint (gst_buffer_get_video_meta (d)->offset[0], ==, 8);
  gst_buffer_memset (d, 0, 0x55, info.size);
  g_object_weak_ref (G_OBJECT (mapper.output_pool), pool_destroyed, &second_retired);
  info = layout (GST_VIDEO_FORMAT_RGBA, 16, 0, 48);
  GstBuffer *e = acquire_output_buffer (&mapper, &info);
  g_assert_nonnull (e); g_assert_false (second_retired);
  gst_buffer_memset (e, 0, 0x66, info.size);
  g_object_weak_ref (G_OBJECT (mapper.output_pool), pool_destroyed, &final_retired);
  clear_output_pool (&mapper);
  g_assert_false (final_retired);
  assert_pattern (a, 0x11); assert_pattern (b, 0x44); assert_pattern (c, 0x33);
  assert_pattern (d, 0x55); assert_pattern (e, 0x66);
  gst_buffer_unref (a); gst_buffer_unref (b); gst_buffer_unref (c);
  g_assert_true (first_retired);
  gst_buffer_unref (d); g_assert_true (second_retired);
  gst_buffer_unref (e); g_assert_true (final_retired);
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
  g_test_add_func ("/output/single-row-stride", single_row_stride);
  g_test_add_func ("/output/gpu-pitch-selection", gpu_pitch_selection);
  g_test_add_func ("/output/fallback-pixels", fallback_pixels);
  g_test_add_func ("/output/held-buffers-and-layout-switch", held_buffers_and_layout_switch);
  g_test_add_func ("/output/destination-memory-flag", destination_memory_flag);
  return g_test_run ();
}
