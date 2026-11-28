/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Extraction acceptance: decode picture N with GStreamer, map it through
 * whichever libgstgtkdovicore.so.0 the loader resolves (the installed one, or
 * a staged build through LD_LIBRARY_PATH) for DISPLAY_PQ at an explicit
 * physical target or for the SDR destination, and write the output rows
 * (RGBA64LE or RGBA) to a new file.
 * usage: mapper-dump FILE N pq|sdr PEAK MIN REF OUT
 * MAPPER_DUMP_DECODER overrides the decoder chain (default avdec_h265).
 * MAPPER_DUMP_CYCLES=n first creates, uses and frees n-1 other mappers, as a
 * process that plays several videos in turn does. */
#include <gst/gst.h>
#include <gst/app/gstappsink.h>
#include <gst/video/video.h>
#include "mapper.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main (int argc, char **argv)
{
  if (argc != 8) { fprintf (stderr, "usage: mapper-dump FILE N pq|sdr PEAK MIN REF OUT\n"); return 2; }
  gst_init (NULL, NULL);
  gboolean sdr = !strcmp (argv[3], "sdr");
  const char *decoder = g_getenv ("MAPPER_DUMP_DECODER") ? g_getenv ("MAPPER_DUMP_DECODER") : "avdec_h265";
  gchar *desc = g_strdup_printf ("filesrc location=\"%s\" ! qtdemux ! h265parse ! %s ! "
      "appsink name=sink sync=false max-buffers=4", argv[1], decoder);
  GError *err = NULL;
  GstElement *pipe = gst_parse_launch (desc, &err);
  g_free (desc);
  if (!pipe) { fprintf (stderr, "%s\n", err->message); return 3; }
  GstElement *sink = gst_bin_get_by_name (GST_BIN (pipe), "sink");
  gst_element_set_state (pipe, GST_STATE_PLAYING);
  int want = atoi (argv[2]);
  GstSample *sample = NULL;
  for (int n = 0; n <= want; n++) {
    if (sample) gst_sample_unref (sample);
    sample = gst_app_sink_pull_sample (GST_APP_SINK (sink));
    if (!sample) { fprintf (stderr, "no picture %d\n", n); return 4; }
  }
  GstVideoInfo info, out_info;
  gst_video_info_from_caps (&info, gst_sample_get_caps (sample));
  gst_video_info_set_format (&out_info, sdr ? GST_VIDEO_FORMAT_RGBA : GST_VIDEO_FORMAT_RGBA64_LE,
      info.width, info.height);
  if (sdr)
    out_info.colorimetry = (GstVideoColorimetry) {GST_VIDEO_COLOR_RANGE_0_255,
        GST_VIDEO_COLOR_MATRIX_RGB, GST_VIDEO_TRANSFER_SRGB, GST_VIDEO_COLOR_PRIMARIES_BT709};
  /* BT.2020 D65 stand-in primaries, as in the project's earlier receipts. */
  GstGtkDoviTarget t = {.generation = 1,
    .primaries = {0.708, 0.292, 0.170, 0.797, 0.131, 0.046, 0.3127, 0.3290},
    .max_nits = atof (argv[4]), .min_nits = atof (argv[5]), .reference_nits = atof (argv[6]),
    .encoding_reference_nits = 203, .encoding_max_nits = 10000,
    .valid = TRUE, .composed = TRUE, .render_ready = TRUE};
  int cycles = g_getenv ("MAPPER_DUMP_CYCLES") ? atoi (g_getenv ("MAPPER_DUMP_CYCLES")) : 1;
  for (int c = 1; c < cycles; c++) {
    GstGtkDoviMapper *earlier = gst_gtk_dovi_mapper_new ();
    GstBuffer *discard = NULL;
    gst_gtk_dovi_mapper_render_destination (earlier, gst_sample_get_buffer (sample), &info,
        sdr ? GST_GTK_DOVI_DESTINATION_STANDARD_SDR_SRGB : GST_GTK_DOVI_DESTINATION_DISPLAY_PQ,
        &t, &discard, &out_info, NULL);
    gst_clear_buffer (&discard);
    gst_gtk_dovi_mapper_free (earlier);
  }
  GstGtkDoviMapper *m = gst_gtk_dovi_mapper_new ();
  GstBuffer *out = NULL;
  int r = gst_gtk_dovi_mapper_render_destination (m, gst_sample_get_buffer (sample), &info,
      sdr ? GST_GTK_DOVI_DESTINATION_STANDARD_SDR_SRGB : GST_GTK_DOVI_DESTINATION_DISPLAY_PQ,
      &t, &out, &out_info, &err);
  fprintf (stderr, "input %s %dx%d, render %d%s%s\n", gst_video_format_to_string (GST_VIDEO_INFO_FORMAT (&info)),
      info.width, info.height, r, err ? ": " : "", err ? err->message : "");
  if (r < 1 || !out) return 5;
  GstVideoFrame f;
  if (!gst_video_frame_map (&f, &out_info, out, GST_MAP_READ)) return 6;
  FILE *o = fopen (argv[7], "wbx");
  if (!o) return 7;
  guint pixel = sdr ? 4 : 8;
  for (int y = 0; y < out_info.height; y++)
    fwrite ((guint8 *) GST_VIDEO_FRAME_PLANE_DATA (&f, 0) + (gsize) y * GST_VIDEO_FRAME_PLANE_STRIDE (&f, 0),
        pixel, out_info.width, o);
  fclose (o);
  gst_video_frame_unmap (&f);
  gst_buffer_unref (out);
  gst_gtk_dovi_mapper_free (m);
  gst_sample_unref (sample);
  gst_element_set_state (pipe, GST_STATE_NULL);
  gst_object_unref (sink);
  gst_object_unref (pipe);
  printf ("{\"width\": %d, \"height\": %d, \"result\": %d}\n", out_info.width, out_info.height, r);
  return 0;
}
