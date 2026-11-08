/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "gstdovipicture.h"
#include <string.h>
#include <gst/pbutils/codec-utils.h>
/* Source is the exact dvcC/dvvC payload transported by the demuxer. No field
 * comes from pixel caps or an RPU profile guess. Reserved truncation is UNKNOWN. */
gboolean gst_dovi_caps_get_stream_config (const GstCaps *caps,
    AVDOVIDecoderConfigurationRecord *record, GBytes **bytes_out)
{
  guint8 data[24];
  memset (record, 0, sizeof (*record));
  *bytes_out = NULL;
  if (!caps || gst_caps_get_size (caps) != 1) return FALSE;
  const GValue *value = gst_structure_get_value (gst_caps_get_structure (caps, 0),
      "dovi-configuration");
  if (!value || !GST_VALUE_HOLDS_BUFFER (value)) return FALSE;
  GstBuffer *buffer = gst_value_get_buffer (value);
  gsize size = gst_buffer_get_size (buffer);
  if (size < 4 || size > sizeof (data) || gst_buffer_extract (buffer, 0, data, size) != size ||
      data[0] != 1 || data[1] != 0) return FALSE;
  GstH265DoviConfiguration parsed;
  if (!gst_codec_utils_h265_parse_dovi_configuration (data, size, &parsed))
    return FALSE;
  *bytes_out = g_bytes_new (data, size);
  if (size != sizeof (data) || !parsed.compatibility_known) return FALSE;
  record->dv_version_major = parsed.version_major;
  record->dv_version_minor = parsed.version_minor;
  record->dv_profile = parsed.profile; record->dv_level = parsed.level;
  record->rpu_present_flag = parsed.rpu_present;
  record->el_present_flag = parsed.el_present;
  record->bl_present_flag = parsed.bl_present;
  record->dv_bl_signal_compatibility_id = parsed.compatibility_id;
  record->dv_md_compression = parsed.compression;
  return TRUE;
}
void gst_dovi_caps_apply_stream_config (GstCaps *caps, GBytes *bytes)
{
  g_return_if_fail (gst_caps_is_writable (caps));
  for (guint i = 0; i < gst_caps_get_size (caps); i++) {
    GstStructure *s = gst_caps_get_structure (caps, i);
    gst_structure_remove_field (s, "dovi-configuration");
    if (bytes) {
      gsize size; const guint8 *data = g_bytes_get_data (bytes, &size);
      GstBuffer *buffer = gst_buffer_new_allocate (NULL, size, NULL);
      if (buffer) {
        gst_buffer_fill (buffer, 0, data, size);
        gst_structure_set (s, "dovi-configuration", GST_TYPE_BUFFER, buffer, NULL);
        gst_buffer_unref (buffer);
      }
    }
  }
}
