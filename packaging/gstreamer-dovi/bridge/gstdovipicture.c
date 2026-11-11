/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "gstdovipicture-private.h"
#include <libavutil/mem.h>
#include <libavcodec/dovi_parser.h>
#include <libavutil/version.h>
#include <libavutil/pixdesc.h>
#include <stdalign.h>
#include <string.h>

struct _GstDoviPicture {
  gint refs;
  AVDOVIMetadata *metadata;
  GBytes *rpu;
  GstDoviGeometry geometry;
  guint profile;
  guint64 epoch, id;
  gboolean config_known;
  AVDOVIDecoderConfigurationRecord config;
  GstDoviEnhancement enhancement;
};

GQuark
gst_dovi_error_quark (void)
{
  return g_quark_from_static_string ("gst-dovi-picture-error");
}

gboolean
gst_dovi_fail (GError **error, const gchar *message)
{
  g_set_error_literal (error, gst_dovi_error_quark (), 1, message);
  return FALSE;
}

static gboolean
range_valid (gsize offset, gsize length, gsize size, gsize alignment)
{
  return offset >= sizeof (AVDOVIMetadata) && offset % alignment == 0 &&
      offset <= size && length <= size - offset;
}

static gboolean
metadata_valid (const AVDOVIMetadata *m, gsize size)
{
  const AVDOVIRpuDataHeader *h;
  const AVDOVIDataMapping *mapping;
  gsize offsets[4], lengths[4];
  if (!m || size < sizeof (*m) ||
      !range_valid (m->header_offset, sizeof (*h), size, alignof (AVDOVIRpuDataHeader)) ||
      !range_valid (m->mapping_offset, sizeof (*mapping), size, alignof (AVDOVIDataMapping)) ||
      !range_valid (m->color_offset, sizeof (AVDOVIColorMetadata), size, alignof (AVDOVIColorMetadata)) ||
      m->num_ext_blocks < 0 || m->num_ext_blocks > AV_DOVI_MAX_EXT_BLOCKS)
    return FALSE;
  offsets[0] = m->header_offset; lengths[0] = sizeof (*h);
  offsets[1] = m->mapping_offset; lengths[1] = sizeof (*mapping);
  offsets[2] = m->color_offset; lengths[2] = sizeof (AVDOVIColorMetadata);
  offsets[3] = m->ext_block_offset; lengths[3] = 0;
  if (m->num_ext_blocks) {
    if (m->ext_block_size < sizeof (AVDOVIDmData) ||
        m->ext_block_size > G_MAXSIZE / (gsize) m->num_ext_blocks)
      return FALSE;
    lengths[3] = m->ext_block_size * m->num_ext_blocks;
    if (!range_valid (offsets[3], lengths[3], size, alignof (AVDOVIDmData)) ||
        m->ext_block_size % alignof (AVDOVIDmData))
      return FALSE;
  }
  for (guint i = 0; i < 4; i++)
    for (guint j = i + 1; j < 4; j++)
      if (lengths[i] && lengths[j] && offsets[i] < offsets[j] + lengths[j] &&
          offsets[j] < offsets[i] + lengths[i])
        return FALSE;
  h = av_dovi_get_header (m);
  if (h->rpu_type != 2 || h->coef_data_type > 1 || h->coef_log2_denom > 32 ||
      h->bl_bit_depth < 8 || h->bl_bit_depth > 16 ||
      h->el_bit_depth < 8 || h->el_bit_depth > 16 ||
      h->vdr_bit_depth < 8 || h->vdr_bit_depth > 16)
    return FALSE;
  mapping = av_dovi_get_mapping (m);
  for (guint c = 0; c < 3; c++) {
    const AVDOVIReshapingCurve *curve = &mapping->curves[c];
    if (curve->num_pivots < 2 || curve->num_pivots > AV_DOVI_MAX_PIECES + 1)
      return FALSE;
    for (guint i = 1; i < curve->num_pivots; i++)
      if (curve->pivots[i] < curve->pivots[i - 1])
        return FALSE;
    for (guint i = 0; i + 1 < curve->num_pivots; i++) {
      if ((curve->mapping_idc[i] == AV_DOVI_MAPPING_POLYNOMIAL &&
              (curve->poly_order[i] < 1 || curve->poly_order[i] > 2)) ||
          (curve->mapping_idc[i] == AV_DOVI_MAPPING_MMR &&
              (curve->mmr_order[i] < 1 || curve->mmr_order[i] > 3)) ||
          curve->mapping_idc[i] > AV_DOVI_MAPPING_MMR)
        return FALSE;
    }
  }
  for (int i = 0; i < m->num_ext_blocks; i++) {
    switch (av_dovi_get_ext (m, i)->level) {
      case 1: case 2: case 3: case 4: case 5: case 6: case 8: case 9:
      case 10: case 11: case 254: case 255: break;
      default: return FALSE;
    }
  }
  const AVDOVIColorMetadata *color = av_dovi_get_color (m);
  if (color->signal_bit_depth < 8 || color->signal_bit_depth > 16)
    return FALSE;
  for (guint i = 0; i < 9; i++)
    if (color->ycc_to_rgb_matrix[i].den <= 0 || color->rgb_to_lms_matrix[i].den <= 0)
      return FALSE;
  for (guint i = 0; i < 3; i++)
    if (color->ycc_to_rgb_offset[i].den <= 0)
      return FALSE;
  return TRUE;
}

GstDoviPicture *
gst_dovi_picture_new (const AVDOVIMetadata *metadata, gsize size,
    const AVDOVIDecoderConfigurationRecord *config, GBytes *rpu,
    const GstDoviGeometry *geometry, guint64 epoch, guint64 id, GError **error)
{
  GstDoviPicture *p = NULL;
  gsize raw_size;
  const guint8 *raw = rpu ? g_bytes_get_data (rpu, &raw_size) : NULL;
  if (avutil_version () != LIBAVUTIL_VERSION_INT || !raw || raw_size < 7 ||
      raw_size > GST_DOVI_MAX_RPU_SIZE || raw[0] != 0x19 || !geometry || !geometry->coded_width || !geometry->coded_height ||
      !geometry->width || !geometry->height ||
      geometry->coded_width > G_MAXINT || geometry->coded_height > G_MAXINT ||
      geometry->x >= geometry->coded_width ||
      geometry->y >= geometry->coded_height ||
      geometry->width > geometry->coded_width - geometry->x ||
      geometry->height > geometry->coded_height - geometry->y ||
      !metadata_valid (metadata, size) ||
      (config && (!config->bl_present_flag || !config->rpu_present_flag))) {
    gst_dovi_fail (error, "incompatible runtime, invalid metadata or missing original picture RPU");
    return NULL;
  }
  p = g_new0 (GstDoviPicture, 1);
  p->metadata = av_dovi_metadata_alloc (NULL);
  if (!p->metadata) {
    g_clear_pointer (&p, g_free);
    gst_dovi_fail (error, "metadata allocation failed");
    return NULL;
  }
  /* Copy typed public values into the allocator's own layout. Source offsets,
   * padding and frame allocation addresses never become an exported blob. */
  *av_dovi_get_header (p->metadata) = *av_dovi_get_header (metadata);
  *av_dovi_get_mapping (p->metadata) = *av_dovi_get_mapping (metadata);
  *av_dovi_get_color (p->metadata) = *av_dovi_get_color (metadata);
  p->metadata->num_ext_blocks = metadata->num_ext_blocks;
  for (int i = 0; i < metadata->num_ext_blocks; i++)
    *av_dovi_get_ext (p->metadata, i) = *av_dovi_get_ext (metadata, i);
  p->refs = 1;
  p->rpu = g_bytes_ref (rpu);
  p->geometry = *geometry; p->epoch = epoch; p->id = id;
  /* HEVC profile guess follows FFmpeg dovi_rpu.c; no container compatibility
   * ID is invented. Container configuration remains a separate stream fact. */
  const AVDOVIRpuDataHeader *header = av_dovi_get_header (metadata);
  if (header->vdr_rpu_profile == 0 && header->bl_video_full_range_flag)
    p->profile = 5;
  else if (header->vdr_rpu_profile == 1)
    p->profile = header->el_spatial_resampling_filter_flag && !header->disable_residual_flag ?
        (header->vdr_bit_depth == 12 ? 7 : 4) : 8;
  if (config) {
    p->config = *config;
    p->config_known = TRUE;
    p->profile = config->dv_profile;
  }
  p->enhancement = av_dovi_get_header (metadata)->disable_residual_flag ?
      GST_DOVI_ENHANCEMENT_NOT_REQUIRED : GST_DOVI_ENHANCEMENT_UNRECONSTRUCTED;
  return p;
}

GstDoviPicture *
gst_dovi_picture_from_avframe (const AVFrame *frame, GBytes *rpu,
    guint64 epoch, guint64 picture_id, GError **error)
{
  return gst_dovi_picture_from_avframe_with_config (frame, rpu, NULL,
      epoch, picture_id, error);
}

GstDoviPicture *
gst_dovi_picture_from_avframe_with_config (const AVFrame *frame, GBytes *rpu,
    const AVDOVIDecoderConfigurationRecord *config,
    guint64 epoch, guint64 picture_id, GError **error)
{
  AVFrameSideData *sd = frame ? av_frame_get_side_data (frame, AV_FRAME_DATA_DOVI_METADATA) : NULL;
  AVFrameSideData *raw_sd = frame ? av_frame_get_side_data (frame, AV_FRAME_DATA_DOVI_RPU_BUFFER) : NULL;
  GstDoviPicture *p;
  GBytes *owned;
  GstDoviGeometry geometry = {0};
  const AVPixFmtDescriptor *format = frame ? av_pix_fmt_desc_get (frame->format) : NULL;
  const AVDictionaryEntry *provenance = raw_sd ? av_dict_get (raw_sd->metadata,
      AV_DOVI_METADATA_STRICT_KEY, NULL, 0) : NULL;
  if (!provenance || strcmp (provenance->value, AV_DOVI_METADATA_STRICT_VALUE)) {
    gst_dovi_fail (error, "matched AVFrame lacks strict Dolby decoder provenance");
    return NULL;
  }
  /* Typed source geometry came from this frame's SPS before FFmpeg applied
   * conformance cropping. Reject missing, rounded or partially cropped output. */
  guint *fields[] = { &geometry.coded_width, &geometry.coded_height,
    &geometry.x, &geometry.y, &geometry.width, &geometry.height };
  const gchar *keys[] = { "coded_width", "coded_height", "x", "y", "width", "height" };
  for (guint i = 0; i < G_N_ELEMENTS (fields); i++) {
    gchar *key = g_strconcat (AV_DOVI_METADATA_GEOMETRY_PREFIX, keys[i], NULL);
    const AVDictionaryEntry *value = av_dict_get (raw_sd->metadata, key, NULL, 0);
    g_free (key);
    if (!value || !value->value[0]) goto geometry_error;
    for (const gchar *c = value->value; *c; c++)
      if (*c < '0' || *c > '9') goto geometry_error;
    guint64 number = g_ascii_strtoull (value->value, NULL, 10);
    if (number > G_MAXUINT) goto geometry_error;
    *fields[i] = number;
  }
  if (!format || format->nb_components < 3 || (format->flags & AV_PIX_FMT_FLAG_RGB) ||
      format->log2_chroma_w > 2 || format->log2_chroma_h > 2 ||
      geometry.x % (1u << format->log2_chroma_w) ||
      geometry.y % (1u << format->log2_chroma_h) ||
      geometry.width % (1u << format->log2_chroma_w) ||
      geometry.height % (1u << format->log2_chroma_h) ||
      frame->crop_left || frame->crop_right || frame->crop_top || frame->crop_bottom ||
      frame->width != (gint) geometry.width || frame->height != (gint) geometry.height)
    goto geometry_error;
  if (!sd || !raw_sd || !raw_sd->data || raw_sd->size < 7 || raw_sd->size > GST_DOVI_MAX_RPU_SIZE || frame->width <= 0 || frame->height <= 0) {
    gst_dovi_fail (error, "matched decoded AVFrame lacks resolved metadata or its original RPU");
    return NULL;
  }
  if (rpu) {
    gsize size;
    const guint8 *raw = g_bytes_get_data (rpu, &size);
    if (size != raw_sd->size || memcmp (raw, raw_sd->data, size)) {
      gst_dovi_fail (error, "decoded AVFrame RPU differs from its matched input picture");
      return NULL;
    }
    owned = g_bytes_ref (rpu);
  } else {
    /* Direct demux->avdec is also safe: use this matched AVFrame's own raw
     * side data, copied before the decoder releases it. */
    owned = g_bytes_new (raw_sd->data, raw_sd->size);
  }
  p = gst_dovi_picture_new ((const AVDOVIMetadata *) sd->data, sd->size,
      config, owned, &geometry, epoch, picture_id, error);
  g_bytes_unref (owned);
  if (p && format->comp[0].depth != av_dovi_get_header (p->metadata)->bl_bit_depth) {
    gst_dovi_picture_unref (p);
    return gst_dovi_fail (error, "decoded sample depth differs from source RPU"), NULL;
  }
  return p;
geometry_error:
  gst_dovi_fail (error, "missing, unsupported or incomplete source conformance geometry");
  return NULL;
}

GstDoviPicture *gst_dovi_picture_ref (GstDoviPicture *p) { g_atomic_int_inc (&p->refs); return p; }
void gst_dovi_picture_unref (GstDoviPicture *p) {
  if (p && g_atomic_int_dec_and_test (&p->refs)) {
    av_free (p->metadata); g_bytes_unref (p->rpu); g_free (p);
  }
}
const AVDOVIMetadata *gst_dovi_picture_get_metadata (const GstDoviPicture *p) { return p->metadata; }
GBytes *gst_dovi_picture_get_rpu (const GstDoviPicture *p) { return p->rpu; }
guint gst_dovi_picture_get_profile (const GstDoviPicture *p) { return p->profile; }
const AVDOVIDecoderConfigurationRecord *gst_dovi_picture_get_stream_config (const GstDoviPicture *p) { return p->config_known ? &p->config : NULL; }
GstDoviEnhancement gst_dovi_picture_get_enhancement (const GstDoviPicture *p) { return p->enhancement; }
void gst_dovi_picture_get_identity (const GstDoviPicture *p, guint64 *epoch, guint64 *id) {
  if (epoch) *epoch = p->epoch;
  if (id) *id = p->id;
}
const GstDoviGeometry *gst_dovi_picture_get_geometry (const GstDoviPicture *p) { return &p->geometry; }
void gst_dovi_picture_get_dimensions (const GstDoviPicture *p, guint *width, guint *height) {
  if (width) *width = p->geometry.width;
  if (height) *height = p->geometry.height;
}

typedef struct {
  GstDoviPictureMeta public;
  AVFrame *fel;
} OwnedMeta;

const AVFrame *gst_dovi_picture_meta_get_fel (const GstDoviPictureMeta *meta) {
  return meta ? ((const OwnedMeta *) meta)->fel : NULL;
}

static gboolean meta_init (GstMeta *meta, gpointer params, GstBuffer *buffer) {
  (void) params; (void) buffer; ((OwnedMeta *) meta)->public.picture = NULL; ((OwnedMeta *) meta)->fel = NULL; return TRUE;
}
static void meta_free (GstMeta *meta, GstBuffer *buffer) {
  (void) buffer; av_frame_free (&((OwnedMeta *) meta)->fel);
  gst_dovi_picture_unref (((GstDoviPictureMeta *) meta)->picture);
}
static gboolean meta_transform (GstBuffer *dest, GstMeta *meta,
    GstBuffer *src, GQuark type, gpointer data) {
  (void) src;
  if (GST_META_TRANSFORM_IS_COPY (type) && !((GstMetaTransformCopy *) data)->region) {
    OwnedMeta *owned = (OwnedMeta *) meta;
    AVFrame *frame = owned->fel ? av_frame_clone (owned->fel) : NULL;
    return gst_dovi_add_meta_take_frame (dest, owned->public.picture, frame) != NULL;
  }
  return FALSE;
}
GType gst_dovi_picture_meta_api_get_type (void) {
  static gsize type;
  static const gchar *tags[] = { "video", "colorspace", "size", "orientation", NULL };
  if (g_once_init_enter (&type)) {
    GType value = gst_meta_api_type_register ("GstDoviPictureMetaAPI", tags);
    g_once_init_leave (&type, value);
  }
  return type;
}
const GstMetaInfo *gst_dovi_picture_meta_get_info (void) {
  static gsize info;
  if (g_once_init_enter (&info)) {
    const GstMetaInfo *value = gst_meta_register (GST_DOVI_PICTURE_META_API_TYPE,
        "GstDoviPictureMeta", sizeof (OwnedMeta), meta_init, meta_free, meta_transform);
    g_once_init_leave (&info, (gsize) value);
  }
  return (const GstMetaInfo *) info;
}
GstDoviPictureMeta *gst_buffer_add_dovi_picture_meta (GstBuffer *buffer, GstDoviPicture *p) {
  return gst_dovi_add_meta_take_frame (buffer, p, NULL);
}

GstDoviPictureMeta *gst_dovi_add_meta_take_frame (GstBuffer *buffer,
    GstDoviPicture *p, AVFrame *frame) {
  GstDoviPictureMeta *meta;
  if (!p || gst_buffer_get_dovi_picture_meta (buffer)) {
    av_frame_free (&frame);
    return NULL;
  }
  meta = (GstDoviPictureMeta *) gst_buffer_add_meta (buffer, GST_DOVI_PICTURE_META_INFO, NULL);
  if (meta) {
    meta->picture = gst_dovi_picture_ref (p);
    ((OwnedMeta *) meta)->fel = frame;
  } else {
    av_frame_free (&frame);
  }
  return meta;
}
