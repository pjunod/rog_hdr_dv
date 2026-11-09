/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GST_GTK_DOVI_STREAM_H
#define GST_GTK_DOVI_STREAM_H
#include "gstdovipicture.h"
/* Exact decoder-transmitted box bytes, qualified by the shared public bridge.
 * This selects rendering for a stream; it never promises per-buffer metadata. */
static inline guint gtk_dovi_stream_profile (const GstStructure *st)
{
  GstCaps *caps = gst_caps_new_empty ();
  gst_caps_append_structure (caps, gst_structure_copy (st));
  AVDOVIDecoderConfigurationRecord config;
  GBytes *bytes = NULL;
  gboolean known = gst_dovi_caps_get_stream_config (caps, &config, &bytes);
  gst_caps_unref (caps);
  g_clear_pointer (&bytes, g_bytes_unref);
  if (!known || config.dv_version_major != 1 || config.dv_version_minor != 0 ||
      !config.rpu_present_flag || !config.bl_present_flag ||
      config.dv_md_compression != AV_DOVI_COMPRESSION_NONE) return 0;
  if (config.el_present_flag) {
    gboolean producer = FALSE;
    return config.dv_profile == 7 && config.dv_bl_signal_compatibility_id == 6 &&
        gst_structure_get_boolean (st, "dovi-fel-decoder", &producer) && producer ? 7 : 0;
  }
  if (config.dv_profile == 5 && config.dv_bl_signal_compatibility_id == 0) return 5;
  if (config.dv_profile == 8 && config.dv_bl_signal_compatibility_id == 1) return 8;
  return 0;
}
#endif
