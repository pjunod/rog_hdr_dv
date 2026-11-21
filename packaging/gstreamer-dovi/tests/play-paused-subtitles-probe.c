/* Public GstPlay regression. All media and captions are authored here.
 * Usage: probe /owned/external/task/fixture.mkv
 * No display, application control, private media or compensating test seek.
 * This output regression configures accurate explicit seeks. Independence from
 * the caller's inaccurate-seek setting is source-reviewed, not claimed here.
 */
#include <gst/app/gstappsink.h>
#include <gst/app/gstappsrc.h>
#include <gst/play/play.h>
#include <gst/video/video.h>
#include <string.h>

typedef struct {
  guint64 serial;
  GstClockTime pts;
  guint bright, nonblack;
  gchar sha256[65];
} Frame;

typedef struct {
  GMutex lock;
  Frame frame;
  gboolean callback_error, api_error;
  GstPlayState state;
  guint seek_done;
  GstClockTime seek_done_position;
} Observation;

static GstFlowReturn
preroll (GstAppSink *sink, gpointer data)
{
  Observation *o = data;
  GstSample *sample = gst_app_sink_pull_preroll (sink);
  GstVideoInfo info;
  GstVideoFrame image;
  Frame next = { 0 };
  GChecksum *checksum;

  if (!sample)
    return GST_FLOW_FLUSHING;
  if (!gst_video_info_from_caps (&info, gst_sample_get_caps (sample)) ||
      GST_VIDEO_INFO_FORMAT (&info) != GST_VIDEO_FORMAT_RGB ||
      !gst_video_frame_map (&image, &info, gst_sample_get_buffer (sample),
          GST_MAP_READ)) {
    g_mutex_lock (&o->lock);
    o->callback_error = TRUE;
    g_mutex_unlock (&o->lock);
    gst_sample_unref (sample);
    return GST_FLOW_ERROR;
  }
  checksum = g_checksum_new (G_CHECKSUM_SHA256);
  next.pts = GST_BUFFER_PTS (gst_sample_get_buffer (sample));
  for (guint y = 0; y < (guint) GST_VIDEO_INFO_HEIGHT (&info); y++) {
    const guint8 *row = (const guint8 *) GST_VIDEO_FRAME_PLANE_DATA (&image, 0) +
        y * GST_VIDEO_FRAME_PLANE_STRIDE (&image, 0);
    g_checksum_update (checksum, row, GST_VIDEO_INFO_WIDTH (&info) * 3);
    for (guint x = 0; x < (guint) GST_VIDEO_INFO_WIDTH (&info); x++) {
      const guint8 *rgb = row + x * 3;
      next.bright += rgb[0] >= 200 && rgb[1] >= 200 && rgb[2] >= 200;
      next.nonblack += MAX (rgb[0], MAX (rgb[1], rgb[2])) > 4;
    }
  }
  g_strlcpy (next.sha256, g_checksum_get_string (checksum), sizeof next.sha256);
  g_checksum_free (checksum);
  gst_video_frame_unmap (&image);
  gst_sample_unref (sample);
  g_mutex_lock (&o->lock);
  next.serial = o->frame.serial + 1;
  o->frame = next;
  g_mutex_unlock (&o->lock);
  return GST_FLOW_OK;
}

static void
messages (GstBus *bus, Observation *o)
{
  GstMessage *message;
  while ((message = gst_bus_pop (bus))) {
    if (gst_play_is_play_message (message)) {
      GstPlayMessage type;
      gst_play_message_parse_type (message, &type);
      if (type == GST_PLAY_MESSAGE_ERROR)
        o->api_error = TRUE;
      else if (type == GST_PLAY_MESSAGE_STATE_CHANGED)
        gst_play_message_parse_state_changed (message, &o->state);
      else if (type == GST_PLAY_MESSAGE_SEEK_DONE) {
        o->seek_done++;
        gst_play_message_parse_seek_done (message, &o->seek_done_position);
      }
    }
    gst_message_unref (message);
  }
}

static gboolean
fresh_paused (GstPlay *play, GstElement *pipeline, GstBus *bus,
    Observation *o, guint64 after, GstClockTime position, Frame *result)
{
  gint64 deadline = g_get_monotonic_time () + 5 * G_TIME_SPAN_SECOND;
  do {
    GstState state, pending;
    gboolean bad;
    messages (bus, o);
    g_mutex_lock (&o->lock);
    *result = o->frame;
    bad = o->callback_error;
    g_mutex_unlock (&o->lock);
    if (o->api_error || bad)
      return FALSE;
    gst_element_get_state (pipeline, &state, &pending, 0);
    if (result->serial > after && state == GST_STATE_PAUSED &&
        pending == GST_STATE_VOID_PENDING && o->state == GST_PLAY_STATE_PAUSED &&
        (position == GST_CLOCK_TIME_NONE ||
            gst_play_get_position (play) == position))
      return TRUE;
    g_usleep (5000);
  } while (g_get_monotonic_time () < deadline);
  return FALSE;
}

static gboolean
seek_completed (GstBus *bus, Observation *o, guint previous,
    GstClockTime position)
{
  gint64 deadline = g_get_monotonic_time () + 5 * G_TIME_SPAN_SECOND;
  do {
    messages (bus, o);
    if (o->api_error)
      return FALSE;
    if (o->seek_done > previous && o->seek_done_position == position)
      return TRUE;
    g_usleep (5000);
  } while (g_get_monotonic_time () < deadline);
  return FALSE;
}

static gboolean
fixture (const gchar *path)
{
  GError *error = NULL;
  GstElement *pipeline, *file;
  GstBus *bus;
  GstMessage *done;
  const gchar *captions[] = { "AAAAAA AAAAAA", "MMMMMM MMMMMM" };
  gboolean ok = FALSE;

  pipeline = gst_parse_launch (
      "matroskamux name=mux ! filesink name=file "
      "videotestsrc pattern=black num-buffers=30 ! "
      "video/x-raw,width=640,height=360,framerate=5/1 ! "
      "vp8enc deadline=1 ! queue ! mux.video_0 "
      "appsrc name=text0 format=time caps=text/x-raw,format=utf8 ! "
      "queue ! mux.subtitle_0 "
      "appsrc name=text1 format=time caps=text/x-raw,format=utf8 ! "
      "queue ! mux.subtitle_1", &error);
  if (!pipeline || error) {
    g_clear_error (&error);
    if (pipeline)
      gst_object_unref (pipeline);
    return FALSE;
  }
  file = gst_bin_get_by_name (GST_BIN (pipeline), "file");
  g_object_set (file, "location", path, NULL);
  gst_object_unref (file);
  bus = gst_element_get_bus (pipeline);
  if (gst_element_set_state (pipeline, GST_STATE_PLAYING) ==
      GST_STATE_CHANGE_FAILURE)
    goto out;
  for (guint i = 0; i < G_N_ELEMENTS (captions); i++) {
    gchar *name = g_strdup_printf ("text%u", i);
    GstElement *source = gst_bin_get_by_name (GST_BIN (pipeline), name);
    GstBuffer *buffer = gst_buffer_new_allocate (NULL, strlen (captions[i]), NULL);
    g_free (name);
    gst_buffer_fill (buffer, 0, captions[i], strlen (captions[i]));
    GST_BUFFER_PTS (buffer) = 0;
    GST_BUFFER_DURATION (buffer) = 6 * GST_SECOND;
    if (gst_app_src_push_buffer (GST_APP_SRC (source), buffer) != GST_FLOW_OK ||
        gst_app_src_end_of_stream (GST_APP_SRC (source)) != GST_FLOW_OK) {
      gst_object_unref (source);
      goto out;
    }
    gst_object_unref (source);
  }
  done = gst_bus_timed_pop_filtered (bus, 10 * GST_SECOND,
      GST_MESSAGE_EOS | GST_MESSAGE_ERROR);
  ok = done && GST_MESSAGE_TYPE (done) == GST_MESSAGE_EOS;
  if (done)
    gst_message_unref (done);
out:
  gst_element_set_state (pipeline, GST_STATE_NULL);
  gst_object_unref (bus);
  gst_object_unref (pipeline);
  return ok;
}

#define REQUIRE(condition, label) G_STMT_START { \
  if (!(condition)) { g_printerr ("FAIL: %s\n", label); goto out; } \
} G_STMT_END

int
main (int argc, char **argv)
{
  GstPlay *play = NULL;
  GstElement *pipeline = NULL, *sink, *audio;
  GstBus *bus = NULL;
  GstCaps *caps;
  GstStructure *config;
  GstPlayMediaInfo *info = NULL;
  GstPlaySubtitleInfo *current = NULL;
  Observation o = { 0 };
  Frame initial, on, off, restored, other, original_track, moved;
  gchar *uri = NULL, *original_id = NULL, *other_id = NULL;
  gint result = 1;
  guint explicit_done;
  GList *subtitles;

  gst_init (&argc, &argv);
  g_mutex_init (&o.lock);
  REQUIRE (argc == 2 && g_path_is_absolute (argv[1]), "owned absolute fixture path");
  REQUIRE (!g_file_test (argv[1], G_FILE_TEST_EXISTS), "fresh fixture path");
  REQUIRE (fixture (argv[1]), "authored Matroska fixture");
  play = gst_play_new (NULL);
  pipeline = gst_play_get_pipeline (play);
  bus = gst_play_get_message_bus (play);
  sink = gst_element_factory_make ("appsink", NULL);
  audio = gst_element_factory_make ("fakesink", NULL);
  REQUIRE (sink && audio, "public sink factories");
  caps = gst_caps_from_string ("video/x-raw,format=RGB,width=640,height=360");
  g_object_set (sink, "caps", caps, "emit-signals", TRUE, "sync", TRUE, NULL);
  gst_caps_unref (caps);
  g_signal_connect (sink, "new-preroll", G_CALLBACK (preroll), &o);
  g_object_set (pipeline, "video-sink", sink, "audio-sink", audio, NULL);
  config = gst_play_get_config (play);
  gst_play_config_set_seek_accurate (config, TRUE);
  REQUIRE (gst_play_set_config (play, config), "accurate explicit seek config");
  uri = gst_filename_to_uri (argv[1], NULL);
  gst_play_set_uri (play, uri);
  gst_play_pause (play);
  REQUIRE (fresh_paused (play, pipeline, bus, &o, 0, GST_CLOCK_TIME_NONE,
          &initial), "initial normal preroll");
  info = gst_play_get_media_info (play);
  REQUIRE (info, "public media info");
  subtitles = gst_play_media_info_get_subtitle_streams (info);
  REQUIRE (g_list_length (subtitles) == 2, "two authored subtitle streams");
  current = gst_play_get_current_subtitle_track (play);
  REQUIRE (current, "actual selected baseline subtitle");
  original_id = g_strdup (gst_play_stream_info_get_stream_id (
          GST_PLAY_STREAM_INFO (current)));
  for (GList *item = subtitles; item; item = item->next) {
    const gchar *id = gst_play_stream_info_get_stream_id (item->data);
    if (strcmp (id, original_id))
      other_id = g_strdup (id);
  }
  REQUIRE (other_id, "other authored subtitle ID");
  messages (bus, &o);
  explicit_done = o.seek_done;
  gst_play_seek (play, GST_SECOND);
  REQUIRE (fresh_paused (play, pipeline, bus, &o, initial.serial, GST_SECOND,
          &on), "baseline explicit seek");
  REQUIRE (seek_completed (bus, &o, explicit_done, GST_SECOND),
      "explicit seek completion preserved");
  g_print ("{\"baseline_pts_ns\":%" G_GUINT64_FORMAT
      ",\"baseline_bright_pixels\":%u,\"baseline_nonblack_pixels\":%u}\n",
      on.pts, on.bright, on.nonblack);
  REQUIRE (on.pts == GST_SECOND && on.bright > 32, "positive authored caption");

  /* Wait for the matching public completion, then inspect its latest frame.
   * A selection can produce an earlier preroll before the automatic refresh.
   * No test seek, play, clock advance or injection follows these toggles. */
  messages (bus, &o);
  explicit_done = o.seek_done;
  gst_play_set_subtitle_track_enabled (play, FALSE);
  REQUIRE (seek_completed (bus, &o, explicit_done, GST_SECOND) &&
      fresh_paused (play, pipeline, bus, &o, on.serial, GST_SECOND,
          &off), "disabled caption fresh paused preroll");
  REQUIRE (off.pts == on.pts && off.nonblack == 0, "disabled caption black frame");
  messages (bus, &o);
  explicit_done = o.seek_done;
  gst_play_set_subtitle_track_enabled (play, TRUE);
  REQUIRE (seek_completed (bus, &o, explicit_done, GST_SECOND) &&
      fresh_paused (play, pipeline, bus, &o, off.serial, GST_SECOND,
          &restored), "restored caption fresh paused preroll");
  REQUIRE (restored.pts == on.pts && !strcmp (restored.sha256, on.sha256),
      "exact caption restoration");
  messages (bus, &o);
  explicit_done = o.seek_done;
  REQUIRE (gst_play_set_subtitle_track_id (play, other_id), "ordinary subtitle ID selection");
  REQUIRE (seek_completed (bus, &o, explicit_done, GST_SECOND) &&
      fresh_paused (play, pipeline, bus, &o, restored.serial, GST_SECOND,
          &other), "different track fresh paused preroll");
  {
    GstPlaySubtitleInfo *observed = gst_play_get_current_subtitle_track (play);
    gboolean expected_id = observed && !g_strcmp0 (
        gst_play_stream_info_get_stream_id (GST_PLAY_STREAM_INFO (observed)), other_id);
    g_print ("{\"other_pts_ns\":%" G_GUINT64_FORMAT
        ",\"other_bright_pixels\":%u,\"other_nonblack_pixels\":%u,"
        "\"same_as_baseline\":%s,\"selected_id_matches_requested\":%s}\n",
        other.pts, other.bright, other.nonblack,
        !strcmp (other.sha256, on.sha256) ? "true" : "false",
        expected_id ? "true" : "false");
    if (observed)
      gst_object_unref (observed);
  }
  REQUIRE (other.pts == on.pts && other.bright > 32 &&
      strcmp (other.sha256, on.sha256), "different authored caption visible");
  messages (bus, &o);
  explicit_done = o.seek_done;
  REQUIRE (gst_play_set_subtitle_track_id (play, original_id), "restore original track ID");
  REQUIRE (seek_completed (bus, &o, explicit_done, GST_SECOND) &&
      fresh_paused (play, pipeline, bus, &o, other.serial, GST_SECOND,
          &original_track), "original track fresh paused preroll");
  REQUIRE (!strcmp (original_track.sha256, on.sha256), "original track exact pixels");

  /* A newer explicit seek takes priority over automatic refresh intent. */
  messages (bus, &o);
  explicit_done = o.seek_done;
  gst_play_set_subtitle_track_enabled (play, FALSE);
  gst_play_seek (play, 2 * GST_SECOND);
  REQUIRE (fresh_paused (play, pipeline, bus, &o, original_track.serial,
          2 * GST_SECOND, &moved), "new explicit seek wins");
  REQUIRE (seek_completed (bus, &o, explicit_done, 2 * GST_SECOND),
      "new explicit seek completion");
  REQUIRE (moved.pts == 2 * GST_SECOND && moved.nonblack == 0,
      "new seek position and caption preserved");
  g_print ("{\"passed\":true,\"scope\":\"synthetic public GstPlay paused subtitle API\","
      "\"baseline_pts_ns\":%" G_GUINT64_FORMAT ",\"on_bright_pixels\":%u,"
      "\"off_nonblack_pixels\":%u,\"other_bright_pixels\":%u,"
      "\"new_explicit_seek_pts_ns\":%" G_GUINT64_FORMAT "}\n",
      on.pts, on.bright, off.nonblack, other.bright, moved.pts);
  result = 0;
out:
  if (play) {
    gst_play_stop (play);
    gst_object_unref (play);
  }
  if (pipeline)
    gst_object_unref (pipeline);
  if (bus)
    gst_object_unref (bus);
  if (info)
    gst_object_unref (info);
  if (current)
    gst_object_unref (current);
  g_free (uri);
  g_free (original_id);
  g_free (other_id);
  g_mutex_clear (&o.lock);
  return result;
}
