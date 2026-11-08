/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <gst/base/gstbasetransform.h>
#include <gst/app/gstappsrc.h>
#include <gst/video/video.h>
#include <string.h>

static guint checks;
static guint failures;

static void
require (gboolean success, const gchar *name)
{
  checks++;
  if (!success) {
    failures++;
    g_printerr ("FAIL %s\n", name);
  }
}

static GstCaps *
caps_for (const gchar *format, const gchar *memory, gboolean marked)
{
  GstCaps *caps = gst_caps_new_simple ("video/x-raw", "format", G_TYPE_STRING,
      format, "width", G_TYPE_INT, 16, "height", G_TYPE_INT, 16,
      "framerate", GST_TYPE_FRACTION, 24, 1, NULL);
  if (memory)
    gst_caps_set_features (caps, 0, !strcmp (memory, "ANY") ?
        gst_caps_features_new_any () : gst_caps_features_new (memory, NULL));
  if (marked) {
    /* Public synthetic complete v1.0 P5/level3 BL+RPU/noEL record. */
    const guint8 record[24] = {1, 0, 10, 29, 0};
    GstBuffer *buffer = gst_buffer_new_memdup (record, sizeof (record));
    gst_caps_set_simple (caps, "dovi-configuration", GST_TYPE_BUFFER, buffer,
        NULL);
    gst_buffer_unref (buffer);
  }
  return caps;
}

static void
pipeline_control (const gchar *format, const gchar *memory, gboolean marked)
{
  GstElement *pipeline = gst_pipeline_new (NULL);
  GstElement *src = gst_element_factory_make ("appsrc", NULL);
  GstElement *map = gst_element_factory_make ("gtkdovimap", NULL);
  GstElement *sink = gst_element_factory_make ("fakesink", NULL);
  GstCaps *caps = caps_for (format, memory, marked);
  GstBus *bus;
  GstMessage *message;
  GstBuffer *buffer = gst_buffer_new_allocate (NULL, 768, NULL);
  GstMapInfo bytes;

  g_object_set (src, "caps", caps, "format", GST_FORMAT_TIME, NULL);
  g_object_set (sink, "sync", FALSE, "async", FALSE, NULL);
  gst_caps_unref (caps);
  gst_bin_add_many (GST_BIN (pipeline), src, map, sink, NULL);
  if (!gst_element_link_many (src, map, sink, NULL)) {
    require (marked, "unsupported marked caps rejected at link negotiation");
    gst_buffer_unref (buffer);
    gst_object_unref (pipeline);
    return;
  }
  require (TRUE, "control links");
  bus = gst_element_get_bus (pipeline);
  require (gst_element_set_state (pipeline, GST_STATE_PLAYING) !=
      GST_STATE_CHANGE_FAILURE, "control starts");
  if (gst_buffer_map (buffer, &bytes, GST_MAP_WRITE)) {
    memset (bytes.data, 0x51, bytes.size);
    gst_buffer_unmap (buffer, &bytes);
  }
  GST_BUFFER_PTS (buffer) = 0;
  GST_BUFFER_DURATION (buffer) = GST_SECOND / 24;
  gst_app_src_push_buffer (GST_APP_SRC (src), buffer);
  gst_app_src_end_of_stream (GST_APP_SRC (src));
  message = gst_bus_timed_pop_filtered (bus, 10 * GST_SECOND,
      GST_MESSAGE_EOS | GST_MESSAGE_ERROR);
  require (message != NULL, "control completes within ten seconds");
  if (message) {
    if (marked) {
      gboolean negotiation_error = FALSE;
      if (GST_MESSAGE_TYPE (message) == GST_MESSAGE_ERROR) {
        GError *error;
        gchar *debug;
        gst_message_parse_error (message, &error, &debug);
        negotiation_error = (debug && strstr (debug, "not-negotiated")) ||
            strstr (error->message, "not-negotiated");
        g_print ("REJECT format=%s memory=%s reason=%s\n", format,
            memory ? memory : "SystemMemory", error->message);
        g_clear_error (&error);
        g_free (debug);
      }
      require (negotiation_error, "unsupported marked input fails negotiation");
    } else {
      require (GST_MESSAGE_TYPE (message) == GST_MESSAGE_EOS,
          "unmarked unsupported import remains ordinary passthrough");
    }
    gst_message_unref (message);
  }
  gst_element_set_state (pipeline, GST_STATE_NULL);
  gst_object_unref (bus);
  gst_object_unref (pipeline);
}

int
main (int argc, char **argv)
{
  GstElement *element;
  GstBaseTransform *base;
  GstBaseTransformClass *klass;
  GstCaps *nv12, *p010, *nv21, *dma, *any_memory, *output, *reverse, *result;
  GstElementFactory *factory;
  GstPlugin *plugin;

  gst_init (&argc, &argv);
  if (argc != 2)
    return 2;
  element = gst_element_factory_make ("gtkdovimap", NULL);
  if (!element)
    return 2;
  factory = gst_element_get_factory (element);
  plugin = gst_plugin_feature_get_plugin (GST_PLUGIN_FEATURE (factory));
  require (plugin && !g_strcmp0 (gst_plugin_get_filename (plugin), argv[1]),
      "exact requested plugin is loaded");
  if (plugin)
    gst_object_unref (plugin);
  base = GST_BASE_TRANSFORM (element);
  klass = GST_BASE_TRANSFORM_GET_CLASS (base);
  nv12 = caps_for ("NV12", NULL, TRUE);
  p010 = caps_for ("P010_10LE", NULL, TRUE);
  nv21 = caps_for ("NV21", NULL, TRUE);
  dma = caps_for ("NV12", "memory:DMABuf", TRUE);
  any_memory = caps_for ("NV12", "ANY", TRUE);
  output = klass->transform_caps (base, GST_PAD_SINK, nv12, NULL);
  require (!gst_caps_is_empty (output) && gst_caps_is_fixed (output),
      "marked NV12 has a fixed graded output");
  require (klass->set_caps (base, nv12, output), "marked NV12 accepted");
  require (klass->set_caps (base, p010, output), "marked P010 accepted");
  require (!klass->set_caps (base, nv21, output), "marked NV21 rejected at set_caps");
  require (!klass->set_caps (base, dma, output), "marked DMABuf rejected at set_caps");
  require (!klass->set_caps (base, any_memory, output), "marked unknown memory rejected at set_caps");
  result = klass->transform_caps (base, GST_PAD_SINK, nv21, NULL);
  require (gst_caps_is_empty (result), "marked NV21 forward query is empty");
  gst_caps_unref (result);
  result = klass->transform_caps (base, GST_PAD_SINK, dma, NULL);
  require (gst_caps_is_empty (result), "marked DMABuf forward query is empty");
  gst_caps_unref (result);
  reverse = klass->transform_caps (base, GST_PAD_SRC, output, NULL);
  require (gst_caps_can_intersect (reverse, nv12), "reverse includes NV12");
  require (gst_caps_can_intersect (reverse, p010), "reverse includes P010");
  require (!gst_caps_can_intersect (reverse, nv21), "reverse excludes NV21");
  require (!gst_caps_can_intersect (reverse, dma), "reverse excludes DMABuf");
  for (guint i = 0; i < gst_caps_get_size (reverse); i++)
    require (gst_caps_features_is_equal (gst_caps_get_features (reverse, i),
            GST_CAPS_FEATURES_MEMORY_SYSTEM_MEMORY), "reverse memory is explicit system memory");
  GstCaps *bad_output = gst_caps_copy (output);
  gst_caps_set_simple (bad_output, "format", G_TYPE_STRING, "RGBA", NULL);
  require (!klass->set_caps (base, nv12, bad_output), "graded eight-bit output rejected");
  result = klass->transform_caps (base, GST_PAD_SRC, bad_output, NULL);
  require (gst_caps_is_empty (result), "reverse rejects impossible graded output");
  gst_caps_unref (result);
  gst_caps_unref (bad_output);
  bad_output = gst_caps_copy (output);
  gst_caps_set_simple (bad_output, "colorimetry", G_TYPE_STRING, "sRGB", NULL);
  require (!klass->set_caps (base, nv12, bad_output), "graded wrong transfer rejected");
  gst_caps_unref (bad_output);
  const GstPadDirection directions[] = {GST_PAD_SINK, GST_PAD_SRC};
  for (guint i = 0; i < G_N_ELEMENTS (directions); i++) {
    GstCaps *plain = caps_for ("NV21", "memory:DMABuf", FALSE);
    result = klass->transform_caps (base, directions[i], plain, NULL);
    require (gst_caps_is_equal (plain, result), "unmarked caps unchanged");
    require (klass->set_caps (base, plain, result), "unmarked caps remain passthrough");
    gst_caps_unref (plain);
    gst_caps_unref (result);
    plain = gst_caps_new_any ();
    result = klass->transform_caps (base, directions[i], plain, NULL);
    require (gst_caps_is_any (result), "unmarked ANY unchanged");
    require (klass->set_caps (base, plain, result), "unmarked ANY safely handled");
    gst_caps_unref (plain);
    gst_caps_unref (result);
  }
  gst_caps_unref (reverse);
  gst_caps_unref (output);
  gst_caps_unref (nv12);
  gst_caps_unref (p010);
  gst_caps_unref (nv21);
  gst_caps_unref (dma);
  gst_caps_unref (any_memory);
  gst_object_unref (element);
  pipeline_control ("NV21", NULL, TRUE);
  pipeline_control ("NV12", "memory:DMABuf", TRUE);
  pipeline_control ("NV21", NULL, FALSE);
  pipeline_control ("NV12", "memory:DMABuf", FALSE);
  g_print ("RESULT checks=%u failures=%u\n", checks, failures);
  return failures ? 1 : 0;
}
