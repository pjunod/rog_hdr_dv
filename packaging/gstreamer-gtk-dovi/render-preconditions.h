/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GST_GTK_DOVI_RENDER_PRECONDITIONS_H
#define GST_GTK_DOVI_RENDER_PRECONDITIONS_H
#include "mapper.h"
#include "stream.h"
#include "gstdovipicture.h"
/* GStreamer views of the mapping core's rules. Called with the decoder-owned
 * complete configuration, never an RPU profile guess. Profile 5 IPT base
 * samples have no ordinary HDR10 interpretation. */
static inline gboolean gtk_dovi_profile5_has_no_base_fallback (
    const AVDOVIDecoderConfigurationRecord *config)
{
  if (!config) return FALSE;
  struct rog_dovi_stream_config core = gtk_dovi_core_config (config);
  return rog_dovi_map_profile5_has_no_base_fallback (&core);
}
static inline gboolean gtk_dovi_profile5_destination_supported (
    const AVDOVIDecoderConfigurationRecord *config, gboolean sdr,
    const GstGtkDoviTarget *physical)
{
  struct rog_dovi_stream_config core;
  if (config) core = gtk_dovi_core_config (config);
  struct rog_dovi_target target = {.struct_size = sizeof (target)};
  if (physical)
    target.flags = (physical->valid ? ROG_DOVI_TARGET_VALID : 0) |
        (physical->render_ready ? ROG_DOVI_TARGET_RENDER_READY : 0) |
        (physical->composed ? ROG_DOVI_TARGET_COMPOSED : 0);
  return rog_dovi_map_profile5_destination_supported (config ? &core : NULL,
      sdr ? ROG_DOVI_DESTINATION_STANDARD_SDR_SRGB : ROG_DOVI_DESTINATION_DISPLAY_PQ,
      physical ? &target : NULL);
}
/* Compare every public parsed field; never compare struct padding or infer
 * compatibility from an RPU profile guess. */
static inline gboolean gtk_dovi_same_configuration (
    const AVDOVIDecoderConfigurationRecord *a, const AVDOVIDecoderConfigurationRecord *b)
{
  if (!a || !b) return FALSE;
  struct rog_dovi_stream_config ca = gtk_dovi_core_config (a), cb = gtk_dovi_core_config (b);
  return rog_dovi_map_same_config (&ca, &cb);
}
static inline gboolean gtk_dovi_profile5_picture_proved (
    const AVDOVIDecoderConfigurationRecord *required, GstBuffer *input)
{
  if (!gtk_dovi_profile5_has_no_base_fallback (required)) return TRUE;
  GstDoviPictureMeta *meta = gst_buffer_get_dovi_picture_meta (input);
  if (!meta || !meta->picture || !gst_dovi_picture_get_metadata (meta->picture)) return FALSE;
  GBytes *rpu = gst_dovi_picture_get_rpu (meta->picture);
  return rpu && g_bytes_get_size (rpu) && gtk_dovi_same_configuration (required,
      gst_dovi_picture_get_stream_config (meta->picture));
}
#endif
