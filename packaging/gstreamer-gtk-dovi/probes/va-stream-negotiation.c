/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* CPU-only contract probe. Synthetic caps model decoder exports; no VA display,
 * decoder, GPU sink, Vulkan renderer or movie fixture is instantiated. */
#include <gst/base/gstbasetransform.h>
#include "gstvabasedecdovi.h"
#include <string.h>

static guint checks, failures;
static void require (gboolean success, const gchar *name)
{
  checks++;
  if (!success) { failures++; g_printerr ("FAIL %s\n", name); }
}
typedef struct {
  GstCaps *caps;
  gboolean normalize;
  const gchar *reject_modifier;
  guint queries, accepts;
} Peer;
static GstCaps *plain_copy (const GstCaps *caps, gboolean plain)
{
  GstCaps *copy = gst_caps_copy (caps);
  if (plain)
    for (guint i = 0; i < gst_caps_get_size (copy); i++)
      gst_structure_remove_fields (gst_caps_get_structure (copy, i),
          "dovi-configuration", "dovi-fel-decoder", NULL);
  return copy;
}
static gboolean query (GstPad *pad, GstObject *parent, GstQuery *q)
{
  Peer *peer = gst_pad_get_element_private (pad);
  if (GST_QUERY_TYPE (q) == GST_QUERY_CAPS) {
    GstCaps *filter, *answer = plain_copy (peer->caps, peer->normalize);
    gst_query_parse_caps (q, &filter); peer->queries++;
    if (filter) {
      GstCaps *wanted = plain_copy (filter, peer->normalize);
      GstCaps *matched = gst_caps_intersect_full (wanted, answer,
          GST_CAPS_INTERSECT_FIRST);
      gst_caps_unref (answer); gst_caps_unref (wanted); answer = matched;
    }
    gst_query_set_caps_result (q, answer); gst_caps_unref (answer); return TRUE;
  }
  if (GST_QUERY_TYPE (q) == GST_QUERY_ACCEPT_CAPS) {
    GstCaps *caps, *offered = plain_copy (peer->caps, peer->normalize);
    gst_query_parse_accept_caps (q, &caps);
    GstCaps *wanted = plain_copy (caps, peer->normalize);
    const gchar *modifier = gst_caps_get_size (caps) == 1 ?
        gst_structure_get_string (gst_caps_get_structure (caps, 0), "drm-format") : NULL;
    gboolean accepted = gst_caps_is_subset (wanted, offered) &&
        (!peer->reject_modifier || g_strcmp0 (modifier, peer->reject_modifier));
    peer->accepts++;
    gst_query_set_accept_caps_result (q, accepted);
    gst_caps_unref (wanted); gst_caps_unref (offered); return TRUE;
  }
  return gst_pad_query_default (pad, parent, q);
}
static GstCaps *coded (guint profile, guint compatibility, guint length)
{
  guint8 bytes[24] = {1, 0, 0, 29, 0};
  bytes[2] = profile << 1; bytes[4] = compatibility << 4;
  if (profile == 7) bytes[3] |= 2;
  GstBuffer *buffer = gst_buffer_new_memdup (bytes, MIN (length, sizeof (bytes)));
  GstCaps *caps = gst_caps_new_simple ("video/x-h265", "stream-format",
      G_TYPE_STRING, "hev1", "alignment", G_TYPE_STRING, "au",
      "dovi-configuration", GST_TYPE_BUFFER, buffer, NULL);
  gst_buffer_unref (buffer); return caps;
}
typedef struct {
  GstPad *src;
  gboolean reject_va;
  guint attempts;
  GstCaps *chosen;
} Choice;
static gboolean choose (GstCaps *candidate, gpointer data)
{
  Choice *choice = data;
  choice->attempts++;
  if (choice->reject_va && gst_caps_features_contains (
      gst_caps_get_features (candidate, 0), "memory:VAMemory"))
    return FALSE;
  if (!gst_caps_is_fixed (candidate) ||
      !gst_pad_peer_query_accept_caps (choice->src, candidate))
    return FALSE;
  choice->chosen = gst_caps_ref (candidate); return TRUE;
}
int main (int argc, char **argv)
{
  gst_init (&argc, &argv);
  if (argc != 2) return 2;
  GstElement *map = gst_element_factory_make ("gtkdovimap", NULL);
  if (!map) return 2;
  GstPlugin *plugin = gst_plugin_feature_get_plugin (
      GST_PLUGIN_FEATURE (gst_element_get_factory (map)));
  require (plugin && !g_strcmp0 (gst_plugin_get_filename (plugin), argv[1]),
      "exact requested mapper plugin is loaded");
  if (plugin) gst_object_unref (plugin);
  g_object_set (map, "destination-kind", 1u, NULL);
  GstPad *input = gst_element_get_static_pad (map, "sink");
  GstPad *output = gst_element_get_static_pad (map, "src");
  GstPad *src = gst_pad_new ("cpu-va-src", GST_PAD_SRC);
  GstPad *sink = gst_pad_new ("cpu-rgb-sink", GST_PAD_SINK);
  GstCaps *real = gst_caps_from_string (
      "video/x-raw(memory:VAMemory),format=P010_10LE,width=[1,4096],height=[1,4096];"
      "video/x-raw(memory:DMABuf),format=DMA_DRM,drm-format=(string){P010:0x0100000000000009,P010:0x0100000000000001},width=[1,4096],height=[1,4096];"
      "video/x-raw,format=P010_10LE,width=[1,4096],height=[1,4096]");
  Peer decoder = {real, FALSE, NULL, 0, 0};
  Peer rgb = {gst_caps_from_string ("video/x-raw,format=RGBA,width=16,height=16,"
      "framerate=24/1,pixel-aspect-ratio=1/1,colorimetry=sRGB"), TRUE, NULL, 0, 0};
  gst_pad_set_element_private (src, &decoder); gst_pad_set_query_function (src, query);
  gst_pad_set_element_private (sink, &rgb); gst_pad_set_query_function (sink, query);
  /* Model decodebin's provisional pad exposure, then query the actual linked
   * peer with the complete coded stream filter before selecting any output. */
  require (gst_pad_link_full (src, input, GST_PAD_LINK_CHECK_NOTHING) == GST_PAD_LINK_OK,
      "provisional decoder pad exposure links");
  require (gst_pad_link_full (output, sink, GST_PAD_LINK_CHECK_NOTHING) == GST_PAD_LINK_OK,
      "real downstream mapper peer links");
  GstCaps *encoded = coded (5, 0, 24);
  GBytes *configuration = gst_va_dovi_qualified_configuration (encoded);
  require (configuration != NULL, "complete coded P5 route qualifies");
  GstVideoInfo geometry;
  gst_video_info_set_format (&geometry, GST_VIDEO_FORMAT_P010_10LE, 16, 16);
  geometry.fps_n = 24; geometry.fps_d = 1;
  GstCaps *local = gst_pad_query_caps (src, NULL);
  GstCaps *allowed = gst_va_dovi_query_allowed (src, local, &geometry, configuration);
  require (!gst_caps_is_empty (allowed), "filtered marked peer returns feasible native inputs");
  for (guint i = 0; i < gst_caps_get_size (allowed); i++) {
    require (!gst_caps_features_contains (gst_caps_get_features (allowed, i), "memory:DMABuf"),
        "mapper rejects unsupported tiled DMA_DRM before decoder selection");
    GstCaps *one = gst_caps_copy_nth (allowed, i);
    require (gst_va_dovi_same_configuration (one, configuration),
        "allowed candidate retains the exact input configuration");
    gst_caps_unref (one);
  }
  Choice choice = {src, FALSE, 0, NULL};
  require (gst_va_dovi_foreach_candidate (allowed, choose, &choice), "a real fixed candidate is accepted");
  require (choice.chosen && gst_caps_features_contains (gst_caps_get_features (choice.chosen, 0),
      "memory:VAMemory"), "existing VA-first preference preserved");
  gst_clear_caps (&choice.chosen);
  choice.reject_va = TRUE; choice.attempts = 0;
  require (gst_va_dovi_foreach_candidate (allowed, choose, &choice), "rejected VA tries a feasible alternative");
  require (choice.chosen && gst_caps_features_is_equal (
      gst_caps_get_features (choice.chosen, 0), GST_CAPS_FEATURES_MEMORY_SYSTEM_MEMORY),
      "system fallback is actual supported memory, not a relabelled DMA allocation");
  gst_clear_caps (&choice.chosen); gst_caps_unref (allowed); gst_caps_unref (local);

  GstCaps *partial = coded (5, 0, 23);
  GBytes *unknown = gst_va_dovi_qualified_configuration (partial);
  require (!unknown, "reserved-truncated config stays on the unchanged legacy route");
  gst_caps_unref (partial);
  partial = coded (8, 1, 24); unknown = gst_va_dovi_qualified_configuration (partial);
  require (unknown != NULL, "complete P8.1 also qualifies");
  g_clear_pointer (&unknown, g_bytes_unref); gst_caps_unref (partial);
  partial = coded (7, 6, 24);
  gst_caps_set_simple (partial, "dovi-fel-decoder", G_TYPE_BOOLEAN, TRUE, NULL);
  unknown = gst_va_dovi_qualified_configuration (partial);
  require (!unknown, "VA never manufactures or trusts a coded P7 FEL decoder marker");
  gst_caps_unref (partial);
  GstCaps *absent = gst_caps_new_empty_simple ("video/x-h265");
  unknown = gst_va_dovi_qualified_configuration (absent);
  require (!unknown, "absent config stays unqualified"); gst_caps_unref (absent);
  GstCaps *encrypted = gst_caps_copy (encoded);
  gst_structure_set_name (gst_caps_get_structure (encrypted, 0), "application/x-cenc");
  unknown = gst_va_dovi_qualified_configuration (encrypted);
  require (!unknown, "protected coded caps are not a clear route");
  gst_caps_unref (encrypted);

  gst_pad_unlink (src, input);
  GstPad *dma_sink = gst_pad_new ("cpu-dma-sink", GST_PAD_SINK);
  Peer dma = {gst_caps_from_string ("video/x-raw(memory:DMABuf),format=DMA_DRM,"
      "drm-format=(string){P010:0x0100000000000009,P010:0x0100000000000001},"
      "width=16,height=16,framerate=24/1,pixel-aspect-ratio=1/1"), TRUE,
      "P010:0x0100000000000009", 0, 0};
  gst_pad_set_element_private (dma_sink, &dma); gst_pad_set_query_function (dma_sink, query);
  require (gst_pad_link_full (src, dma_sink, GST_PAD_LINK_CHECK_NOTHING) == GST_PAD_LINK_OK,
      "independent real modifier peer links");
  allowed = gst_va_dovi_query_allowed (src, real, &geometry, configuration);
  choice.reject_va = FALSE; choice.attempts = 0;
  require (gst_va_dovi_foreach_candidate (allowed, choose, &choice),
      "fixed rejection retries the remaining genuine modifier");
  require (choice.attempts == 2 && choice.chosen && !g_strcmp0 (
      gst_structure_get_string (gst_caps_get_structure (choice.chosen, 0), "drm-format"),
      "P010:0x0100000000000001"), "modifier bytes are preserved, never linear-mapped or invented");
  GstCaps *wrong = gst_caps_copy (choice.chosen);
  gst_structure_remove_field (gst_caps_get_structure (wrong, 0), "dovi-configuration");
  require (!gst_va_dovi_same_configuration (wrong, configuration),
      "unmarked final allocation cannot inherit qualification");
  gst_caps_unref (wrong); gst_clear_caps (&choice.chosen);
  gst_caps_unref (allowed); gst_pad_unlink (src, dma_sink);
  allowed = gst_va_dovi_query_allowed (src, real, &geometry, configuration);
  require (!gst_caps_is_empty (allowed), "unlinked early exposure stays provisional rather than failing");
  gst_caps_unref (allowed);
  gst_caps_unref (dma.caps); gst_object_unref (dma_sink);
  gst_pad_unlink (output, sink);
  gst_caps_unref (rgb.caps); gst_caps_unref (real); gst_caps_unref (encoded);
  g_bytes_unref (configuration); gst_object_unref (src); gst_object_unref (sink);
  gst_object_unref (input); gst_object_unref (output); gst_object_unref (map);
  g_print ("RESULT checks=%u failures=%u\n", checks, failures);
  return failures ? 1 : 0;
}
