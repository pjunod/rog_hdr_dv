/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GST_GTK_DOVI_RENDER_PRECONDITIONS_H
#define GST_GTK_DOVI_RENDER_PRECONDITIONS_H
#include "mapper.h"
#include "gstdovipicture.h"
/* Called with the decoder-owned complete configuration, never an RPU profile
 * guess. Profile 5 IPT base samples have no ordinary HDR10 interpretation. */
static inline gboolean gtk_dovi_profile5_has_no_base_fallback (
    const AVDOVIDecoderConfigurationRecord *config)
{
  return config && config->dv_version_major == 1 && config->dv_version_minor == 0 &&
      config->dv_profile == 5 && config->dv_bl_signal_compatibility_id == 0 &&
      config->rpu_present_flag && config->bl_present_flag && !config->el_present_flag &&
      config->dv_md_compression == AV_DOVI_COMPRESSION_NONE;
}
static inline gboolean gtk_dovi_profile5_destination_supported (
    const AVDOVIDecoderConfigurationRecord *config, gboolean sdr,
    const GstGtkDoviTarget *physical)
{
  return !gtk_dovi_profile5_has_no_base_fallback (config) || sdr ||
      (physical && physical->valid && physical->render_ready && physical->composed);
}
/* Compare every public parsed field; never compare struct padding or infer
 * compatibility from an RPU profile guess. */
static inline gboolean gtk_dovi_same_configuration (
    const AVDOVIDecoderConfigurationRecord *a, const AVDOVIDecoderConfigurationRecord *b)
{
  return a && b && a->dv_version_major == b->dv_version_major &&
      a->dv_version_minor == b->dv_version_minor && a->dv_profile == b->dv_profile &&
      a->dv_level == b->dv_level && a->rpu_present_flag == b->rpu_present_flag &&
      a->el_present_flag == b->el_present_flag && a->bl_present_flag == b->bl_present_flag &&
      a->dv_bl_signal_compatibility_id == b->dv_bl_signal_compatibility_id &&
      a->dv_md_compression == b->dv_md_compression;
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
