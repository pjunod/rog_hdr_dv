/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Count NVDEC output pictures of a Profile 7 FEL file that carry a matched enhancement frame.
 * usage: fel-nvdec-pairing-probe FILE [SEEK_SECONDS] — plays FILE (optionally after a flushing seek) to EOS. */
#include <gst/gst.h>
#include <gst/app/gstappsink.h>
#include <gstdovipicture.h>
#include <stdlib.h>
static guint total, paired;
static GstFlowReturn sample (GstAppSink *sink, gpointer data) {
  GstSample *s = gst_app_sink_pull_sample (sink); GstBuffer *b = gst_sample_get_buffer (s);
  GstDoviPictureMeta *m = gst_buffer_get_dovi_picture_meta (b);
  gboolean ok = m && gst_dovi_picture_meta_get_fel (m);
  total++; if (ok) paired++; else g_print ("unpaired pts=%" GST_TIME_FORMAT "\n", GST_TIME_ARGS (GST_BUFFER_PTS (b)));
  gst_sample_unref (s); return GST_FLOW_OK;
}
int main (int argc, char **argv) {
  gst_init (&argc, &argv);
  gchar *d = g_strdup_printf ("filesrc location=\"%s\" ! qtdemux ! h265parse ! nvh265dec ! appsink name=out sync=false emit-signals=true", argv[1]);
  GstElement *p = gst_parse_launch (d, NULL); GstElement *out = gst_bin_get_by_name (GST_BIN (p), "out");
  g_signal_connect (out, "new-sample", G_CALLBACK (sample), NULL);
  gst_element_set_state (p, GST_STATE_PAUSED); gst_element_get_state (p, NULL, NULL, GST_CLOCK_TIME_NONE);
  if (argc > 2) { total = paired = 0; gst_element_seek_simple (p, GST_FORMAT_TIME, GST_SEEK_FLAG_FLUSH | GST_SEEK_FLAG_ACCURATE, (gint64) (atof (argv[2]) * GST_SECOND)); gst_element_get_state (p, NULL, NULL, GST_CLOCK_TIME_NONE); }
  gst_element_set_state (p, GST_STATE_PLAYING);
  GstMessage *msg = gst_bus_timed_pop_filtered (gst_element_get_bus (p), 60 * GST_SECOND, GST_MESSAGE_EOS | GST_MESSAGE_ERROR);
  g_print ("%s total=%u paired=%u\n", msg && GST_MESSAGE_TYPE (msg) == GST_MESSAGE_EOS ? "eos" : "error/timeout", total, paired);
  gst_element_set_state (p, GST_STATE_NULL); return total && total == paired ? 0 : 1;
}
