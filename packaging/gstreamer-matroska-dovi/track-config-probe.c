/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <gst/gst.h>
#include <gstdovipicture.h>
#include <string.h>

typedef struct {
  gchar *name;
  guint8 bytes[24];
  gsize size;
  gboolean seen;
  guint buffers;
} Expected;
typedef struct {
  GstElement *pipeline;
  Expected *tracks;
  guint count;
  gint failed;
  guint decoded;
  guint resolved;
} Probe;

static gboolean
check_caps (Probe *p, Expected *track, const GstCaps *caps)
{
  const GstStructure *s = gst_caps_get_structure (caps, 0);
  const GValue *value = gst_structure_get_value (s, "dovi-configuration");
  guint8 bytes[24];
  GstBuffer *buffer;

  if (!track->size) {
    if (value)
      goto mismatch;
  } else {
    if (!value || !GST_VALUE_HOLDS_BUFFER (value))
      goto mismatch;
    buffer = gst_value_get_buffer (value);
    if (gst_buffer_get_size (buffer) != track->size ||
        gst_buffer_extract (buffer, 0, bytes, track->size) != track->size ||
        memcmp (bytes, track->bytes, track->size))
      goto mismatch;
  }
  track->seen = TRUE;
  g_print ("CAPS pad=%s media=%s bytes=%zu exact=yes\n", track->name,
      gst_structure_get_name (s), track->size);
  return TRUE;
mismatch:
  g_printerr ("configuration mismatch on %s\n", track->name);
  g_atomic_int_set (&p->failed, 1);
  return FALSE;
}

static GstPadProbeReturn
observe_caps (GstPad *pad, GstPadProbeInfo *info, gpointer data)
{
  Probe *p = data;
  guint i;
  GstEvent *event = GST_PAD_PROBE_INFO_EVENT (info);

  for (i = 0; i < p->count; i++) {
    if (strcmp (GST_PAD_NAME (pad), p->tracks[i].name))
      continue;
    if (GST_EVENT_TYPE (event) == GST_EVENT_CAPS) {
      GstCaps *caps;
      gst_event_parse_caps (event, &caps);
      check_caps (p, &p->tracks[i], caps);
    }
  }
  return GST_PAD_PROBE_OK;
}

static void
add_pad (GstElement *demux, GstPad *pad, gpointer data)
{
  Probe *p = data;
  GstElement *sink = gst_element_factory_make ("fakesink", NULL);
  GstPad *sinkpad;
  guint i;
  gboolean expected = FALSE;

  (void) demux;
  for (i = 0; i < p->count; i++)
    expected |= !strcmp (GST_PAD_NAME (pad), p->tracks[i].name);
  if (!expected)
    g_atomic_int_set (&p->failed, 1);
  g_object_set (sink, "sync", FALSE, "async", FALSE, NULL);
  gst_bin_add (GST_BIN (p->pipeline), sink);
  gst_element_sync_state_with_parent (sink);
  gst_pad_add_probe (pad, GST_PAD_PROBE_TYPE_EVENT_DOWNSTREAM, observe_caps, p,
      NULL);
  sinkpad = gst_element_get_static_pad (sink, "sink");
  if (gst_pad_link (pad, sinkpad) != GST_PAD_LINK_OK)
    g_atomic_int_set (&p->failed, 1);
  gst_object_unref (sinkpad);
}

static void
raw_frame (GstElement *sink, GstBuffer *buffer, GstPad *pad, gpointer data)
{
  Probe *p = data;
  GstDoviPictureMeta *meta = gst_buffer_get_dovi_picture_meta (buffer);
  const AVDOVIDecoderConfigurationRecord *config;

  (void) sink;
  (void) pad;
  p->decoded++;
  if (p->decoded == 1) {
    GstCaps *caps = gst_pad_get_current_caps (pad);
    if (!caps || !check_caps (p, &p->tracks[0], caps))
      g_atomic_int_set (&p->failed, 1);
    if (caps)
      gst_caps_unref (caps);
  }
  if (!meta)
    return;
  config = gst_dovi_picture_get_stream_config (meta->picture);
  if (!config || config->dv_profile != 5 || config->el_present_flag ||
      !config->bl_present_flag ||
      gst_dovi_picture_get_enhancement (meta->picture) !=
      GST_DOVI_ENHANCEMENT_NOT_REQUIRED ||
      !gst_dovi_picture_get_metadata (meta->picture) ||
      !gst_dovi_picture_get_rpu (meta->picture)) {
    g_atomic_int_set (&p->failed, 1);
    return;
  }
  p->resolved++;
}

static void
child_added (GstBin *root, GstBin *bin, GstElement *element, gpointer data)
{
  GstElementFactory *factory = gst_element_get_factory (element);
  const gchar *klass = factory ? gst_element_factory_get_metadata (factory,
      GST_ELEMENT_METADATA_KLASS) : NULL;

  (void) root;
  (void) bin;
  (void) data;
  if (klass && strstr (klass, "Decoder") && strstr (klass, "Video"))
    g_print ("DECODER factory=%s\n", GST_OBJECT_NAME (factory));
}

static gboolean
parse_expected (Expected *out, gchar *text)
{
  gchar **pair = g_strsplit (text, ":", 2);
  gboolean valid = pair[0] && pair[1];
  gsize i, n = valid ? strlen (pair[1]) : 0;

  if (valid && strcmp (pair[1], "-")) {
    valid = n >= 8 && n <= 48 && !(n % 2);
    for (i = 0; valid && i < n; i += 2) {
      gint a = g_ascii_xdigit_value (pair[1][i]);
      gint b = g_ascii_xdigit_value (pair[1][i + 1]);
      valid = a >= 0 && b >= 0;
      if (valid)
        out->bytes[i / 2] = (a << 4) | b;
    }
    out->size = n / 2;
  }
  out->name = g_strdup (pair[0]);
  g_strfreev (pair);
  return valid;
}

int
main (int argc, char **argv)
{
  Probe p = { 0 };
  GstElement *src, *demux, *sink;
  GstBus *bus;
  GstMessage *message;
  gboolean decode;
  guint i;
  gint result = 1;

  gst_init (&argc, &argv);
  decode = argc == 4 && !strcmp (argv[1], "--decode-p5");
  if ((!decode && argc < 3) || (decode && argc != 4))
    return 2;
  if (decode) {
    p.tracks = g_new0 (Expected, 1);
    if (!parse_expected (p.tracks, argv[3]))
      return 2;
    p.pipeline = gst_parse_launch ("filesrc name=src ! matroskademux ! "
        "h265parse ! decodebin ! fakesink name=out sync=false async=false "
        "signal-handoffs=true", NULL);
    g_signal_connect (p.pipeline, "deep-element-added", G_CALLBACK (child_added),
        NULL);
    sink = gst_bin_get_by_name (GST_BIN (p.pipeline), "out");
    g_signal_connect (sink, "handoff", G_CALLBACK (raw_frame), &p);
    gst_object_unref (sink);
  } else {
    p.count = argc - 2;
    p.tracks = g_new0 (Expected, p.count);
    for (i = 0; i < p.count; i++) {
      if (!parse_expected (&p.tracks[i], argv[i + 2]))
        return 2;
    }
    p.pipeline = gst_pipeline_new (NULL);
    src = gst_element_factory_make ("filesrc", "src");
    demux = gst_element_factory_make ("matroskademux", NULL);
    gst_bin_add_many (GST_BIN (p.pipeline), src, demux, NULL);
    if (!gst_element_link (src, demux))
      return 2;
    g_signal_connect (demux, "pad-added", G_CALLBACK (add_pad), &p);
  }
  src = gst_bin_get_by_name (GST_BIN (p.pipeline), "src");
  g_object_set (src, "location", decode ? argv[2] : argv[1], NULL);
  gst_object_unref (src);
  bus = gst_element_get_bus (p.pipeline);
  if (gst_element_set_state (p.pipeline, GST_STATE_PLAYING) ==
      GST_STATE_CHANGE_FAILURE)
    goto done;
  message = gst_bus_timed_pop_filtered (bus, 60 * GST_SECOND,
      GST_MESSAGE_EOS | GST_MESSAGE_ERROR);
  if (!message)
    goto done;
  if (GST_MESSAGE_TYPE (message) == GST_MESSAGE_ERROR) {
    GError *error;
    gchar *debug;
    gst_message_parse_error (message, &error, &debug);
    g_printerr ("ERROR %s (%s)\n", error->message, debug ? debug : "");
    g_clear_error (&error);
    g_free (debug);
  } else {
    result = g_atomic_int_get (&p.failed) ? 1 : 0;
    for (i = 0; i < p.count; i++)
      if (!p.tracks[i].seen)
        result = 1;
    if (decode && (!p.decoded || p.resolved != p.decoded))
      result = 1;
  }
  gst_message_unref (message);
done:
  gst_element_set_state (p.pipeline, GST_STATE_NULL);
  g_print ("RESULT exit=%d decoded=%u resolved=%u\n", result, p.decoded,
      p.resolved);
  gst_object_unref (bus);
  gst_object_unref (p.pipeline);
  for (i = 0; i < p.count; i++)
    g_free (p.tracks[i].name);
  if (decode && p.tracks)
    g_free (p.tracks[0].name);
  g_free (p.tracks);
  return result;
}
