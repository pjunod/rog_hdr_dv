/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* CPU-only native-frame lease control. The rendering boundary is a stub; this
 * exercises source ownership/revocation, not pixel or GPU rendering. */
#include "mapper.h"
#include <string.h>
GstDebugCategory *gtk_dovi_map_debug;
static guint checks, failures, renders;
static GstGtkDoviSourceLease *revoke_in_render;
static void require (gboolean ok, const gchar *name)
{ checks++; if (!ok) { failures++; g_printerr ("FAIL %s\n", name); } }
int gst_gtk_dovi_mapper_render_destination (GstGtkDoviMapper *mapper,
    GstBuffer *input, const GstVideoInfo *info, GstGtkDoviDestinationKind kind,
    const GstGtkDoviTarget *target, GstBuffer **output, GstVideoInfo *out_info,
    GError **error)
{
  (void) mapper; (void) input; (void) info; (void) kind; (void) target;
  (void) error; renders++;
  *output = gst_buffer_new_allocate (NULL, GST_VIDEO_INFO_SIZE (out_info), NULL);
  if (revoke_in_render) gst_gtk_dovi_source_lease_revoke (revoke_in_render);
  return 2;
}
static GstCaps *coded (guint length)
{
  guint8 record[24] = {1, 0, 10, 29, 0};
  GstBuffer *buffer = gst_buffer_new_memdup (record, length);
  GstCaps *caps = gst_caps_new_simple ("video/x-h265", "dovi-configuration",
      GST_TYPE_BUFFER, buffer, NULL);
  gst_buffer_unref (buffer); return caps;
}
static GstGtkDoviNativeFrame *frame (GstGtkDoviSourceLease *lease)
{
  GstVideoInfo info; gst_video_info_set_format (&info, GST_VIDEO_FORMAT_RGBA, 4, 4);
  GstBuffer *input = gst_buffer_new_allocate (NULL, info.size, NULL);
  GstBuffer *output = gst_buffer_new_allocate (NULL, info.size, NULL);
  require (gst_gtk_dovi_native_frame_attach_source (output, input, &info, &info, 1, lease),
      "frame strongly retains source lease");
  GstGtkDoviNativeFrame *f = gst_gtk_dovi_native_frame_from_buffer (output, NULL);
  gst_buffer_unref (output); gst_buffer_unref (input); return f;
}
int main (int argc, char **argv)
{
  gst_init (&argc, &argv);
  GST_DEBUG_CATEGORY_INIT (gtk_dovi_map_debug, "lease-control", 0, "CPU lease control");
  GstCaps *caps = coded (24);
  GstGtkDoviSourceLease *lease = gst_gtk_dovi_source_lease_new (caps, "source/video0", 17);
  require (lease && gst_gtk_dovi_source_lease_is_valid (lease), "complete original coded configuration qualifies");
  require (gst_gtk_dovi_source_lease_matches (lease, "source/video0", caps), "exact original stream/configuration match");
  require (!gst_gtk_dovi_source_lease_matches (lease, "source/video1", caps), "different stream cannot borrow the lease");
  require (!gst_gtk_dovi_source_lease_matches (lease, "source/video0", NULL), "missing configuration cannot borrow the lease");
  require (!gst_gtk_dovi_source_lease_new (caps, "", 17), "missing stream identity is rejected");
  require (!gst_gtk_dovi_source_lease_new (caps, "source/video0", 0), "zero source revision is rejected");
  GstCaps *invalid = coded (23);
  require (!gst_gtk_dovi_source_lease_new (invalid, "source/video0", 17), "partial configuration is rejected");
  gst_caps_unref (invalid); invalid = gst_caps_copy (caps);
  gst_structure_set_name (gst_caps_get_structure (invalid, 0), "application/x-cenc");
  require (!gst_gtk_dovi_source_lease_new (invalid, "source/video0", 17), "protected input is rejected");
  gst_caps_unref (invalid);
  GstGtkDoviNativeFrame *f = frame (lease);
  require (gst_gtk_dovi_native_frame_source_revision (f) == 17, "revision belongs to retained frame");
  GstBuffer *output = NULL; GstVideoInfo info; guint64 epoch = 99, picture = 99;
  int result = gst_gtk_dovi_native_frame_render_destination (f, NULL,
      GST_GTK_DOVI_DESTINATION_STANDARD_SDR_SRGB, NULL, &output, &info,
      &epoch, &picture, NULL);
  require (result == 2 && output && renders == 1, "valid lease reaches rendering boundary");
  gst_clear_buffer (&output);
  gst_gtk_dovi_source_lease_revoke (lease);
  require (!gst_gtk_dovi_source_lease_is_valid (lease) &&
      !gst_gtk_dovi_native_frame_source_revision (f), "revocation is visible on retained frame");
  result = gst_gtk_dovi_native_frame_render_destination (f, NULL,
      GST_GTK_DOVI_DESTINATION_STANDARD_SDR_SRGB, NULL, &output, &info,
      &epoch, &picture, NULL);
  require (!result && !output && renders == 1 && !epoch && !picture,
      "pre-render revocation does not render or publish identity");
  gst_gtk_dovi_native_frame_unref (f); gst_gtk_dovi_source_lease_unref (lease);
  lease = gst_gtk_dovi_source_lease_new (caps, "source/video0", 18); f = frame (lease);
  revoke_in_render = lease;
  result = gst_gtk_dovi_native_frame_render_destination (f, NULL,
      GST_GTK_DOVI_DESTINATION_STANDARD_SDR_SRGB, NULL, &output, &info,
      &epoch, &picture, NULL);
  require (!result && !output && renders == 2 && !epoch && !picture,
      "revocation during rendering discards the produced buffer and identity");
  revoke_in_render = NULL;
  gst_gtk_dovi_native_frame_unref (f); gst_gtk_dovi_source_lease_unref (lease);
  f = frame (NULL);
  result = gst_gtk_dovi_native_frame_render_destination (f, NULL,
      GST_GTK_DOVI_DESTINATION_STANDARD_SDR_SRGB, NULL, &output, &info,
      &epoch, &picture, NULL);
  require (result == 2 && output && !gst_gtk_dovi_native_frame_source_revision (f),
      "legacy null-lease behavior remains available to existing callers");
  gst_clear_buffer (&output); gst_gtk_dovi_native_frame_unref (f); gst_caps_unref (caps);
  g_print ("RESULT checks=%u failures=%u\n", checks, failures); return failures ? 1 : 0;
}
