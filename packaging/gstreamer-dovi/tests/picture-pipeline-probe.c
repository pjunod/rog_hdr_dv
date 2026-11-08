/* Resolved-picture extension of the reviewed raw-transport regression.
 * This keeps the independent AU scanner, gaps, reordering and flushing seek,
 * then also retains an owned resolved picture across the seek generation.
 * Run only after independent premerge review.
 * Uses ordinary native HEVC parser/decoder elements and a fakesink; no display.
 * The injection removes selected RPU NALs but deliberately retains old meta,
 * so the second parser must clear it from access units that now have no RPU.
 */
#include <gst/gst.h>
#include <gst/video/gstvideodovirpumeta.h>
#include <gstdovipicture.h>
#include <gst/video/video.h>
#include <string.h>

struct expected { gchar *hash; };
struct probe {
  GstElement *pipeline;
  GMutex lock;
  GHashTable *expected, *values;
  guint epoch, inputs, outputs[2], gaps, verified, failures, transformed, headers;
  GstClockTime last_input_pts;
  GstVideoInfo decoded_info;
  gboolean have_decoded_info;
  gboolean reordered, seek_requested, done_requested;
  gboolean input_flushing, output_flushing, transform_negative;
  GstDoviPicture *retained;
  gchar *retained_hash;
  guint64 retained_epoch;
  gboolean lifetime_verified, generation_verified;
};

static void
expected_free (gpointer p)
{
  struct expected *e = p;
  g_free (e->hash);
  g_free (e);
}

static void
post (struct probe *p, const gchar *name)
{
  gst_element_post_message (p->pipeline,
      gst_message_new_application (GST_OBJECT (p->pipeline),
          gst_structure_new_empty (name)));
}

/* Independent Annex-B scanner for the complete AU produced by the first
 * parser. Output is forced byte-stream/AU by negotiated test caps. */
static gsize
start_code (const guint8 *data, gsize size, gsize from, gsize *header)
{
  for (gsize i = from; i + 3 <= size; i++) {
    if (data[i] || data[i + 1])
      continue;
    if (data[i + 2] == 1) {
      *header = i + 3;
      return i;
    }
    if (i + 4 <= size && !data[i + 2] && data[i + 3] == 1) {
      *header = i + 4;
      return i;
    }
  }
  *header = size;
  return size;
}

static GstPadProbeReturn
input_event (GstPad *pad, GstPadProbeInfo *info, gpointer opaque)
{
  struct probe *p = opaque;
  GstEventType type = GST_EVENT_TYPE (GST_PAD_PROBE_INFO_EVENT (info));
  (void) pad;

  g_mutex_lock (&p->lock);
  if (type == GST_EVENT_FLUSH_START) {
    p->epoch++;
    p->input_flushing = p->output_flushing = TRUE;
    p->inputs = 0;
    p->last_input_pts = GST_CLOCK_TIME_NONE;
    g_hash_table_remove_all (p->expected);
  } else if (type == GST_EVENT_FLUSH_STOP) {
    /* A base parser may queue SEGMENT until it sees the first new buffer.
     * Input admission must never depend on that downstream segment event. */
    p->input_flushing = FALSE;
  }
  g_mutex_unlock (&p->lock);
  return GST_PAD_PROBE_OK;
}

static GstPadProbeReturn
inject (GstPad *pad, GstPadProbeInfo *info, gpointer opaque)
{
  struct probe *p = opaque;
  GstBuffer *in = GST_PAD_PROBE_INFO_BUFFER (info);
  GstMapInfo map;
  GByteArray *bytes = g_byte_array_new ();
  gchar *hash = NULL;
  gboolean omit, invalid = FALSE;
  guint rpus = 0, epoch;
  GstClockTime pts = GST_BUFFER_PTS (in);
  gsize pos, header;
  (void) pad;

  g_mutex_lock (&p->lock);
  if (p->input_flushing) {
    g_mutex_unlock (&p->lock);
    g_byte_array_unref (bytes);
    return GST_PAD_PROBE_DROP;
  }
  epoch = p->epoch;
  omit = (++p->inputs + p->epoch) % 7 == 3;
  if (GST_CLOCK_TIME_IS_VALID (p->last_input_pts) && pts < p->last_input_pts)
    p->reordered = TRUE;
  p->last_input_pts = pts;
  g_mutex_unlock (&p->lock);
  if (!GST_CLOCK_TIME_IS_VALID (pts) || !gst_buffer_map (in, &map, GST_MAP_READ)) {
    g_byte_array_unref (bytes);
    post (p, "probe-error");
    return GST_PAD_PROBE_DROP;
  }
  pos = start_code (map.data, map.size, 0, &header);
  if (pos != 0)
    invalid = TRUE;
  while (pos < map.size && !invalid) {
    gsize next_header, next = start_code (map.data, map.size, header, &next_header);
    if (next - header < 2) {
      invalid = TRUE;
      break;
    }
    guint type = (map.data[header] >> 1) & 63;
    if (type == 62) {
      rpus++;
      if (!omit && rpus == 1)
        hash = g_compute_checksum_for_data (G_CHECKSUM_SHA256,
            map.data + header + 2, next - header - 2);
    }
    if (type != 62 || !omit)
      g_byte_array_append (bytes, map.data + pos, next - pos);
    pos = next;
    header = next_header;
  }
  gst_buffer_unmap (in, &map);
  if (rpus > 1)
    invalid = TRUE;
  if (invalid) {
    g_free (hash);
    g_byte_array_unref (bytes);
    post (p, "probe-error");
    return GST_PAD_PROBE_DROP;
  }
  if (omit && rpus) {
    GstBuffer *out = gst_buffer_new_allocate (NULL, bytes->len, NULL);
    gst_buffer_fill (out, 0, bytes->data, bytes->len);
    gst_buffer_copy_into (out, in, GST_BUFFER_COPY_METADATA, 0, -1);
    gst_buffer_unref (in);
    GST_PAD_PROBE_INFO_DATA (info) = out;
  }
  g_byte_array_unref (bytes);
  struct expected *e = g_new0 (struct expected, 1);
  e->hash = hash;
  guint64 *key = g_new (guint64, 1);
  *key = pts;
  g_mutex_lock (&p->lock);
  if (p->input_flushing || p->epoch != epoch) {
    g_mutex_unlock (&p->lock);
    g_free (key);
    expected_free (e);
    return GST_PAD_PROBE_DROP;
  }
  if (g_hash_table_contains (p->expected, key)) {
    p->failures++;
    g_mutex_unlock (&p->lock);
    g_free (key);
    expected_free (e);
    post (p, "probe-error");
    return GST_PAD_PROBE_DROP;
  }
  if (hash)
    g_hash_table_add (p->values, g_strdup (hash));
  g_hash_table_insert (p->expected, key, e);
  g_mutex_unlock (&p->lock);
  return GST_PAD_PROBE_OK;
}

static gboolean
matches (GstBuffer *buffer, const struct expected *e)
{
  GstVideoDoviRpuMeta *meta = gst_buffer_get_video_dovi_rpu_meta (buffer);
  if (!e->hash)
    return meta == NULL;
  if (!meta || !meta->rpu || !meta->width || !meta->height)
    return FALSE;
  gsize size;
  const guint8 *data = g_bytes_get_data (meta->rpu, &size);
  gchar *hash = g_compute_checksum_for_data (G_CHECKSUM_SHA256, data, size);
  gboolean equal = !strcmp (hash, e->hash);
  g_free (hash);
  return equal;
}

/* Resolved metadata must match the independently scanned AU, while the raw
 * parser contract remains checked separately by the original scanner. */
static gboolean
matches_picture (struct probe *p, GstBuffer *buffer, const struct expected *e)
{
  GstDoviPictureMeta *meta = gst_buffer_get_dovi_picture_meta (buffer);
  if (!e->hash)
    return meta == NULL;
  if (!meta || !meta->picture)
    return FALSE;
  guint width, height;
  guint64 epoch;
  gst_dovi_picture_get_dimensions (meta->picture, &width, &height);
  gst_dovi_picture_get_identity (meta->picture, &epoch, NULL);
  GBytes *rpu = gst_dovi_picture_get_rpu (meta->picture);
  gsize size;
  const guint8 *data = g_bytes_get_data (rpu, &size);
  gchar *hash = g_compute_checksum_for_data (G_CHECKSUM_SHA256, data, size);
  gboolean equal = !strcmp (hash, e->hash) && width && height &&
      (!p->have_decoded_info ||
       (width == (guint) GST_VIDEO_INFO_WIDTH (&p->decoded_info) &&
        height == (guint) GST_VIDEO_INFO_HEIGHT (&p->decoded_info)));
  if (!p->retained) {
    p->retained = gst_dovi_picture_ref (meta->picture);
    p->retained_hash = g_strdup (hash);
    p->retained_epoch = epoch;
  } else {
    data = g_bytes_get_data (gst_dovi_picture_get_rpu (p->retained), &size);
    gchar *old = g_compute_checksum_for_data (G_CHECKSUM_SHA256, data, size);
    equal = equal && !strcmp (old, p->retained_hash);
    g_free (old);
    if (p->epoch) {
      p->lifetime_verified = TRUE;
      if (epoch != p->retained_epoch)
        p->generation_verified = TRUE;
      else
        equal = FALSE;
    }
  }
  g_free (hash);
  return equal;
}

static void
report_mismatch (const gchar *stage, struct probe *p, GstBuffer *buffer,
    const struct expected *expected)
{
  GstVideoDoviRpuMeta *meta = gst_buffer_get_video_dovi_rpu_meta (buffer);
  gchar *actual = NULL;
  if (meta && meta->rpu) {
    gsize size;
    const guint8 *bytes = g_bytes_get_data (meta->rpu, &size);
    actual = g_compute_checksum_for_data (G_CHECKSUM_SHA256, bytes, size);
  }
  g_printerr ("mismatch stage=%s epoch=%u pts=%" G_GUINT64_FORMAT
      " expected=%s actual=%s dimensions=%ux%u pending=%u inputs=%u\n",
      stage, p->epoch, GST_BUFFER_PTS (buffer),
      expected ? (expected->hash ? expected->hash : "NONE") : "MISSING",
      actual ? actual : "NONE", meta ? meta->width : 0, meta ? meta->height : 0,
      g_hash_table_size (p->expected), p->inputs);
  g_free (actual);
  if (!strcmp (stage, "parser")) {
    GstMapInfo map;
    if (gst_buffer_map (buffer, &map, GST_MAP_READ)) {
      gsize header, pos = start_code (map.data, map.size, 0, &header);
      guint count = 0;
      g_printerr ("parser-buffer flags=%u size=%zu nal-types=", GST_BUFFER_FLAGS (buffer), map.size);
      while (pos < map.size && header < map.size && count++ < 16) {
        g_printerr ("%u,", (map.data[header] >> 1) & 63);
        pos = start_code (map.data, map.size, header, &header);
      }
      g_printerr ("\n");
      gst_buffer_unmap (buffer, &map);
    }
  }
}

/* h265parse may send VPS/SPS/PPS separately before a picture. Such a
 * HEADER buffer has no presentation timestamp and is not a decoded picture. */
static gboolean
parameter_sets_only (GstBuffer *buffer)
{
  GstMapInfo map;
  gsize header, pos;
  guint count = 0;
  gboolean valid = TRUE;
  if (!GST_BUFFER_FLAG_IS_SET (buffer, GST_BUFFER_FLAG_HEADER) ||
      gst_buffer_get_video_dovi_rpu_meta (buffer) ||
      !gst_buffer_map (buffer, &map, GST_MAP_READ))
    return FALSE;
  pos = start_code (map.data, map.size, 0, &header);
  valid = pos == 0;
  while (pos < map.size && valid) {
    gsize next_header, next = start_code (map.data, map.size, header, &next_header);
    guint type = header < map.size ? (map.data[header] >> 1) & 63 : 0;
    valid = next - header >= 2 && type >= 32 && type <= 34;
    count++;
    pos = next;
    header = next_header;
  }
  gst_buffer_unmap (buffer, &map);
  return valid && count;
}

static GstPadProbeReturn
check_parser (GstPad *pad, GstPadProbeInfo *info, gpointer opaque)
{
  struct probe *p = opaque;
  (void) pad;
  GstBuffer *buffer = GST_PAD_PROBE_INFO_BUFFER (info);
  guint64 pts = GST_BUFFER_PTS (buffer);
  gboolean good;
  if (!GST_CLOCK_TIME_IS_VALID (pts) && parameter_sets_only (buffer)) {
    g_mutex_lock (&p->lock);
    p->headers++;
    g_mutex_unlock (&p->lock);
    return GST_PAD_PROBE_OK;
  }
  g_mutex_lock (&p->lock);
  if (p->input_flushing) {
    g_mutex_unlock (&p->lock);
    return GST_PAD_PROBE_OK;
  }
  struct expected *e = g_hash_table_lookup (p->expected, &pts);
  good = e && matches (buffer, e);
  if (good)
    p->verified++;
  else {
    p->failures++;
    report_mismatch ("parser", p, buffer, e);
  }
  g_mutex_unlock (&p->lock);
  if (!good)
    post (p, "probe-error");
  return GST_PAD_PROBE_OK;
}

static GstPadProbeReturn
check_decoded (GstPad *pad, GstPadProbeInfo *info, gpointer opaque)
{
  struct probe *p = opaque;
  if (GST_PAD_PROBE_INFO_TYPE (info) & GST_PAD_PROBE_TYPE_EVENT_DOWNSTREAM) {
    GstEventType type = GST_EVENT_TYPE (GST_PAD_PROBE_INFO_EVENT (info));
    GstVideoInfo decoded_info;
    gboolean have_info = FALSE;
    if (type == GST_EVENT_CAPS) {
      GstCaps *caps;
      gst_event_parse_caps (GST_PAD_PROBE_INFO_EVENT (info), &caps);
      have_info = gst_video_info_from_caps (&decoded_info, caps);
    }
    g_mutex_lock (&p->lock);
    if (have_info) {
      p->decoded_info = decoded_info;
      p->have_decoded_info = TRUE;
    }
    if (type == GST_EVENT_FLUSH_START)
      p->output_flushing = TRUE;
    else if (type == GST_EVENT_SEGMENT)
      p->output_flushing = FALSE;
    g_mutex_unlock (&p->lock);
    return GST_PAD_PROBE_OK;
  }
  GstBuffer *buffer = GST_PAD_PROBE_INFO_BUFFER (info);
  guint64 pts = GST_BUFFER_PTS (buffer);
  gboolean good, request_seek = FALSE, done = FALSE;
  (void) pad;
  g_mutex_lock (&p->lock);
  if (p->output_flushing) {
    g_mutex_unlock (&p->lock);
    return GST_PAD_PROBE_OK;
  }
  struct expected *e = g_hash_table_lookup (p->expected, &pts);
  good = e && matches_picture (p, buffer, e);
  if (good) {
    p->gaps += e->hash == NULL;
    p->outputs[p->epoch != 0]++;
    g_hash_table_remove (p->expected, &pts);
    if (!p->epoch && p->outputs[0] >= 30 && !p->seek_requested) {
      p->seek_requested = request_seek = TRUE;
    } else if (p->epoch && p->outputs[1] >= 60 && !p->done_requested) {
      p->done_requested = done = TRUE;
    }
  } else {
    p->failures++;
    report_mismatch ("decoder", p, buffer, e);
  }
  g_mutex_unlock (&p->lock);
  if (!good)
    post (p, "probe-error");
  else if (request_seek)
    post (p, "probe-seek");
  else if (done)
    post (p, "probe-done");
  return GST_PAD_PROBE_OK;
}

static GstPadProbeReturn
check_transformed (GstPad *pad, GstPadProbeInfo *info, gpointer opaque)
{
  struct probe *p = opaque;
  GstBuffer *buffer = GST_PAD_PROBE_INFO_BUFFER (info);
  gboolean failed = FALSE, comparable = TRUE;
  GstCaps *caps = gst_pad_get_current_caps (pad);
  GstVideoInfo info_out;
  gboolean have_info = caps && gst_video_info_from_caps (&info_out, caps);
  gst_clear_caps (&caps);

  g_mutex_lock (&p->lock);
  if (!p->output_flushing) {
    comparable = have_info && p->have_decoded_info &&
        GST_VIDEO_INFO_FORMAT (&info_out) == GST_VIDEO_INFO_FORMAT (&p->decoded_info) &&
        GST_VIDEO_INFO_WIDTH (&info_out) == GST_VIDEO_INFO_WIDTH (&p->decoded_info) &&
        GST_VIDEO_INFO_HEIGHT (&info_out) == GST_VIDEO_INFO_HEIGHT (&p->decoded_info);
    if (comparable) {
      p->transformed++;
      failed = gst_buffer_get_dovi_picture_meta (buffer) != NULL;
      p->failures += failed;
    }
  }
  g_mutex_unlock (&p->lock);
  if (failed)
    post (p, "probe-error");
  else if (!comparable) {
    g_printerr ("orientation negative requires unchanged format and dimensions\n");
    post (p, "probe-inconclusive");
  }
  return GST_PAD_PROBE_OK;
}

int
main (int argc, char **argv)
{
  if ((argc != 3 && argc != 4) ||
      (strcmp (argv[1], "avdec_h265") && strcmp (argv[1], "vah265dec") &&
       strcmp (argv[1], "nvh265dec")) ||
      (argc == 4 && strcmp (argv[3], "rotate-180")))
    return 2;
  gst_init (&argc, &argv);
  struct probe p = {.last_input_pts = GST_CLOCK_TIME_NONE,
      .transform_negative = argc == 4};
  g_mutex_init (&p.lock);
  p.expected = g_hash_table_new_full (g_int64_hash, g_int64_equal, g_free, expected_free);
  p.values = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, NULL);
  gchar *file = g_strescape (argv[2], NULL);
  gchar *description = g_strdup_printf (
      "filesrc location=\"%s\" ! qtdemux ! h265parse name=au ! "
      "video/x-h265,stream-format=byte-stream,alignment=au ! identity name=inject ! "
      "h265parse name=check ! %s name=decoder ! %s identity sleep-time=2000 ! fakesink sync=false",
      file, argv[1], p.transform_negative ? "vapostproc name=transform !" : "");
  GError *error = NULL;
  p.pipeline = gst_parse_launch (description, &error);
  g_free (description);
  g_free (file);
  if (!p.pipeline || error) {
    g_printerr ("pipeline: %s\n", error ? error->message : "unavailable");
    return 2;
  }
  GstElement *injection = gst_bin_get_by_name (GST_BIN (p.pipeline), "inject");
  GstElement *parser = gst_bin_get_by_name (GST_BIN (p.pipeline), "check");
  GstElement *decoder = gst_bin_get_by_name (GST_BIN (p.pipeline), "decoder");
  GstPad *pad = gst_element_get_static_pad (injection, "src");
  gst_pad_add_probe (pad, GST_PAD_PROBE_TYPE_EVENT_DOWNSTREAM |
      GST_PAD_PROBE_TYPE_EVENT_FLUSH, input_event, &p, NULL);
  gst_pad_add_probe (pad, GST_PAD_PROBE_TYPE_BUFFER, inject, &p, NULL);
  gst_object_unref (pad);
  pad = gst_element_get_static_pad (parser, "src");
  gst_pad_add_probe (pad, GST_PAD_PROBE_TYPE_BUFFER, check_parser, &p, NULL);
  gst_object_unref (pad);
  pad = gst_element_get_static_pad (decoder, "src");
  gst_pad_add_probe (pad, GST_PAD_PROBE_TYPE_BUFFER | GST_PAD_PROBE_TYPE_EVENT_DOWNSTREAM |
      GST_PAD_PROBE_TYPE_EVENT_FLUSH, check_decoded, &p, NULL);
  gst_object_unref (pad);
  if (p.transform_negative) {
    GstElement *transform = gst_bin_get_by_name (GST_BIN (p.pipeline), "transform");
    GParamSpec *property = g_object_class_find_property (
        G_OBJECT_GET_CLASS (transform), "video-direction");
    gint configured = GST_VIDEO_ORIENTATION_IDENTITY;
    if (!property) {
      g_printerr ("native vapostproc has no video-direction property\n");
      return 2;
    }
    g_object_set (transform, "video-direction", GST_VIDEO_ORIENTATION_180, NULL);
    g_object_get (transform, "video-direction", &configured, NULL);
    if (configured != GST_VIDEO_ORIENTATION_180) {
      g_printerr ("native vapostproc rejected 180-degree rotation\n");
      return 2;
    }
    pad = gst_element_get_static_pad (transform, "src");
    gst_pad_add_probe (pad, GST_PAD_PROBE_TYPE_BUFFER, check_transformed, &p, NULL);
    gst_object_unref (pad);
    gst_object_unref (transform);
  }
  gst_object_unref (injection);
  gst_object_unref (parser);
  gst_object_unref (decoder);
  GstBus *bus = gst_element_get_bus (p.pipeline);
  int result = 2;
  if (gst_element_set_state (p.pipeline, GST_STATE_PLAYING) == GST_STATE_CHANGE_FAILURE)
    goto done;
  for (;;) {
    GstMessage *message = gst_bus_timed_pop_filtered (bus, 90 * GST_SECOND,
        GST_MESSAGE_ERROR | GST_MESSAGE_EOS | GST_MESSAGE_APPLICATION);
    if (!message)
      break;
    gboolean stop = FALSE;
    if (GST_MESSAGE_TYPE (message) == GST_MESSAGE_ERROR) {
      gchar *debug;
      gst_message_parse_error (message, &error, &debug);
      g_printerr ("native pipeline: %s (%s)\n", error->message, debug ? debug : "");
      g_clear_error (&error);
      g_free (debug);
      stop = TRUE;
      result = 1;
    } else if (GST_MESSAGE_TYPE (message) == GST_MESSAGE_APPLICATION) {
      const gchar *name = gst_structure_get_name (gst_message_get_structure (message));
      if (!strcmp (name, "probe-seek")) {
        if (!gst_element_seek_simple (p.pipeline, GST_FORMAT_TIME,
                GST_SEEK_FLAG_FLUSH | GST_SEEK_FLAG_KEY_UNIT, 0)) {
          stop = TRUE;
          result = 1;
        }
      } else if (!strcmp (name, "probe-done")) {
        result = 0;
        stop = TRUE;
      } else if (!strcmp (name, "probe-error")) {
        result = 1;
        stop = TRUE;
      } else if (!strcmp (name, "probe-inconclusive")) {
        result = 2;
        stop = TRUE;
      }
    } else {
      stop = TRUE;
    }
    gst_message_unref (message);
    if (stop)
      break;
  }
done:
  gst_element_set_state (p.pipeline, GST_STATE_NULL);
  if (!result && (!p.lifetime_verified || !p.generation_verified || p.failures || !p.reordered || !p.epoch || !p.gaps ||
          p.outputs[0] < 30 || p.outputs[1] < 60 || g_hash_table_size (p.values) < 2 ||
          (p.transform_negative && !p.transformed)))
    result = 2; /* Insufficient fixture evidence never becomes a pass. */
  g_printerr ("decoder=%s before=%u after=%u gaps=%u parser-verified=%u "
      "flushes=%u reordered=%d distinct-rpu=%u transformed=%u headers=%u errors=%u result=%d lifetime=%d generation=%d\n",
      argv[1], p.outputs[0], p.outputs[1], p.gaps, p.verified, p.epoch,
      p.reordered, g_hash_table_size (p.values), p.transformed, p.headers, p.failures, result, p.lifetime_verified, p.generation_verified);
  gst_object_unref (bus);
  gst_dovi_picture_unref (p.retained);
  g_free (p.retained_hash);
  gst_object_unref (p.pipeline);
  g_hash_table_unref (p.expected);
  g_hash_table_unref (p.values);
  g_mutex_clear (&p.lock);
  return result;
}
