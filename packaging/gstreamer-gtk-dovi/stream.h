/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GST_GTK_DOVI_STREAM_H
#define GST_GTK_DOVI_STREAM_H
#include "gstdovipicture.h"
#include <rog-dovi-map.h>
/* The public fields of a parsed decoder record, for the mapping core. */
static inline struct rog_dovi_stream_config gtk_dovi_core_config (
    const AVDOVIDecoderConfigurationRecord *c)
{
  return (struct rog_dovi_stream_config) {
    .version_major = c->dv_version_major, .version_minor = c->dv_version_minor,
    .profile = c->dv_profile, .level = c->dv_level,
    .rpu_present = c->rpu_present_flag, .el_present = c->el_present_flag,
    .bl_present = c->bl_present_flag,
    .bl_signal_compatibility_id = c->dv_bl_signal_compatibility_id,
    .md_compression = c->dv_md_compression,
  };
}
/* Exact decoder-transmitted box bytes, qualified by the shared public bridge.
 * This selects rendering for a stream; it never promises per-buffer metadata.
 * The qualification rule is the mapping core's. */
static inline guint gtk_dovi_stream_profile (const GstStructure *st)
{
  GstCaps *caps = gst_caps_new_empty ();
  gst_caps_append_structure (caps, gst_structure_copy (st));
  AVDOVIDecoderConfigurationRecord config;
  GBytes *bytes = NULL;
  gboolean known = gst_dovi_caps_get_stream_config (caps, &config, &bytes);
  gst_caps_unref (caps);
  g_clear_pointer (&bytes, g_bytes_unref);
  if (!known) return 0;
  gboolean producer = FALSE;
  if (config.el_present_flag && !gst_structure_get_boolean (st, "dovi-fel-decoder", &producer))
    producer = FALSE;
  struct rog_dovi_stream_config core = gtk_dovi_core_config (&config);
  return rog_dovi_map_stream_profile (&core, producer);
}
#endif
