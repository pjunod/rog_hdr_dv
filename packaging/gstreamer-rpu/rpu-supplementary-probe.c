/* SPDX-License-Identifier: MIT
 * Supplementary raw-RPU transport checks. Compile before independent review;
 * execute only after that review. No renderer, display or mapper is involved.
 *
 * rpu-supplementary-probe regions
 * rpu-supplementary-probe nal|duplicate|oversize|va-size fixture.mp4
 */
#include <gst/gst.h>
#include <gst/video/video.h>
#include <gst/video/gstvideodovirpumeta.h>
#include <string.h>

struct observation {
  GMutex lock;
  GstElement *sizecaps;
  guint absent_meta;
  const gchar *mode;
  guint failures, positives, mutated, checked, rpu_nals, pictures, decoded_rpu, matched;
  GHashTable *tagged_inputs;
  GstVideoInfo decoded_info;
  gboolean have_decoded_info, dimension_change, format_preserved, color_preserved;
};

static gsize
start_code (const guint8 *p, gsize size, gsize from, gsize *header)
{
  for (gsize i = from; i + 3 <= size; i++) {
    if (p[i] || p[i + 1]) continue;
    if (p[i + 2] == 1) { *header = i + 3; return i; }
    if (i + 4 <= size && !p[i + 2] && p[i + 3] == 1) {
      *header = i + 4; return i;
    }
  }
  *header = size;
  return size;
}

static gboolean
same_rpu (GstBuffer *buffer, const guint8 *bytes, gsize size)
{
  GstVideoDoviRpuMeta *meta = gst_buffer_get_video_dovi_rpu_meta (buffer);
  gsize actual_size = 0;
  const guint8 *actual = meta && meta->rpu ?
      g_bytes_get_data (meta->rpu, &actual_size) : NULL;
  return actual && actual_size == size && !memcmp (actual, bytes, size);
}

static GstPadProbeReturn
seed_and_mutate (GstPad *pad, GstPadProbeInfo *info, gpointer data)
{
  struct observation *o = data;
  GstBuffer *in = GST_PAD_PROBE_INFO_BUFFER (info);
  GstMapInfo map;
  GByteArray *kept = g_byte_array_new ();
  const guint8 *rpu = NULL;
  gsize rpu_size = 0, pos, header;
  guint rpus = 0;
  gboolean valid;
  (void) pad;
  if (!gst_buffer_map (in, &map, GST_MAP_READ)) {
    g_mutex_lock (&o->lock); o->failures++; g_mutex_unlock (&o->lock);
    g_byte_array_unref (kept);
    return GST_PAD_PROBE_DROP;
  }
  pos = start_code (map.data, map.size, 0, &header);
  valid = pos == 0 && map.size <= G_MAXUINT;
  while (pos < map.size && valid) {
    gsize next_header, next = start_code (map.data, map.size, header, &next_header);
    if (next - header < 2) { valid = FALSE; break; }
    guint type = (map.data[header] >> 1) & 63;
    if (type == 62) {
      rpus++;
      rpu = map.data + header + 2;
      rpu_size = next - header - 2;
    }
    if (type != 62 || strcmp (o->mode, "oversize"))
      g_byte_array_append (kept, map.data + pos, next - pos);
    pos = next;
    header = next_header;
  }
  g_mutex_lock (&o->lock);
  if (!valid || rpus > 1 || (rpus && !same_rpu (in, rpu, rpu_size)))
    o->failures++;
  if (valid && rpus == 1 && same_rpu (in, rpu, rpu_size)) o->positives++;
  g_mutex_unlock (&o->lock);

  if (valid && rpus == 1 && (!strcmp (o->mode, "duplicate") ||
                            !strcmp (o->mode, "oversize"))) {
    static const guint8 prefix[] = {0, 0, 0, 1, 0x7c, 1};
    g_byte_array_append (kept, prefix, sizeof prefix);
    if (!strcmp (o->mode, "duplicate")) {
      g_byte_array_append (kept, rpu, rpu_size);
    } else {
      guint8 fill[1024]; memset (fill, 0x55, sizeof fill);
      gsize remaining = GST_VIDEO_DOVI_RPU_MAX_SIZE + 1;
      while (remaining) {
        guint amount = MIN (remaining, sizeof fill);
        g_byte_array_append (kept, fill, amount);
        remaining -= amount;
      }
    }
    GstBuffer *out = gst_buffer_new_allocate (NULL, kept->len, NULL);
    if (!out || gst_buffer_fill (out, 0, kept->data, kept->len) != kept->len ||
        !gst_buffer_copy_into (out, in, GST_BUFFER_COPY_METADATA, 0, -1)) {
      gst_clear_buffer (&out);
      g_mutex_lock (&o->lock); o->failures++; g_mutex_unlock (&o->lock);
    } else {
      /* Deliberately retain the original meta: the second parser must remove
       * stale ownership and re-derive eligibility from the modified AU. */
      g_mutex_lock (&o->lock);
      o->mutated++;
      o->failures += !same_rpu (out, rpu, rpu_size);
      if (GST_CLOCK_TIME_IS_VALID (GST_BUFFER_PTS (out))) {
        guint64 *pts = g_new (guint64, 1); *pts = GST_BUFFER_PTS (out);
        g_hash_table_replace (o->tagged_inputs, pts, GINT_TO_POINTER (1));
      } else o->failures++;
      g_mutex_unlock (&o->lock);
      GST_PAD_PROBE_INFO_DATA (info) = out;
      gst_buffer_unmap (in, &map);
      gst_buffer_unref (in);
      g_byte_array_unref (kept);
      return GST_PAD_PROBE_OK;
    }
  }
  gst_buffer_unmap (in, &map);
  g_byte_array_unref (kept);
  return GST_PAD_PROBE_OK;
}

static GstPadProbeReturn
check_parser (GstPad *pad, GstPadProbeInfo *info, gpointer data)
{
  struct observation *o = data;
  GstBuffer *buffer = GST_PAD_PROBE_INFO_BUFFER (info);
  gboolean valid_caps = TRUE;
  if (!strcmp (o->mode, "nal")) {
    GstCaps *caps = gst_pad_get_current_caps (pad);
    const gchar *alignment = caps ? gst_structure_get_string (
        gst_caps_get_structure (caps, 0), "alignment") : NULL;
    valid_caps = alignment && !strcmp (alignment, "nal");
    gst_clear_caps (&caps);
    GstMapInfo map;
    if (gst_buffer_map (buffer, &map, GST_MAP_READ)) {
      gsize header; start_code (map.data, map.size, 0, &header);
      if (map.size - header >= 2) {
        guint type = (map.data[header] >> 1) & 63;
        g_mutex_lock (&o->lock);
        o->rpu_nals += type == 62;
        o->pictures += type <= 31;
        g_mutex_unlock (&o->lock);
      } else valid_caps = FALSE;
      gst_buffer_unmap (buffer, &map);
    } else valid_caps = FALSE;
  }
  if (strcmp (o->mode, "nal")) {
    GstMapInfo map;
    gboolean picture = FALSE;
    if (gst_buffer_map (buffer, &map, GST_MAP_READ)) {
      gsize header, pos = start_code (map.data, map.size, 0, &header);
      while (pos < map.size) {
        gsize next_header, next = start_code (map.data, map.size, header, &next_header);
        if (next - header < 2) { valid_caps = FALSE; break; }
        picture |= ((map.data[header] >> 1) & 63) <= 31;
        pos = next; header = next_header;
      }
      gst_buffer_unmap (buffer, &map);
    } else valid_caps = FALSE;
    g_mutex_lock (&o->lock);
    guint64 pts = GST_BUFFER_PTS (buffer);
    if (picture && g_hash_table_remove (o->tagged_inputs, &pts)) o->matched++;
    o->pictures += picture;
    g_mutex_unlock (&o->lock);
  }
  g_mutex_lock (&o->lock);
  o->checked++;
  o->failures += !valid_caps || gst_buffer_get_video_dovi_rpu_meta (buffer) != NULL;
  g_mutex_unlock (&o->lock);
  return GST_PAD_PROBE_OK;
}

/* Fix the scale-only output contract before VPP receives the decoder CAPS
 * event. Preserve actual decoder format/color; never guess HDR attributes. */
static GstPadProbeReturn
constrain_scale (GstPad *pad, GstPadProbeInfo *info, gpointer data)
{
  struct observation *o = data;
  GstEvent *event = GST_PAD_PROBE_INFO_EVENT (info);
  (void) pad;
  if (GST_EVENT_TYPE (event) == GST_EVENT_CAPS) {
    GstCaps *input;
    GstVideoInfo vi;
    gst_event_parse_caps (event, &input);
    if (!gst_video_info_from_caps (&vi, input)) {
      g_mutex_lock (&o->lock); o->failures++; g_mutex_unlock (&o->lock);
      return GST_PAD_PROBE_OK;
    }
    gchar *color = gst_video_colorimetry_to_string (&vi.colorimetry);
    GstCaps *desired = gst_caps_new_simple ("video/x-raw",
        "width", G_TYPE_INT, 960, "height", G_TYPE_INT, 540,
        "format", G_TYPE_STRING, gst_video_format_to_string (GST_VIDEO_INFO_FORMAT (&vi)),
        "colorimetry", G_TYPE_STRING, color, NULL);
    const GValue *chroma = gst_structure_get_value (gst_caps_get_structure (input, 0), "chroma-site");
    if (chroma) gst_structure_set_value (gst_caps_get_structure (desired, 0), "chroma-site", chroma);
    GstCaps *previous = NULL;
    g_object_get (o->sizecaps, "caps", &previous, NULL);
    if (!previous || !gst_caps_is_equal (previous, desired))
      g_object_set (o->sizecaps, "caps", desired, NULL);
    g_print ("scale-input-caps=%" GST_PTR_FORMAT " scale-required-caps=%" GST_PTR_FORMAT "\n",
        (gpointer) input, (gpointer) desired);
    gst_clear_caps (&previous); gst_caps_unref (desired); g_free (color);
  }
  return GST_PAD_PROBE_OK;
}

static GstPadProbeReturn
check_decoded (GstPad *pad, GstPadProbeInfo *info, gpointer data)
{
  struct observation *o = data;
  GstBuffer *buffer = GST_PAD_PROBE_INFO_BUFFER (info);
  GstCaps *caps = gst_pad_get_current_caps (pad);
  GstVideoInfo vi;
  gboolean valid = caps && gst_video_info_from_caps (&vi, caps);
  gst_clear_caps (&caps);
  g_mutex_lock (&o->lock);
  if (valid) { o->decoded_info = vi; o->have_decoded_info = TRUE; }
  else o->failures++;
  if (gst_buffer_get_video_dovi_rpu_meta (buffer)) {
    o->decoded_rpu++;
    if (GST_CLOCK_TIME_IS_VALID (GST_BUFFER_PTS (buffer))) {
      guint64 *pts = g_new (guint64, 1); *pts = GST_BUFFER_PTS (buffer);
      g_hash_table_replace (o->tagged_inputs, pts, GINT_TO_POINTER (1));
    } else o->failures++;
  }
  g_mutex_unlock (&o->lock);
  return GST_PAD_PROBE_OK;
}

static GstPadProbeReturn
check_scaled (GstPad *pad, GstPadProbeInfo *info, gpointer data)
{
  struct observation *o = data;
  GstBuffer *buffer = GST_PAD_PROBE_INFO_BUFFER (info);
  GstCaps *caps = gst_pad_get_current_caps (pad);
  GstVideoInfo vi;
  gboolean valid = caps && gst_video_info_from_caps (&vi, caps);
  g_mutex_lock (&o->lock);
  if (!o->checked) g_print ("scale-output-caps=%" GST_PTR_FORMAT "\n", (gpointer) caps);
  gst_clear_caps (&caps);
  valid &= o->have_decoded_info;
  if (valid) {
    o->dimension_change = GST_VIDEO_INFO_WIDTH (&vi) == 960 &&
        GST_VIDEO_INFO_HEIGHT (&vi) == 540 &&
        (GST_VIDEO_INFO_WIDTH (&vi) != GST_VIDEO_INFO_WIDTH (&o->decoded_info) ||
         GST_VIDEO_INFO_HEIGHT (&vi) != GST_VIDEO_INFO_HEIGHT (&o->decoded_info));
    o->format_preserved = GST_VIDEO_INFO_FORMAT (&vi) ==
        GST_VIDEO_INFO_FORMAT (&o->decoded_info);
    o->color_preserved = gst_video_colorimetry_is_equal (&vi.colorimetry,
                                                       &o->decoded_info.colorimetry);
    valid = o->dimension_change && o->format_preserved && o->color_preserved;
  }
  guint64 pts = GST_BUFFER_PTS (buffer);
  if (g_hash_table_remove (o->tagged_inputs, &pts)) o->matched++;
  o->checked++;
  gboolean absent = gst_buffer_get_video_dovi_rpu_meta (buffer) == NULL;
  o->absent_meta += absent;
  o->failures += !valid;
  o->failures += !absent;
  g_mutex_unlock (&o->lock);
  return GST_PAD_PROBE_OK;
}

static int
regions (void)
{
  guint8 rpu[] = {0x19, 0x08, 0x09, 0x80};
  const guint8 expected[] = {0x19, 0x08, 0x09, 0x80};
  GstBuffer *source = gst_buffer_new_allocate (NULL, 64, NULL);
  if (!source || !gst_buffer_add_video_dovi_rpu_meta (source, rpu, sizeof rpu, 1920, 1080))
    return 2;
  GstBuffer *full = gst_buffer_copy (source);
  GstBuffer *head = gst_buffer_copy_region (source, GST_BUFFER_COPY_ALL, 0, 32);
  GstBuffer *middle = gst_buffer_copy_region (source, GST_BUFFER_COPY_ALL, 8, 32);
  memset (rpu, 0, sizeof rpu);
  gst_buffer_unref (source);
  gboolean owned = full && same_rpu (full, expected, sizeof expected);
  gboolean head_absent = head && !gst_buffer_get_video_dovi_rpu_meta (head);
  gboolean middle_absent = middle && !gst_buffer_get_video_dovi_rpu_meta (middle);
  gboolean pass = owned && head_absent && middle_absent;
  gst_clear_buffer (&full); gst_clear_buffer (&head); gst_clear_buffer (&middle);
  g_print ("%s mode=regions full-owned-copy=%d partial-origin-absent=%d partial-offset-absent=%d\n",
           pass ? "PASS" : "FAIL", owned, head_absent, middle_absent);
  return pass ? 0 : 1;
}

static void
add_probe (GstElement *pipeline, const gchar *name, GstPadProbeCallback callback,
           struct observation *o)
{
  GstElement *element = gst_bin_get_by_name (GST_BIN (pipeline), name);
  GstPad *pad = gst_element_get_static_pad (element, "src");
  gst_pad_add_probe (pad, GST_PAD_PROBE_TYPE_BUFFER, callback, o, NULL);
  gst_object_unref (pad); gst_object_unref (element);
}

int
main (int argc, char **argv)
{
  gst_init (&argc, &argv);
  if (argc == 2 && !strcmp (argv[1], "regions")) return regions ();
  if (argc != 3 || (strcmp (argv[1], "nal") && strcmp (argv[1], "duplicate") &&
      strcmp (argv[1], "oversize") && strcmp (argv[1], "va-size"))) return 2;
  struct observation o = {.mode = argv[1]};
  g_mutex_init (&o.lock);
  o.tagged_inputs = g_hash_table_new_full (g_int64_hash, g_int64_equal, g_free, NULL);
  gchar *file = g_strescape (argv[2], NULL);
  gchar *description = g_strdup_printf (
      "filesrc location=\"%s\" ! qtdemux ! h265parse ! "
      "video/x-h265,stream-format=byte-stream,alignment=au ! identity name=seed ! %s "
      "fakesink sync=false num-buffers=24", file,
      !strcmp (o.mode, "va-size") ?
        "vah265dec name=decoder ! vapostproc name=scaled ! capsfilter name=sizecaps caps=\"video/x-raw,width=960,height=540\" !" :
      !strcmp (o.mode, "nal") ?
        "h265parse name=check ! video/x-h265,stream-format=byte-stream,alignment=nal !" :
        "h265parse name=check ! video/x-h265,stream-format=byte-stream,alignment=au !");
  g_free (file);
  GError *error = NULL;
  GstElement *pipeline = gst_parse_launch (description, &error);
  g_free (description);
  if (!pipeline || error) {
    g_printerr ("pipeline unavailable: %s\n", error ? error->message : "unknown");
    g_clear_error (&error); gst_clear_object (&pipeline);
    g_hash_table_unref (o.tagged_inputs); g_mutex_clear (&o.lock);
    return 2;
  }
  add_probe (pipeline, "seed", seed_and_mutate, &o);
  if (!strcmp (o.mode, "va-size")) {
    o.sizecaps = gst_bin_get_by_name (GST_BIN (pipeline), "sizecaps");
    GstElement *decoder = gst_bin_get_by_name (GST_BIN (pipeline), "decoder");
    GstPad *decoder_src = gst_element_get_static_pad (decoder, "src");
    gst_pad_add_probe (decoder_src, GST_PAD_PROBE_TYPE_EVENT_DOWNSTREAM,
        constrain_scale, &o, NULL);
    gst_object_unref (decoder_src); gst_object_unref (decoder);
    add_probe (pipeline, "decoder", check_decoded, &o);
    add_probe (pipeline, "scaled", check_scaled, &o);
  } else add_probe (pipeline, "check", check_parser, &o);
  GstBus *bus = gst_element_get_bus (pipeline);
  gboolean eos = FALSE;
  if (gst_element_set_state (pipeline, GST_STATE_PLAYING) != GST_STATE_CHANGE_FAILURE) {
    GstMessage *message = gst_bus_timed_pop_filtered (bus, 60 * GST_SECOND,
        GST_MESSAGE_ERROR | GST_MESSAGE_EOS);
    if (message) {
      eos = GST_MESSAGE_TYPE (message) == GST_MESSAGE_EOS;
      if (!eos) {
        gchar *debug = NULL;
        gst_message_parse_error (message, &error, &debug);
        g_printerr ("pipeline error: %s (%s)\n", error->message, debug ? debug : "");
        g_clear_error (&error); g_free (debug);
      }
      gst_message_unref (message);
    }
  }
  gst_element_set_state (pipeline, GST_STATE_NULL);
  gboolean pass = eos && !o.failures && o.positives >= 3 && o.checked >= 3;
  if (!strcmp (o.mode, "nal")) pass &= o.rpu_nals >= 3 && o.pictures >= 3;
  else if (!strcmp (o.mode, "va-size"))
    pass &= o.decoded_rpu >= 3 && o.matched >= 3 && o.dimension_change && o.format_preserved && o.color_preserved && o.absent_meta == o.checked;
  else pass &= o.mutated >= 3 && o.matched >= 3 && o.pictures >= 3;
  g_print ("%s mode=%s positive=%u mutated=%u checked=%u rpu-nals=%u pictures=%u "
      "decoded-rpu=%u matched=%u dimension-change=%d format-preserved=%d color-preserved=%d absent-meta=%u failures=%u eos=%d\n",
      pass ? "PASS" : "FAIL", o.mode, o.positives, o.mutated, o.checked, o.rpu_nals,
      o.pictures, o.decoded_rpu, o.matched, o.dimension_change, o.format_preserved, o.color_preserved, o.absent_meta, o.failures, eos);
  gst_clear_object (&o.sizecaps);
  gst_object_unref (bus); gst_object_unref (pipeline);
  g_hash_table_unref (o.tagged_inputs); g_mutex_clear (&o.lock);
  return pass ? 0 : 1;
}
