/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GST_GTK_DOVI_MAPPER_H
#define GST_GTK_DOVI_MAPPER_H
#include <gst/video/video.h>
#define GST_GTK_DOVI_CORE_ABI 1
#define GST_GTK_DOVI_DESTINATION_ABI 1
#define GST_GTK_DOVI_SOURCE_LEASE_ABI 2
#define GST_GTK_DOVI_API __attribute__((visibility("default")))
extern GST_GTK_DOVI_API GstDebugCategory *gtk_dovi_map_debug;
#define GST_CAT_DEFAULT gtk_dovi_map_debug
typedef struct GstGtkDoviMapper GstGtkDoviMapper;
typedef enum {
  GST_GTK_DOVI_DESTINATION_DISPLAY_PQ = 0,
  GST_GTK_DOVI_DESTINATION_STANDARD_SDR_SRGB = 1,
} GstGtkDoviDestinationKind;
/* Caller serializes mapper on the streaming thread. Target is a copied GDK
 * snapshot, never a GdkSurface dereferenced from the streaming thread. */
typedef struct {
  guint64 generation;
  double primaries[8], min_nits, max_nits, reference_nits;
  double encoding_reference_nits, encoding_max_nits;
  gboolean valid, composed, render_ready;
} GstGtkDoviTarget;
GST_GTK_DOVI_API GstGtkDoviMapper *gst_gtk_dovi_mapper_new (void);
GST_GTK_DOVI_API void gst_gtk_dovi_mapper_free (GstGtkDoviMapper *self);
/* Known-DV stream only: output_info is the negotiated output format/encoding.
 * 1 privately mapped, 2 baseline re-encoded to the negotiated PQ output, -1
 * failure. No metadata/unsupported frame means ordinary input color conversion,
 * never a reused previous RPU. Non-DV streams bypass this function entirely. */
GST_GTK_DOVI_API int gst_gtk_dovi_mapper_render (GstGtkDoviMapper *self, GstBuffer *input,
    const GstVideoInfo *info, const GstGtkDoviTarget *target,
    GstBuffer **output, GstVideoInfo *output_info, GError **error);
/* Additive destination API. DISPLAY_PQ requires the actual per-view native
 * render witness. STANDARD_SDR_SRGB grades once to logical100nit BT709 and
 * emits full-range RGBA/sRGB without claiming a native HDR surface. */
GST_GTK_DOVI_API int gst_gtk_dovi_mapper_render_destination (
    GstGtkDoviMapper *self, GstBuffer *input, const GstVideoInfo *info,
    GstGtkDoviDestinationKind kind, const GstGtkDoviTarget *physical,
    GstBuffer **output, GstVideoInfo *output_info, GError **error);
typedef struct GstGtkDoviNativeFrame GstGtkDoviNativeFrame;
typedef struct GstGtkDoviSourceLease GstGtkDoviSourceLease;
/* The browser supplies original demuxer caps, before any decryption, and the
 * exact selected stream identity. This validates coded configuration only;
 * per-picture metadata and decoded FEL participation remain independent. */
GST_GTK_DOVI_API GstGtkDoviSourceLease *gst_gtk_dovi_source_lease_new (
    const GstCaps *clear_coded_caps, const gchar *stream_id, guint64 revision);
GST_GTK_DOVI_API GstGtkDoviSourceLease *gst_gtk_dovi_source_lease_ref (GstGtkDoviSourceLease *lease);
GST_GTK_DOVI_API void gst_gtk_dovi_source_lease_unref (GstGtkDoviSourceLease *lease);
GST_GTK_DOVI_API void gst_gtk_dovi_source_lease_revoke (GstGtkDoviSourceLease *lease);
GST_GTK_DOVI_API gboolean gst_gtk_dovi_source_lease_is_valid (const GstGtkDoviSourceLease *lease);
GST_GTK_DOVI_API gboolean gst_gtk_dovi_source_lease_matches (
    const GstGtkDoviSourceLease *lease, const gchar *stream_id, const GstCaps *caps);
GST_GTK_DOVI_API guint64 gst_gtk_dovi_native_frame_source_revision (GstGtkDoviNativeFrame *frame);
GST_GTK_DOVI_API guint64 gst_gtk_dovi_native_frame_source_selection (GstGtkDoviNativeFrame *frame);
GST_GTK_DOVI_API gboolean gst_gtk_dovi_native_frame_attach_source (
    GstBuffer *output, GstBuffer *input, const GstVideoInfo *input_info,
    const GstVideoInfo *output_info, guint64 generation, GstGtkDoviSourceLease *lease);

/* Render the retained original picture into the selected destination layout.
 * Successful output retains authoritative original epoch/picture identity.
 * A prior SDR attachment does not constrain a later native PQ regrade. */
GST_GTK_DOVI_API int gst_gtk_dovi_native_frame_render_destination (
    GstGtkDoviNativeFrame *frame, GstGtkDoviMapper *mapper,
    GstGtkDoviDestinationKind kind, const GstContext *context,
    GstBuffer **output, GstVideoInfo *output_info, guint64 *epoch,
    guint64 *picture_id, GError **error);
GST_GTK_DOVI_API void gst_gtk_dovi_debug_init (void);
GST_GTK_DOVI_API guint gst_gtk_dovi_core_abi (void);
GST_GTK_DOVI_API gboolean gst_gtk_dovi_target_from_context (const GstContext *context, GstGtkDoviTarget *target);
/* Full-picture owned source, retained by the visible sink frame. Never a
 * process-global most-recent RPU and never borrowed decoder storage. */
GST_GTK_DOVI_API GstGtkDoviNativeFrame *gst_gtk_dovi_native_frame_from_buffer (GstBuffer *buffer, guint64 *generation);
GST_GTK_DOVI_API GstGtkDoviNativeFrame *gst_gtk_dovi_native_frame_ref (GstGtkDoviNativeFrame *frame);
GST_GTK_DOVI_API void gst_gtk_dovi_native_frame_unref (GstGtkDoviNativeFrame *frame);
GST_GTK_DOVI_API gboolean gst_gtk_dovi_native_frame_attach (GstBuffer *output, GstBuffer *input,
    const GstVideoInfo *input_info, const GstVideoInfo *output_info, guint64 generation);
GST_GTK_DOVI_API int gst_gtk_dovi_native_frame_render (GstGtkDoviNativeFrame *frame,
    GstGtkDoviMapper *mapper, const GstContext *context, GstBuffer **output,
    GstVideoInfo *output_info, GError **error);
#endif
