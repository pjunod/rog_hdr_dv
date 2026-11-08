/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GST_DOVI_PICTURE_H
#define GST_DOVI_PICTURE_H
#include <gst/gst.h>
#include <gst/video/gstvideodecoder.h>
#include <libavutil/dovi_meta.h>
#include <libavutil/frame.h>
G_BEGIN_DECLS
/* Local in-process bridge ABI. Not a wire format: libavutil60, exact distro
 * headers/runtime and the public libavcodec resolver extension are required. The pointer remains owned by
 * its immutable picture. No AVFrame or parser allocation is borrowed. */
#define GST_DOVI_BRIDGE_ABI 2
#define GST_DOVI_MAX_RPU_SIZE 65536
#define GST_DOVI_API __attribute__((visibility("default")))
typedef struct _GstDoviPicture GstDoviPicture;
typedef struct _GstDoviResolver GstDoviResolver;
/* Exact SPS source geometry in luma pixels, before codec conformance cropping.
 * width/height describe the complete active image, never a downstream crop. */
typedef struct {
  guint coded_width, coded_height;
  guint x, y, width, height;
} GstDoviGeometry;
typedef enum {
  GST_DOVI_ENHANCEMENT_NOT_REQUIRED,
  GST_DOVI_ENHANCEMENT_UNRECONSTRUCTED,
  /* Reserved for a future renderer with verified residual participation.
   * Neither current decoder constructor can produce this state. */
  GST_DOVI_ENHANCEMENT_VERIFIED
} GstDoviEnhancement;
GST_DOVI_API GQuark gst_dovi_error_quark (void);
/* Requires the public strict HEVC decoder provenance on matched raw side data.
 * Default AVFrame Dolby metadata cannot establish reference/CRC validity.
 * original_rpu may be NULL to copy this AVFrame's matched raw side data.
 * Decoders must disable publication for lowres, cropping or transformed output. */
GST_DOVI_API GstDoviPicture *gst_dovi_picture_from_avframe (const AVFrame *frame,
    GBytes *original_rpu, guint64 epoch, guint64 picture_id, GError **error);
/* Complete qualification requires24bytes; valid abbreviated4..23-byte records
 * are retained in bytes_out for transport but returnFALSE/UNKNOWN. */
GST_DOVI_API gboolean gst_dovi_caps_get_stream_config (const GstCaps *caps,
    AVDOVIDecoderConfigurationRecord *record, GBytes **bytes_out);
GST_DOVI_API void gst_dovi_caps_apply_stream_config (GstCaps *caps, GBytes *bytes);
GST_DOVI_API GstDoviPicture *gst_dovi_picture_from_avframe_with_config (const AVFrame *frame,
    GBytes *original_rpu, const AVDOVIDecoderConfigurationRecord *config,
    guint64 epoch, guint64 picture_id, GError **error);
GST_DOVI_API GstDoviPicture *gst_dovi_picture_ref (GstDoviPicture *picture);
GST_DOVI_API void gst_dovi_picture_unref (GstDoviPicture *picture);
/* Both getters return read-only borrowed data, valid while picture is owned. */
GST_DOVI_API const AVDOVIMetadata *gst_dovi_picture_get_metadata (const GstDoviPicture *picture);
GST_DOVI_API GBytes *gst_dovi_picture_get_rpu (const GstDoviPicture *picture);
GST_DOVI_API guint gst_dovi_picture_get_profile (const GstDoviPicture *picture);
/* NULL means container configuration/compatibility is UNKNOWN. The profile
 * getter is then an RPU-header guess only, never a compatibility assertion. */
GST_DOVI_API const AVDOVIDecoderConfigurationRecord *gst_dovi_picture_get_stream_config (
    const GstDoviPicture *picture);
GST_DOVI_API GstDoviEnhancement gst_dovi_picture_get_enhancement (const GstDoviPicture *picture);
GST_DOVI_API void gst_dovi_picture_get_identity (const GstDoviPicture *picture,
    guint64 *epoch, guint64 *picture_id);
GST_DOVI_API const GstDoviGeometry *gst_dovi_picture_get_geometry (const GstDoviPicture *picture);
GST_DOVI_API void gst_dovi_picture_get_dimensions (const GstDoviPicture *picture,
    guint *width, guint *height);
GST_DOVI_API GstDoviPicture *gst_dovi_resolver_resolve_geometry (GstDoviResolver *resolver,
    GBytes *original_rpu, const GstDoviGeometry *geometry, guint64 picture_id, GError **error);
/* Decoder-owned, serialized in decode order. Reset at flush, stream changes and
 * after a rejected RPU, so no uncertain predecessor can make a later snapshot. */
GST_DOVI_API GstDoviResolver *gst_dovi_resolver_new (void);
GST_DOVI_API void gst_dovi_resolver_free (GstDoviResolver *resolver);
GST_DOVI_API void gst_dovi_resolver_reset (GstDoviResolver *resolver);
/* Stream boundary: copies a public decoder record, or NULL/zero for UNKNOWN.
 * Caller must supply authoritative container facts; never derive compatibility
 * from hvcC, YUV caps or an RPU profile guess. An invalid record clears state. */
GST_DOVI_API gboolean gst_dovi_resolver_configure (GstDoviResolver *resolver,
    const AVDOVIDecoderConfigurationRecord *config, gsize size, GError **error);
GST_DOVI_API GstDoviPicture *gst_dovi_resolver_resolve (GstDoviResolver *resolver,
    GBytes *original_rpu, guint width, guint height, guint64 picture_id, GError **error);
/* Return 1 and copied original RPU for exactly one layer-0 RPU in one AU;
 * 0 means a real metadata gap; -1 means malformed/ambiguous/unsupported input.
 * AU size is locally bounded to64MiB. hvc1/hev1 use the input hvcC length size.
 * Callers must reset resolver state on -1, never equate it with a gap. */
GST_DOVI_API int gst_dovi_extract_hevc_rpu (GstBuffer *buffer,
    const GstVideoCodecState *state, GBytes **rpu, GError **error);
typedef struct {
  GstMeta meta;
  GstDoviPicture *picture;
} GstDoviPictureMeta;
GST_DOVI_API GType gst_dovi_picture_meta_api_get_type (void);
GST_DOVI_API const GstMetaInfo *gst_dovi_picture_meta_get_info (void);
#define GST_DOVI_PICTURE_META_API_TYPE (gst_dovi_picture_meta_api_get_type ())
#define GST_DOVI_PICTURE_META_INFO (gst_dovi_picture_meta_get_info ())
#define gst_buffer_get_dovi_picture_meta(b) ((GstDoviPictureMeta *) gst_buffer_get_meta ((b), GST_DOVI_PICTURE_META_API_TYPE))
GST_DOVI_API GstDoviPictureMeta *gst_buffer_add_dovi_picture_meta (GstBuffer *buffer,
    GstDoviPicture *picture);
G_END_DECLS
#endif
