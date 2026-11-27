/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* CPU log forwarding only: no Vulkan device, renderer, provider or media. */
#include <string.h>
#include <libplacebo/cache.h>
#include "placebo-log.h"
GST_DEBUG_CATEGORY_STATIC (probe_category);
static guint checks, failures;
static void require (gboolean ok, const gchar *name)
{ checks++; if (!ok) { failures++; g_printerr ("FAIL %s\n", name); } }
static GMutex seen_lock;
static guint seen;
static GstDebugLevel last_level;
static gchar *last_message;
static void capture (GstDebugCategory *category, GstDebugLevel level, const gchar *file,
    const gchar *function, gint line, GObject *object, GstDebugMessage *message, gpointer data)
{
  (void) file; (void) function; (void) line; (void) object; (void) data;
  if (category != probe_category) return;
  g_mutex_lock (&seen_lock);
  seen++;
  last_level = level;
  g_free (last_message);
  last_message = g_strdup (gst_debug_message_get (message));
  g_mutex_unlock (&seen_lock);
}
static void reset (void) { g_mutex_lock (&seen_lock); seen = 0; last_level = GST_LEVEL_NONE; g_clear_pointer (&last_message, g_free); g_mutex_unlock (&seen_lock); }
static gpointer emit_warnings (gpointer data)
{
  pl_log placebo = data;
  for (guint i = 0; i < 100; i++) placebo->params.log_cb (placebo->params.log_priv, PL_LOG_WARN, "threaded");
  return NULL;
}
int main (int argc, char **argv)
{
  gst_init (&argc, &argv);
  GST_DEBUG_CATEGORY_INIT (probe_category, "gtkdoviplacebolog", 0, "placebo log probe");
  /* Call the functions, not gstinfo.h's macros, which compare function and
   * object pointers and so fail -Wpedantic. */
  (gst_debug_remove_log_function) (gst_debug_log_default);
  (gst_debug_add_log_function) (capture, NULL, NULL);
  const struct { enum pl_log_level pl; GstDebugLevel gst; } table[] = {
    {PL_LOG_FATAL, GST_LEVEL_ERROR}, {PL_LOG_ERR, GST_LEVEL_ERROR}, {PL_LOG_WARN, GST_LEVEL_WARNING},
    {PL_LOG_INFO, GST_LEVEL_INFO}, {PL_LOG_DEBUG, GST_LEVEL_DEBUG}, {PL_LOG_TRACE, GST_LEVEL_LOG},
    {PL_LOG_NONE, GST_LEVEL_NONE},
  };
  for (guint i = 0; i < G_N_ELEMENTS (table); i++)
    require (gtk_dovi_placebo_gst_level (table[i].pl) == table[i].gst, "libplacebo level maps to its GStreamer level");
  require (gtk_dovi_placebo_log_level (GST_LEVEL_NONE) == PL_LOG_NONE, "silent category requests no libplacebo messages");
  require (gtk_dovi_placebo_log_level (GST_LEVEL_ERROR) == PL_LOG_ERR, "ERROR threshold requests errors");
  require (gtk_dovi_placebo_log_level (GST_LEVEL_WARNING) == PL_LOG_WARN, "WARNING threshold requests warnings");
  require (gtk_dovi_placebo_log_level (GST_LEVEL_FIXME) == PL_LOG_WARN, "FIXME threshold requests warnings");
  require (gtk_dovi_placebo_log_level (GST_LEVEL_INFO) == PL_LOG_INFO, "INFO threshold requests info");
  require (gtk_dovi_placebo_log_level (GST_LEVEL_DEBUG) == PL_LOG_DEBUG, "DEBUG threshold requests debug");
  require (gtk_dovi_placebo_log_level (GST_LEVEL_LOG) == PL_LOG_TRACE, "LOG threshold requests trace");
  require (gtk_dovi_placebo_log_level (GST_LEVEL_TRACE) == PL_LOG_TRACE, "TRACE threshold requests trace");

  gst_debug_category_set_threshold (probe_category, GST_LEVEL_WARNING);
  pl_log placebo = gtk_dovi_placebo_log_create (probe_category);
  require (placebo && placebo->params.log_level == PL_LOG_WARN, "log level follows the category threshold at creation");
  gst_debug_category_set_threshold (probe_category, GST_LEVEL_LOG);
  gtk_dovi_placebo_log_refresh (placebo, probe_category);
  require (placebo->params.log_level == PL_LOG_TRACE, "refresh follows a raised threshold");

  /* A real libplacebo message, without a GPU: loading a malformed cache. */
  reset ();
  pl_cache cache = pl_cache_create (pl_cache_params (.log = placebo, .max_total_size = 1 << 20));
  static const uint8_t garbage[64] = {'n', 'o', 't', 'a', 'c', 'a', 'c', 'h', 'e'};
  int loaded = pl_cache_load (cache, garbage, sizeof garbage);
  require (cache && loaded < 0, "malformed cache is rejected");
  g_mutex_lock (&seen_lock);
  require (seen > 0, "libplacebo's own message reaches the GStreamer category");
  require (last_message && g_str_has_prefix (last_message, "libplacebo: "), "forwarded message is labelled");
  require (last_level == GST_LEVEL_ERROR || last_level == GST_LEVEL_WARNING,
      "cache rejection is forwarded at error or warning level");
  g_print ("cache rejection forwarded at %s: %s\n", gst_debug_level_get_name (last_level),
      last_message ? last_message : "(none)");
  g_mutex_unlock (&seen_lock);
  pl_cache_destroy (&cache);

  reset ();
  placebo->params.log_cb (placebo->params.log_priv, PL_LOG_TRACE, "trace message");
  require (seen == 1 && last_level == GST_LEVEL_LOG && !strcmp (last_message, "libplacebo: trace message"),
      "trace is forwarded as LOG with its text");
  gst_debug_category_set_threshold (probe_category, GST_LEVEL_ERROR);
  reset ();
  placebo->params.log_cb (placebo->params.log_priv, PL_LOG_WARN, "below threshold");
  require (seen == 0, "GStreamer threshold still filters forwarded messages");
  placebo->params.log_cb (placebo->params.log_priv, PL_LOG_NONE, "none");
  require (seen == 0, "PL_LOG_NONE is never forwarded");

  gst_debug_category_set_threshold (probe_category, GST_LEVEL_WARNING);
  reset ();
  GThread *threads[4];
  for (guint i = 0; i < G_N_ELEMENTS (threads); i++) threads[i] = g_thread_new ("emit", emit_warnings, (gpointer) placebo);
  for (guint i = 0; i < G_N_ELEMENTS (threads); i++) g_thread_join (threads[i]);
  require (seen == 400, "concurrent callers each reach the category");

  pl_log_destroy (&placebo);
  reset ();
  g_print ("RESULT checks=%u failures=%u\n", checks, failures);
  return failures ? 1 : 0;
}
