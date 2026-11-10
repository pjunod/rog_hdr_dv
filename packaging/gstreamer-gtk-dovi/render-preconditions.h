/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GST_GTK_DOVI_RENDER_PRECONDITIONS_H
#define GST_GTK_DOVI_RENDER_PRECONDITIONS_H
#include "mapper.h"
#include <libavutil/dovi_meta.h>
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
#endif
