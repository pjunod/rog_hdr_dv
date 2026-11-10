/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* CPU policy controls only: no renderer, decoder, GPU or media fixture. */
#include "gstdovipicture.h"
#include "render-preconditions.h"
static guint checks, failures;
static void require (gboolean ok, const gchar *name)
{ checks++; if (!ok) { failures++; g_printerr ("FAIL %s\n", name); } }
int main (int argc, char **argv)
{
  gst_init (&argc, &argv);
  guint8 record[24] = {1, 0, 10, 29, 0};
  GstBuffer *bytes = gst_buffer_new_memdup (record, sizeof record);
  GstCaps *caps = gst_caps_new_simple ("video/x-h265", "dovi-configuration", GST_TYPE_BUFFER, bytes, NULL);
  AVDOVIDecoderConfigurationRecord p5; GBytes *original = NULL;
  require (gst_dovi_caps_get_stream_config (caps, &p5, &original) && g_bytes_get_size (original) == 24,
      "complete original configuration establishes the Profile 5 policy input");
  require (gtk_dovi_profile5_has_no_base_fallback (&p5), "Profile 5 has no HDR10 base fallback");
  for (guint flags = 0; flags < 8; flags++) {
    GstGtkDoviTarget target = {.valid = !!(flags & 1), .render_ready = !!(flags & 2), .composed = !!(flags & 4)};
    require (gtk_dovi_profile5_destination_supported (&p5, FALSE, &target) == (flags == 7),
        "legacy Profile 5 DISPLAY requires every physical witness flag");
    require (gtk_dovi_profile5_destination_supported (&p5, TRUE, &target),
        "explicit logical SDR does not require a native HDR witness");
    require (gtk_dovi_profile5_destination_supported (NULL, FALSE, &target),
        "unmarked/H264 policy stays unchanged");
  }
  require (!gtk_dovi_profile5_destination_supported (&p5, FALSE, NULL), "missing physical target rejects legacy Profile 5 DISPLAY");
  require (gtk_dovi_profile5_destination_supported (&p5, TRUE, NULL), "explicit SDR accepts absent physical target");
  AVDOVIDecoderConfigurationRecord compatible = p5;
  compatible.dv_profile = 8; compatible.dv_bl_signal_compatibility_id = 1;
  require (!gtk_dovi_profile5_has_no_base_fallback (&compatible) && gtk_dovi_profile5_destination_supported (&compatible, FALSE, NULL),
      "Profile 8.1 safe base fallback remains unchanged");
  compatible.dv_profile = 7; compatible.dv_bl_signal_compatibility_id = 6; compatible.el_present_flag = 1;
  require (!gtk_dovi_profile5_has_no_base_fallback (&compatible) && gtk_dovi_profile5_destination_supported (&compatible, FALSE, NULL),
      "Profile 7 safe base fallback remains unchanged");
  compatible = p5; compatible.dv_version_major = 0;
  require (!gtk_dovi_profile5_has_no_base_fallback (&compatible), "broken configuration cannot become a Profile 5 assertion");
  g_bytes_unref (original); gst_caps_unref (caps); gst_buffer_unref (bytes);
  g_print ("RESULT checks=%u failures=%u\n", checks, failures);
  return failures ? 1 : 0;
}
