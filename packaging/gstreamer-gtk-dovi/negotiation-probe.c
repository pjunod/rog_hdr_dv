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

typedef struct {
  GstCaps *offered;
  gboolean normalize_stream_fields;
} QueryPeer;

static GstCaps *
peer_caps_copy (GstCaps *caps, gboolean normalize)
{
  GstCaps *copy = gst_caps_copy (caps);
  if (normalize) {
    for (guint i = 0; i < gst_caps_get_size (copy); i++)
      gst_structure_remove_fields (gst_caps_get_structure (copy, i),
          "dovi-configuration", "dovi-fel-decoder", NULL);
  }
  return copy;
}

static gboolean
query_peer (GstPad *pad, GstObject *parent, GstQuery *query)
{
  QueryPeer *peer = gst_pad_get_element_private (pad);
  if (GST_QUERY_TYPE (query) == GST_QUERY_CAPS) {
    GstCaps *filter, *offered, *answer;
    gst_query_parse_caps (query, &filter);
    offered = peer_caps_copy (peer->offered, peer->normalize_stream_fields);
    if (filter) {
      GstCaps *plain_filter = peer_caps_copy (filter,
          peer->normalize_stream_fields);
      answer = gst_caps_intersect_full (plain_filter, offered,
          GST_CAPS_INTERSECT_FIRST);
      gst_caps_unref (plain_filter);
    } else {
      answer = gst_caps_ref (offered);
    }
    gst_query_set_caps_result (query, answer);
    gst_caps_unref (answer);
    gst_caps_unref (offered);
    return TRUE;
  }
  if (GST_QUERY_TYPE (query) == GST_QUERY_ACCEPT_CAPS) {
    GstCaps *caps, *offered, *plain;
    gst_query_parse_accept_caps (query, &caps);
    plain = peer_caps_copy (caps, peer->normalize_stream_fields);
    offered = peer_caps_copy (peer->offered, peer->normalize_stream_fields);
    gst_query_set_accept_caps_result (query,
        gst_caps_is_subset (plain, offered));
    gst_caps_unref (offered);
    gst_caps_unref (plain);
    return TRUE;
  }
  return gst_pad_query_default (pad, parent, query);
}

static void
linked_query_controls (GstElement *element, GstBaseTransformClass *klass,
    GstCaps *output)
{
  GstBaseTransform *base = GST_BASE_TRANSFORM (element);
  GstPad *src = gst_element_get_static_pad (element, "src");
  GstPad *sink = gst_element_get_static_pad (element, "sink");
  GstPad *peer_pad = gst_pad_new ("cpu-query-peer", GST_PAD_SINK);
  QueryPeer peer = {gst_caps_copy (output), TRUE};
  gst_pad_set_element_private (peer_pad, &peer);
  gst_pad_set_query_function (peer_pad, query_peer);
  require (gst_pad_link (src, peer_pad) == GST_PAD_LINK_OK,
      "real downstream peer links for filtered query controls");

  GstCaps *input = caps_for ("P010_10LE", "memory:VAMemory", TRUE);
  GstCaps *result = gst_pad_query_caps (sink, input);
  require (gst_caps_is_equal (result, input),
      "filtered sink query preserves VA preimage when peer drops stream fields");
  gst_caps_unref (result);

  GstCaps *dma = caps_for ("DMA_DRM", "memory:DMABuf", TRUE);
  gst_caps_set_simple (dma, "drm-format", G_TYPE_STRING,
      "P010:0x0100000000000009", NULL);
  result = gst_pad_query_caps (sink, dma);
  require (gst_caps_is_empty (result),
      "marked tiled DMA_DRM cannot acquire support through unmarked identity");
  require (!gst_pad_query_accept_caps (sink, dma),
      "actual marked tiled DMA_DRM ACCEPT_CAPS is false");
  gst_caps_unref (result);

  GstCaps *unmarked_output = peer_caps_copy (output, TRUE);
  result = klass->transform_caps (base, GST_PAD_SRC, unmarked_output, dma);
  require (gst_caps_is_empty (result),
      "normalized output plus marked DMA filter has no false identity preimage");
  gst_caps_unref (result);

  GstCaps *wrong = gst_caps_copy (unmarked_output);
  gst_caps_set_simple (wrong, "width", G_TYPE_INT, 32, NULL);
  gst_caps_unref (peer.offered); peer.offered = wrong;
  result = gst_pad_query_caps (sink, input);
  require (gst_caps_is_empty (result), "actual peer width restriction retained");
  gst_caps_unref (result);

  wrong = gst_caps_copy (unmarked_output);
  gst_caps_set_simple (wrong, "format", G_TYPE_STRING, "RGB", NULL);
  gst_caps_unref (peer.offered); peer.offered = wrong;
  result = gst_pad_query_caps (sink, input);
  require (gst_caps_is_empty (result), "actual peer wrong output format rejected");
  gst_caps_unref (result);

  wrong = gst_caps_copy (unmarked_output);
  gst_caps_set_features_simple (wrong,
      gst_caps_features_new ("memory:GLMemory", NULL));
  gst_caps_unref (peer.offered); peer.offered = wrong;
  result = gst_pad_query_caps (sink, input);
  require (gst_caps_is_empty (result), "actual peer wrong output memory rejected");
  gst_caps_unref (result);

  GstCaps *plain = caps_for ("NV21", "memory:DMABuf", FALSE);
  gst_caps_unref (peer.offered); peer.offered = gst_caps_copy (plain);
  result = gst_pad_query_caps (sink, plain);
  require (gst_caps_is_equal (result, plain),
      "real unmarked DMA passthrough query remains byte-for-byte unchanged");
  gst_caps_unref (result);

  GstCaps *other = gst_caps_copy (input);
  GstBuffer *other_config = gst_buffer_new_allocate (NULL, 24, NULL);
  const guint8 record[24] = {1, 0, 10, 37, 0};
  gst_buffer_fill (other_config, 0, record, sizeof (record));
  gst_caps_set_simple (other, "dovi-configuration", GST_TYPE_BUFFER,
      other_config, NULL);
  gst_buffer_unref (other_config);
  GstCaps *other_output = klass->transform_caps (base, GST_PAD_SINK,
      other, NULL);
  GstCaps *mixed = gst_caps_copy (input);
  gst_caps_append (mixed, gst_caps_copy (other));
  gst_caps_append (mixed, gst_caps_copy (plain));
  GstCaps *offer = gst_caps_copy (other_output);
  gst_caps_append (offer, gst_caps_copy (plain));
  peer.normalize_stream_fields = FALSE;
  gst_caps_unref (peer.offered); peer.offered = offer;
  result = gst_pad_query_caps (sink, mixed);
  require (gst_caps_can_intersect (result, other),
      "mixed query retains the matching marked config");
  require (!gst_caps_can_intersect (result, input),
      "mixed query never crosses marked configuration identity");
  require (gst_caps_can_intersect (result, plain),
      "mixed marked and unmarked query preserves plain alternative");
  gst_caps_unref (result);

  gst_caps_unref (other_output);
  gst_caps_unref (mixed);
  gst_caps_unref (other);
  gst_caps_unref (plain);
  gst_caps_unref (unmarked_output);
  gst_caps_unref (dma);
  gst_caps_unref (input);
  gst_pad_unlink (src, peer_pad);
  gst_caps_unref (peer.offered);
  gst_object_unref (peer_pad);
  gst_object_unref (sink);
  gst_object_unref (src);
}

static void
profile5_missing_picture_controls (void)
{
  for (guint kind = 0; kind < 2; kind++) {
    GstElement *map = gst_element_factory_make ("gtkdovimap", NULL);
    g_object_set (map, "destination-kind", kind, NULL);
    GstBus *bus = gst_bus_new (); gst_element_set_bus (map, bus);
    GstBaseTransform *base = GST_BASE_TRANSFORM (map);
    GstBaseTransformClass *klass = GST_BASE_TRANSFORM_GET_CLASS (base);
    GstCaps *input = caps_for ("P010_10LE", NULL, TRUE);
    GstCaps *graded = klass->transform_caps (base, GST_PAD_SINK, input, NULL);
    require (klass->set_caps (base, input, graded), "complete marked P5 has an explicit destination contract");
    GstBuffer *pixels = gst_buffer_new_allocate (NULL, 768, NULL), *output = NULL;
    require (klass->prepare_output_buffer (base, pixels, &output) == GST_FLOW_ERROR && !output,
        "known P5 pixels without immutable picture proof cannot become graded or retained output");
    GstMessage *message = gst_bus_pop_filtered (bus, GST_MESSAGE_ERROR);
    GError *error = NULL;
    if (message) gst_message_parse_error (message, &error, NULL);
    require (error && error->domain == GST_STREAM_ERROR && error->code == GST_STREAM_ERROR_FORMAT,
        "known P5 missing-proof refusal keeps typed FORMAT on the real element bus");
    g_clear_error (&error); if (message) gst_message_unref (message);
    GstCaps *plain = caps_for ("P010_10LE", NULL, FALSE);
    require (klass->set_caps (base, plain, plain), "unmarked stream returns to its original identity contract");
    require (klass->prepare_output_buffer (base, pixels, &output) == GST_FLOW_OK && output == pixels,
        "unmarked control preserves the exact original GstBuffer");
    gst_clear_buffer (&output); gst_buffer_unref (pixels);
    gst_caps_unref (plain); gst_caps_unref (graded); gst_caps_unref (input);
    gst_element_set_bus (map, NULL); gst_object_unref (bus); gst_object_unref (map);
  }
}

static void
source_context (GstElement *map, guint64 revision, gboolean blocked,
    const gchar *stream_id, GstCaps *coded)
{
  GstContext *context = gst_context_new ("gst.webkit.dovi.source.v1", FALSE);
  GstStructure *st = gst_context_writable_structure (context);
  gst_structure_set (st, "source-revision", G_TYPE_UINT64, revision,
      "blocked", G_TYPE_BOOLEAN, blocked, NULL);
  if (stream_id) gst_structure_set (st, "stream-id", G_TYPE_STRING, stream_id, NULL);
  if (coded) gst_structure_set (st, "clear-coded-caps", GST_TYPE_CAPS, coded, NULL);
  gst_element_set_context (map, context); gst_context_unref (context);
}
static void
source_gate_check (GstElement *map, GstCaps *input, gboolean graded, const gchar *name)
{
  GstBaseTransform *base = GST_BASE_TRANSFORM (map);
  GstCaps *out = GST_BASE_TRANSFORM_GET_CLASS (base)->transform_caps (base,
      GST_PAD_SINK, input, NULL);
  gboolean mapped = !gst_caps_is_empty (out) && !gst_caps_is_equal (input, out) &&
      !g_strcmp0 (gst_structure_get_string (gst_caps_get_structure (out, 0), "format"), "RGBA");
  require (graded ? mapped : gst_caps_is_equal (input, out), name);
  gst_caps_unref (out);
}
typedef struct { guint64 revoked_revision, revoked_selection; guint revokes; } SelectionEvents;
static void source_selection_revoked (GstElement *map, guint64 revision,
    guint64 selection, gpointer data)
{
  (void) map;
  SelectionEvents *events = data;
  events->revoked_revision = revision; events->revoked_selection = selection;
  events->revokes++;
}
static void
pre_start_query_controls (void)
{
  GstElement *map = gst_element_factory_make ("gtkdovimap", NULL);
  g_object_set (map, "destination-kind", 1u, "require-clear-source", TRUE, NULL);
  GstPad *sink = gst_element_get_static_pad (map, "sink");
  GstPad *src = gst_element_get_static_pad (map, "src");
  gst_pad_set_active (sink, TRUE); gst_pad_set_active (src, TRUE);
  GstCaps *input = caps_for ("P010_10LE", NULL, TRUE);
  GstCaps *coded = gst_caps_copy (input);
  gst_structure_set_name (gst_caps_get_structure (coded, 0), "video/x-h265");
  source_gate_check (map, input, FALSE, "pre-start query without a clear proof keeps identity caps");
  source_context (map, 1, FALSE, "clear/video0", coded);
  source_gate_check (map, input, TRUE,
      "pre-start query is qualified by an identical clear proof of the current revision");
  GstBaseTransform *base = GST_BASE_TRANSFORM (map);
  GstCaps *downstream = gst_caps_from_string ("video/x-raw, format=(string)RGBA; "
      "video/x-raw(memory:DMABuf), format=(string)DMA_DRM");
  GstCaps *offered = GST_BASE_TRANSFORM_GET_CLASS (base)->transform_caps (base,
      GST_PAD_SRC, downstream, NULL);
  GstCaps *va = caps_for ("P010_10LE", "memory:VAMemory", TRUE);
  require (gst_caps_can_intersect (offered, va),
      "unfiltered reverse query offers the marked importable domain of a clear proof");
  gst_caps_unref (va); gst_caps_unref (offered); gst_caps_unref (downstream);
  GstCaps *wrong = gst_caps_copy (input);
  guint8 record[24] = {1, 0, 16, 29, 16};
  GstBuffer *config = gst_buffer_new_memdup (record, sizeof (record));
  gst_caps_set_simple (wrong, "dovi-configuration", GST_TYPE_BUFFER, config, NULL);
  gst_buffer_unref (config);
  source_gate_check (map, wrong, FALSE, "pre-start query cannot borrow a different configuration");
  gst_pad_send_event (sink, gst_event_new_stream_start ("other/video0"));
  source_gate_check (map, input, FALSE, "a started stream needs its own exact lease");
  source_context (map, 2, FALSE, "clear/video0", coded);
  source_gate_check (map, input, FALSE, "after a stream started, a new revision needs its own start");
  source_context (map, 3, TRUE, NULL, NULL);
  gst_caps_unref (wrong); gst_caps_unref (coded); gst_caps_unref (input);
  gst_pad_set_active (sink, FALSE); gst_pad_set_active (src, FALSE);
  gst_object_unref (sink); gst_object_unref (src); gst_object_unref (map);
}
static void
source_lifecycle_controls (void)
{
  GstElement *map = gst_element_factory_make ("gtkdovimap", NULL);
  g_object_set (map, "destination-kind", 1u, "require-clear-source", TRUE, NULL);
  SelectionEvents selections = {0};
  g_signal_connect (map, "source-selection-revoked", G_CALLBACK (source_selection_revoked), &selections);
  GstPad *sink = gst_element_get_static_pad (map, "sink");
  GstPad *src = gst_element_get_static_pad (map, "src");
  gst_pad_set_active (sink, TRUE); gst_pad_set_active (src, TRUE);
  GstCaps *input = caps_for ("P010_10LE", NULL, TRUE);
  GstCaps *coded = gst_caps_copy (input);
  gst_structure_set_name (gst_caps_get_structure (coded, 0), "video/x-h265");
  source_gate_check (map, input, FALSE, "browser unknown source uses exact identity caps");
  gst_pad_send_event (sink, gst_event_new_stream_start ("other/video0"));
  gst_pad_send_event (sink, gst_event_new_caps (input));
  GstBaseTransform *base = GST_BASE_TRANSFORM (map);
  GstBaseTransformClass *klass = GST_BASE_TRANSFORM_GET_CLASS (base);
  require (klass->set_caps (base, input, input), "unknown source establishes original identity contract");
  GstBuffer *pending = gst_buffer_new_allocate (NULL, 768, NULL), *prepared = NULL;
  require (klass->prepare_output_buffer (base, pending, &prepared) == GST_FLOW_OK && prepared == pending,
      "unknown source preserves the exact original buffer");
  gst_clear_buffer (&prepared);

  source_context (map, 1, FALSE, "clear/video0", coded);
  source_gate_check (map, input, FALSE, "coded proof alone cannot authorize a prior or unknown raw stream");
  gst_pad_send_event (sink, gst_event_new_stream_start ("other/video0"));
  source_gate_check (map, input, FALSE, "another stream cannot borrow a clear configuration");
  gst_pad_send_event (sink, gst_event_new_stream_start ("clear/video0"));
  source_gate_check (map, input, TRUE, "matching raw stream and original coded proof enable grade");
  require (klass->prepare_output_buffer (base, pending, &prepared) == GST_BASE_TRANSFORM_FLOW_DROPPED && !prepared,
      "positive STREAM_START lease drops old marked identity buffers pending graded renegotiation");
  GstCaps *fresh = klass->transform_caps (base, GST_PAD_SINK, input, NULL);
  require (klass->set_caps (base, input, fresh), "fresh graded caps resume the matched lease contract");
  gst_caps_unref (fresh); gst_buffer_unref (pending);

  guint64 revision_a = 0, selection_a = 0, revision_b = 0, selection_b = 0;
  g_object_get (map, "active-source-revision", &revision_a,
      "active-source-selection", &selection_a, NULL);
  source_context (map, 1, FALSE, "clear/video1", coded);
  gst_pad_send_event (sink, gst_event_new_stream_start ("clear/video1"));
  g_object_get (map, "active-source-revision", &revision_b,
      "active-source-selection", &selection_b, NULL);
  require (revision_a == 1 && revision_b == revision_a && selection_a && selection_b > selection_a,
      "downstream-only STREAM_START rotates the selected lease within the same origin");
  require (selections.revokes && selections.revoked_revision == revision_a && selections.revoked_selection == selection_a,
      "held A export receives exact selected-lease revocation before B");
  gst_pad_send_event (sink, gst_event_new_stream_start ("clear/video0"));

  GstCaps *wrong = gst_caps_copy (input);
  guint8 record[24] = {1, 0, 16, 29, 16};
  GstBuffer *config = gst_buffer_new_memdup (record, sizeof (record));
  gst_caps_set_simple (wrong, "dovi-configuration", GST_TYPE_BUFFER, config, NULL);
  gst_buffer_unref (config);
  source_gate_check (map, wrong, FALSE, "different coded configuration cannot borrow source proof");
  gst_pad_send_event (sink, gst_event_new_caps (wrong));
  require (klass->set_caps (base, wrong, wrong), "distinct valid B config under A proof negotiates original identity");
  GstBuffer *other = gst_buffer_new_allocate (NULL, 768, NULL);
  prepared = NULL;
  require (klass->prepare_output_buffer (base, other, &prepared) == GST_FLOW_OK && prepared == other,
      "same stream ID with unmatched valid B configuration preserves exact buffer identity");
  gst_clear_buffer (&prepared); gst_buffer_unref (other);

  gst_caps_unref (wrong);
  source_context (map, 1, TRUE, NULL, NULL);
  source_gate_check (map, input, FALSE, "CDM/source revoke restores identity negotiation");
  source_context (map, 1, FALSE, "clear/video0", coded);
  source_gate_check (map, input, FALSE, "same-revision late callback cannot undo protection revocation");
  source_context (map, 2, FALSE, "clear/video0", coded);
  source_gate_check (map, input, FALSE, "new source revision requires its own raw stream start");
  gst_pad_send_event (sink, gst_event_new_stream_start ("clear/video0"));
  source_gate_check (map, input, TRUE, "new clear source revision qualifies independently");
  g_object_get (map, "active-source-selection", &selection_a, NULL);
  gst_pad_send_event (sink, gst_event_new_flush_start ());
  g_object_get (map, "active-source-selection", &selection_b, NULL);
  require (!selection_b && selections.revoked_selection == selection_a,
      "filter-local flush revokes and clears the actual selected lease");
  source_gate_check (map, input, FALSE, "flush revokes the retained source lease immediately");
  source_context (map, 3, FALSE, "clear/video0", coded);
  gst_pad_send_event (sink, gst_event_new_flush_stop (TRUE));
  source_gate_check (map, input, TRUE, "flush stop restores exact sticky stream identity under the new proof");
  source_context (map, 1, TRUE, NULL, NULL);
  source_gate_check (map, input, TRUE, "older callback cannot revoke the newer source revision");
  GstCaps *protected = gst_caps_copy (coded);
  gst_structure_set_name (gst_caps_get_structure (protected, 0), "application/x-cenc");
  source_context (map, 3, FALSE, "clear/video0", protected);
  source_gate_check (map, input, FALSE, "protected replacement cannot retain clear source proof");
  gst_caps_unref (protected); gst_caps_unref (coded); gst_caps_unref (input);
  gst_pad_set_active (sink, FALSE); gst_pad_set_active (src, FALSE);
  gst_object_unref (sink); gst_object_unref (src); gst_object_unref (map);
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
  const gchar *accelerators[] = {"memory:CUDAMemory", "memory:VAMemory"};
  const gchar *accelerator_formats[] = {"NV12", "P010_10LE"};
  for (guint i = 0; i < G_N_ELEMENTS (accelerators); i++) {
    for (guint j = 0; j < G_N_ELEMENTS (accelerator_formats); j++) {
      GstCaps *input = caps_for (accelerator_formats[j], accelerators[i], TRUE);
      GstCaps *mapped = klass->transform_caps (base, GST_PAD_SINK, input, NULL);
      require (!gst_caps_is_empty (mapped) && gst_caps_is_fixed (mapped),
          "host-readable accelerator format has graded output");
      if (!gst_caps_is_empty (mapped)) {
        require (gst_caps_features_is_equal (gst_caps_get_features (mapped, 0),
                GST_CAPS_FEATURES_MEMORY_SYSTEM_MEMORY),
            "accelerator input produces system-memory output");
        require (klass->set_caps (base, input, mapped),
            "known host-readable accelerator input accepted");
      }
      require (gst_caps_can_intersect (reverse, input),
          "reverse exposes concrete host-readable accelerator input");
      gst_caps_unref (mapped);
      gst_caps_unref (input);
    }
    GstCaps *unqualified = caps_for ("RGBA", accelerators[i], TRUE);
    result = klass->transform_caps (base, GST_PAD_SINK, unqualified, NULL);
    require (gst_caps_is_empty (result),
        "accelerator domain does not imply all CPU formats are qualified");
    require (!klass->set_caps (base, unqualified, output),
        "unqualified accelerator format rejected at final gate");
    gst_caps_unref (unqualified);
    gst_caps_unref (result);
  }
  for (guint i = 0; i < gst_caps_get_size (reverse); i++) {
    const GstCapsFeatures *features = gst_caps_get_features (reverse, i);
    require (gst_caps_features_is_equal (features,
            GST_CAPS_FEATURES_MEMORY_SYSTEM_MEMORY) ||
        (gst_caps_features_get_size (features) == 1 &&
        (gst_caps_features_contains (features, "memory:CUDAMemory") ||
         gst_caps_features_contains (features, "memory:VAMemory"))),
        "reverse exposes only concrete CPU-readable domains");
  }
  /* Overlay composition meta (playsink's subtitleoverlay) pairs one to one,
   * in accelerator memory and in both spellings of system memory. */
  const gchar *overlay_memory[] = {"memory:CUDAMemory", "memory:VAMemory",
      GST_CAPS_FEATURE_MEMORY_SYSTEM_MEMORY, NULL};
  for (guint i = 0; i < G_N_ELEMENTS (overlay_memory); i++) {
    GstCaps *plain = caps_for ("P010_10LE", NULL, TRUE);
    gst_caps_set_features (plain, 0, overlay_memory[i] ?
        gst_caps_features_new (overlay_memory[i], NULL) : gst_caps_features_new_empty ());
    GstCaps *input = gst_caps_copy (plain);
    gst_caps_features_add (gst_caps_get_features (input, 0),
        GST_CAPS_FEATURE_META_GST_VIDEO_OVERLAY_COMPOSITION);
    GstCaps *mapped = klass->transform_caps (base, GST_PAD_SINK, input, NULL);
    require (!gst_caps_is_empty (mapped), "overlay input has graded output");
    GstCaps *plain_mapped = klass->transform_caps (base, GST_PAD_SINK, plain, NULL);
    require (!gst_caps_is_empty (plain_mapped), "plain input has graded output (control)");
    if (!gst_caps_is_empty (mapped) && !gst_caps_is_empty (plain_mapped)) {
      GstCaps *first = gst_caps_copy_nth (mapped, 0);
      GstCaps *plain_first = gst_caps_copy_nth (plain_mapped, 0);
      require (gst_caps_is_fixed (first), "overlay graded output is fixed");
      for (guint k = 0; k < gst_caps_get_size (mapped); k++)
        require (gst_caps_features_contains (gst_caps_get_features (mapped, k),
                GST_CAPS_FEATURE_META_GST_VIDEO_OVERLAY_COMPOSITION) &&
            !gst_caps_features_contains (gst_caps_get_features (mapped, k), "memory:CUDAMemory") &&
            !gst_caps_features_contains (gst_caps_get_features (mapped, k), "memory:VAMemory"),
            "overlay input produces system memory output with the overlay meta");
      require (klass->set_caps (base, input, first), "overlay input accepted");
      require (!klass->set_caps (base, input, plain_first),
          "overlay input rejected with an output that drops the meta");
      require (!klass->set_caps (base, plain, first),
          "plain input rejected with an output that claims the meta");
      GstCaps *overlay_reverse = klass->transform_caps (base, GST_PAD_SRC, first, NULL);
      GstCaps *plain_reverse = klass->transform_caps (base, GST_PAD_SRC, plain_first, NULL);
      require (gst_caps_can_intersect (overlay_reverse, input),
          "overlay output reverse exposes overlay input");
      require (!gst_caps_can_intersect (overlay_reverse, plain),
          "overlay output reverse excludes plain input");
      require (gst_caps_can_intersect (plain_reverse, plain),
          "plain output reverse exposes plain input (control)");
      require (!gst_caps_can_intersect (plain_reverse, input),
          "plain output reverse excludes overlay input");
      gst_caps_unref (plain_reverse);
      gst_caps_unref (overlay_reverse);
      gst_caps_unref (plain_first);
      gst_caps_unref (first);
    }
    gst_caps_unref (plain_mapped);
    gst_caps_unref (mapped);
    gst_caps_unref (input);
    gst_caps_unref (plain);
  }
  GstCaps *dma_overlay = gst_caps_copy (dma);
  gst_caps_features_add (gst_caps_get_features (dma_overlay, 0),
      GST_CAPS_FEATURE_META_GST_VIDEO_OVERLAY_COMPOSITION);
  result = klass->transform_caps (base, GST_PAD_SINK, dma_overlay, NULL);
  require (gst_caps_is_empty (result), "marked DMABuf with overlay forward query is empty");
  gst_caps_unref (result);
  gst_caps_unref (dma_overlay);
  require (klass->set_caps (base, nv12, output), "plain NV12 accepted again after overlay checks");
  GstCaps *gpu_output = gst_caps_copy (output);
  gst_caps_set_features (gpu_output, 0,
      gst_caps_features_new ("memory:CUDAMemory", NULL));
  require (!klass->set_caps (base, nv12, gpu_output),
      "graded output must remain system memory");
  result = klass->transform_caps (base, GST_PAD_SRC, gpu_output, NULL);
  require (gst_caps_is_empty (result), "reverse rejects accelerator-domain output");
  gst_caps_unref (gpu_output);
  gst_caps_unref (result);
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
  linked_query_controls (element, klass, output);
  pre_start_query_controls ();
  source_lifecycle_controls ();
  profile5_missing_picture_controls ();
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
