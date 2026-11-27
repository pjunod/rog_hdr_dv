/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GST_GTK_DOVI_PLACEBO_LOG_H
#define GST_GTK_DOVI_PLACEBO_LOG_H
#include <gst/gst.h>
#include <libplacebo/log.h>
/* Forward libplacebo and provider messages to a GStreamer debug category.
 * pl_log is thread-safe and may call the callback from any thread; GStreamer
 * logging is itself thread-safe, so the callback keeps no state of its own. */
static inline GstDebugLevel gtk_dovi_placebo_gst_level (enum pl_log_level level)
{
  switch (level) {
    case PL_LOG_FATAL: case PL_LOG_ERR: return GST_LEVEL_ERROR;
    case PL_LOG_WARN: return GST_LEVEL_WARNING;
    case PL_LOG_INFO: return GST_LEVEL_INFO;
    case PL_LOG_DEBUG: return GST_LEVEL_DEBUG;
    case PL_LOG_TRACE: return GST_LEVEL_LOG;
    case PL_LOG_NONE: default: return GST_LEVEL_NONE;
  }
}
/* The most verbose libplacebo level that the category would print, so that
 * libplacebo does not format messages GStreamer discards. */
static inline enum pl_log_level gtk_dovi_placebo_log_level (GstDebugLevel threshold)
{
  if (threshold >= GST_LEVEL_LOG) return PL_LOG_TRACE;
  if (threshold >= GST_LEVEL_DEBUG) return PL_LOG_DEBUG;
  if (threshold >= GST_LEVEL_INFO) return PL_LOG_INFO;
  if (threshold >= GST_LEVEL_WARNING) return PL_LOG_WARN;
  if (threshold >= GST_LEVEL_ERROR) return PL_LOG_ERR;
  return PL_LOG_NONE;
}
static inline void gtk_dovi_placebo_log_cb (void *priv, enum pl_log_level level, const char *msg)
{
  GstDebugCategory *category = priv;
  GstDebugLevel gst_level = gtk_dovi_placebo_gst_level (level);
  if (gst_level != GST_LEVEL_NONE)
    GST_CAT_LEVEL_LOG (category, gst_level, NULL, "libplacebo: %s", msg);
}
static inline pl_log gtk_dovi_placebo_log_create (GstDebugCategory *category)
{
  return pl_log_create (PL_API_VER, pl_log_params (.log_cb = gtk_dovi_placebo_log_cb,
      .log_priv = category,
      .log_level = gtk_dovi_placebo_log_level (gst_debug_category_get_threshold (category))));
}
/* Follow a threshold changed after creation, e.g. by gst_debug_set_threshold_*. */
static inline void gtk_dovi_placebo_log_refresh (pl_log placebo, GstDebugCategory *category)
{
  pl_log_level_update (placebo, gtk_dovi_placebo_log_level (gst_debug_category_get_threshold (category)));
}
#endif
