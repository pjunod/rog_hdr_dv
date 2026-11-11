/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* Headless ordinary uridecodebin boundary observer. No decoder rank changes. */
#include <gst/app/gstappsink.h>
#include <gstdovipicture.h>
#include <stdio.h>
#include <string.h>

typedef struct {
  GMutex lock;
  FILE *trace;
  guint frames, pictures, profile7, config7, residual_pending, verified;
  guint aus, rpu_aus, el_aus, bl_aus, malformed, parser_probes;
  guint identity_errors, pts_errors, phases, seek_success;
  guint width, height;
  guint64 last_epoch, last_id, first_epoch, first_id;
  GstClockTime last_pts;
  gboolean have_last;
  GstDoviPicture *retained;
  GstBuffer *fel_copy;
  gchar *fel_digest;
  guint paired[2], phase_frames[2];
  GHashTable *decoders, *identities;
} State;

static void count_nal (const guint8 *p, gsize n, gboolean *bl,
    gboolean *rpu, gboolean *el)
{
  if (n < 2 || (p[0] & 0x80) || !(p[1] & 7)) return;
  guint type = (p[0] >> 1) & 63;
  guint layer = ((p[0] & 1) << 5) | (p[1] >> 3);
  if (!layer && type < 32) *bl = TRUE;
  if (!layer && type == 62) *rpu = TRUE;
  if (type == 63 && n >= 4) *el = TRUE;
}

static gsize start_code (const guint8 *p, gsize n, gsize from, guint *length)
{
  for (gsize i = from; i + 3 <= n; i++) {
    if (p[i] || p[i + 1]) continue;
    if (p[i + 2] == 1) { *length = 3; return i; }
    if (i + 4 <= n && !p[i + 2] && p[i + 3] == 1) {
      *length = 4; return i;
    }
  }
  return n;
}

static GstPadProbeReturn observe_au (GstPad *pad, GstPadProbeInfo *probe,
    gpointer opaque)
{
  State *s = opaque;
  GstBuffer *buffer = GST_PAD_PROBE_INFO_BUFFER (probe);
  if (!buffer) return GST_PAD_PROBE_OK;
  GstCaps *caps = gst_pad_get_current_caps (pad);
  if (!caps) return GST_PAD_PROBE_OK;
  const GstStructure *st = gst_caps_get_structure (caps, 0);
  const gchar *format = gst_structure_get_string (st, "stream-format");
  guint length_size = 0;
  const GValue *codec = gst_structure_get_value (st, "codec_data");
  if (codec && GST_VALUE_HOLDS_BUFFER (codec)) {
    GstMapInfo m;
    if (gst_buffer_map (gst_value_get_buffer (codec), &m, GST_MAP_READ)) {
      if (m.size >= 23 && m.data[0] == 1) length_size = (m.data[21] & 3) + 1;
      gst_buffer_unmap (gst_value_get_buffer (codec), &m);
    }
  }
  gboolean bl = FALSE, rpu = FALSE, el = FALSE, invalid = FALSE;
  GstMapInfo m;
  if (!gst_buffer_map (buffer, &m, GST_MAP_READ)) {
    gst_caps_unref (caps); return GST_PAD_PROBE_OK;
  }
  if (m.size > 64u * 1024u * 1024u) invalid = TRUE;
  else if (format && !strcmp (format, "byte-stream")) {
    guint prefix = 0; gsize at = start_code (m.data, m.size, 0, &prefix);
    if (at == m.size) invalid = TRUE;
    while (at < m.size) {
      gsize begin = at + prefix;
      guint next_prefix = 0;
      gsize end = start_code (m.data, m.size, begin, &next_prefix);
      if (end - begin < 2) invalid = TRUE;
      else count_nal (m.data + begin, end - begin, &bl, &rpu, &el);
      at = end; prefix = next_prefix;
    }
  } else if (length_size) {
    gsize at = 0;
    while (at < m.size) {
      if (length_size > m.size - at) { invalid = TRUE; break; }
      guint32 n = 0;
      for (guint i = 0; i < length_size; i++) n = (n << 8) | m.data[at++];
      if (n < 2 || n > m.size - at) { invalid = TRUE; break; }
      count_nal (m.data + at, n, &bl, &rpu, &el); at += n;
    }
  } else invalid = TRUE;
  g_mutex_lock (&s->lock);
  s->aus++; s->bl_aus += bl; s->rpu_aus += rpu; s->el_aus += el;
  s->malformed += invalid;
  fprintf (s->trace, "AU phase=%u pts=%" G_GUINT64_FORMAT " bl=%d rpu=%d el=%d invalid=%d\n",
      s->phases, GST_BUFFER_PTS (buffer), bl, rpu, el, invalid);
  g_mutex_unlock (&s->lock);
  gst_buffer_unmap (buffer, &m); gst_caps_unref (caps);
  return GST_PAD_PROBE_OK;
}

static void element_setup (GstBin *bin, GstBin *sub_bin, GstElement *element, gpointer opaque)
{
  (void) bin; (void) sub_bin;
  State *s = opaque;
  GstElementFactory *factory = gst_element_get_factory (element);
  if (!factory) return;
  const gchar *name = gst_plugin_feature_get_name (GST_PLUGIN_FEATURE (factory));
  const gchar *klass = gst_element_factory_get_metadata (factory, GST_ELEMENT_METADATA_KLASS);
  if (klass && strstr (klass, "Decoder") && strstr (klass, "Video")) {
    g_mutex_lock (&s->lock); g_hash_table_add (s->decoders, g_strdup (name));
    g_mutex_unlock (&s->lock);
  }
  if (!strcmp (name, "h265parse")) {
    GstPad *pad = gst_element_get_static_pad (element, "src");
    if (pad) {
      gst_pad_add_probe (pad, GST_PAD_PROBE_TYPE_BUFFER, observe_au, s, NULL);
      gst_object_unref (pad); s->parser_probes++;
    }
  }
}

/* The staged decoder supports planar 10-bit 4:2:0. Hash active samples only,
 * so the retained full-buffer-copy control is independent of stride/padding. */
static gchar *digest_fel (const AVFrame *frame)
{
  if (!frame || frame->format != AV_PIX_FMT_YUV420P10LE ||
      frame->width <= 0 || frame->height <= 0) return NULL;
  GChecksum *sum = g_checksum_new (G_CHECKSUM_SHA256);
  for (guint i = 0; i < 3; i++) {
    gint rows = i ? (frame->height + 1) / 2 : frame->height;
    gint bytes = 2 * (i ? (frame->width + 1) / 2 : frame->width);
    for (gint y = 0; y < rows; y++)
      g_checksum_update (sum, frame->data[i] + (gssize) y * frame->linesize[i], bytes);
  }
  gchar *digest = g_strdup (g_checksum_get_string (sum));
  g_checksum_free (sum);
  return digest;
}

static GstFlowReturn new_sample (GstAppSink *sink, gpointer opaque)
{
  State *s = opaque;
  GstSample *sample = gst_app_sink_pull_sample (sink);
  if (!sample) return GST_FLOW_EOS;
  GstBuffer *buffer = gst_sample_get_buffer (sample);
  GstVideoInfo info;
  gst_video_info_init (&info);
  if (!gst_video_info_from_caps (&info, gst_sample_get_caps (sample))) {
    gst_sample_unref (sample); return GST_FLOW_ERROR;
  }
  GstDoviPictureMeta *meta = gst_buffer_get_dovi_picture_meta (buffer);
  g_mutex_lock (&s->lock);
  s->frames++; s->width = info.width; s->height = info.height;
  guint64 epoch = 0, id = 0;
  s->phase_frames[s->phases]++;
  const AVFrame *fel = gst_dovi_picture_meta_get_fel (meta);
  if (fel) {
    s->paired[s->phases]++;
    if (!s->fel_copy) {
      s->fel_digest = digest_fel (fel);
      s->fel_copy = gst_buffer_copy (buffer);
    }
  }
  if (meta && meta->picture) {
    s->pictures++;
    gst_dovi_picture_get_identity (meta->picture, &epoch, &id);
    s->profile7 += gst_dovi_picture_get_profile (meta->picture) == 7;
    const AVDOVIDecoderConfigurationRecord *c = gst_dovi_picture_get_stream_config (meta->picture);
    s->config7 += c && c->dv_profile == 7 && c->el_present_flag;
    GstDoviEnhancement e = gst_dovi_picture_get_enhancement (meta->picture);
    s->residual_pending += e == GST_DOVI_ENHANCEMENT_UNRECONSTRUCTED;
    s->verified += e == GST_DOVI_ENHANCEMENT_VERIFIED;
    gchar *identity = g_strdup_printf ("%" G_GUINT64_FORMAT ":%" G_GUINT64_FORMAT, epoch, id);
    if (!g_hash_table_add (s->identities, identity)) s->identity_errors++;
    if (s->have_last && epoch == s->last_epoch && GST_CLOCK_TIME_IS_VALID (s->last_pts) &&
        GST_CLOCK_TIME_IS_VALID (GST_BUFFER_PTS (buffer)) && GST_BUFFER_PTS (buffer) < s->last_pts)
      s->pts_errors++;
    s->last_epoch = epoch; s->last_id = id; s->last_pts = GST_BUFFER_PTS (buffer); s->have_last = TRUE;
    if (!s->retained) {
      s->retained = gst_dovi_picture_ref (meta->picture); s->first_epoch = epoch; s->first_id = id;
    }
  }
  fprintf (s->trace, "FRAME phase=%u pts=%" G_GUINT64_FORMAT " epoch=%" G_GUINT64_FORMAT
      " id=%" G_GUINT64_FORMAT " meta=%d width=%u height=%u\n", s->phases,
      GST_BUFFER_PTS (buffer), epoch, id, meta != NULL, s->width, s->height);
  g_mutex_unlock (&s->lock);
  gst_sample_unref (sample); return GST_FLOW_OK;
}

static void pad_added (GstElement *decode, GstPad *pad, gpointer pipeline)
{
  (void) decode;
  GstCaps *caps = gst_pad_get_current_caps (pad);
  if (!caps) return;
  gboolean video = g_str_has_prefix (gst_structure_get_name (gst_caps_get_structure (caps, 0)), "video/x-raw");
  GstElement *sink = video ? gst_bin_get_by_name (pipeline, "observer") : gst_element_factory_make ("fakesink", NULL);
  if (!video && sink) { g_object_set (sink, "sync", FALSE, NULL); gst_bin_add (pipeline, sink); gst_element_sync_state_with_parent (sink); }
  if (sink) {
    GstPad *target = gst_element_get_static_pad (sink, "sink");
    if (!gst_pad_is_linked (target)) gst_pad_link (pad, target);
    gst_object_unref (target); if (video) gst_object_unref (sink);
  }
  gst_caps_unref (caps);
}

int main (int argc, char **argv)
{
  gst_init (&argc, &argv);
  gboolean require_fel = argc == 4 && !strcmp (argv[3], "--require-fel");
  if (argc != 3 && !require_fel) return 2;
  State s = {0}; g_mutex_init (&s.lock); s.last_pts = GST_CLOCK_TIME_NONE;
  s.trace = fopen (argv[2], "wx"); if (!s.trace) return 2;
  s.decoders = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, NULL);
  s.identities = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, NULL);
  GstElement *pipeline = gst_pipeline_new ("fel-boundary");
  GstElement *decode = gst_element_factory_make ("uridecodebin", "ordinary-decode");
  GstElement *sink = gst_element_factory_make ("appsink", "observer");
  if (!decode || !sink) return 2;
  g_object_set (decode, "uri", argv[1], NULL);
  g_object_set (sink, "emit-signals", TRUE, "sync", FALSE, NULL);
  g_signal_connect (pipeline, "deep-element-added", G_CALLBACK (element_setup), &s);
  g_signal_connect (decode, "pad-added", G_CALLBACK (pad_added), pipeline);
  g_signal_connect (sink, "new-sample", G_CALLBACK (new_sample), &s);
  gst_bin_add_many (GST_BIN (pipeline), decode, sink, NULL);
  GstBus *bus = gst_element_get_bus (pipeline);
  gboolean ok = gst_element_set_state (pipeline, GST_STATE_PLAYING) != GST_STATE_CHANGE_FAILURE;
  while (ok) {
    GstMessage *message = gst_bus_timed_pop_filtered (bus, 60 * GST_SECOND, GST_MESSAGE_ERROR | GST_MESSAGE_EOS);
    if (!message) { ok = FALSE; break; }
    if (GST_MESSAGE_TYPE (message) == GST_MESSAGE_ERROR) {
      GError *error = NULL; gchar *debug = NULL; gst_message_parse_error (message, &error, &debug);
      fprintf (s.trace, "ERROR %s %s\n", error->message, debug ? debug : "");
      g_clear_error (&error); g_free (debug); ok = FALSE;
    } else if (!s.seek_success) {
      g_mutex_lock (&s.lock); s.phases++; g_mutex_unlock (&s.lock);
      s.seek_success = gst_element_seek_simple (pipeline, GST_FORMAT_TIME, GST_SEEK_FLAG_FLUSH | GST_SEEK_FLAG_KEY_UNIT, 0);
      if (!s.seek_success) ok = FALSE;
    } else { gst_message_unref (message); break; }
    gst_message_unref (message);
  }
  gst_element_set_state (pipeline, GST_STATE_NULL);
  gboolean retained_ok = FALSE;
  if (s.retained) {
    guint64 epoch, id; gst_dovi_picture_get_identity (s.retained, &epoch, &id);
    retained_ok = epoch == s.first_epoch && id == s.first_id &&
        gst_dovi_picture_get_rpu (s.retained) &&
        g_bytes_get_size (gst_dovi_picture_get_rpu (s.retained)) > 0;
  }
  const AVFrame *copied_fel = s.fel_copy ? gst_dovi_picture_meta_get_fel (
      gst_buffer_get_dovi_picture_meta (s.fel_copy)) : NULL;
  gchar *copied_digest = digest_fel (copied_fel);
  gboolean retained_fel_ok = copied_digest && !g_strcmp0 (copied_digest, s.fel_digest);
  g_free (copied_digest); g_free (s.fel_digest);
  gst_clear_buffer (&s.fel_copy);
  if (require_fel)
    ok = ok && s.seek_success && retained_ok && retained_fel_ok && !s.identity_errors &&
        !s.pts_errors && !s.verified && s.residual_pending == s.frames &&
        s.paired[0] && s.paired[1] && s.paired[0] == s.phase_frames[0] &&
        s.paired[1] == s.phase_frames[1];
  printf ("{\"paired_before_seek\":%u,\"paired_after_seek\":%u,"
      "\"copied_fel_pixels_retained\":%s,", s.paired[0], s.paired[1],
      retained_fel_ok ? "true" : "false");
  printf ("\"pipeline_ok\":%s,\"frames\":%u,\"pictures\":%u,\"profile7\":%u,"
      "\"known_profile7_EL_config\":%u,\"unreconstructed\":%u,\"verified\":%u,"
      "\"width\":%u,\"height\":%u,\"aus\":%u,\"BL_AUs\":%u,\"RPU_AUs\":%u,"
      "\"EL_AUs\":%u,\"malformed_AUs\":%u,\"identity_errors\":%u,\"PTS_errors\":%u,"
      "\"seek_success\":%u,\"retained_picture_valid\":%s,\"decoders\":[",
      ok ? "true" : "false", s.frames, s.pictures, s.profile7, s.config7, s.residual_pending,
      s.verified, s.width, s.height, s.aus, s.bl_aus, s.rpu_aus, s.el_aus, s.malformed,
      s.identity_errors, s.pts_errors, s.seek_success, retained_ok ? "true" : "false");
  GHashTableIter iterator; gpointer key; gboolean first = TRUE;
  g_hash_table_iter_init (&iterator, s.decoders);
  while (g_hash_table_iter_next (&iterator, &key, NULL)) {
    printf ("%s\"%s\"", first ? "" : ",", (gchar *) key); first = FALSE;
  }
  puts ("]}");
  gst_dovi_picture_unref (s.retained); fclose (s.trace); g_hash_table_unref (s.decoders); g_hash_table_unref (s.identities);
  gst_object_unref (bus); gst_object_unref (pipeline); g_mutex_clear (&s.lock);
  return ok ? 0 : 1;
}
