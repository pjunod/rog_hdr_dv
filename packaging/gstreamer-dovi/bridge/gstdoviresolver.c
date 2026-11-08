/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "gstdovipicture-private.h"
#include <libavcodec/dovi_parser.h>
#include <libavutil/error.h>
#include <libavutil/mem.h>
#include <string.h>
struct _GstDoviResolver {
  AVDoviRpuParser *parser;
  guint64 epoch;
  gboolean config_known;
  AVDOVIDecoderConfigurationRecord config;
};
GstDoviResolver *gst_dovi_resolver_new (void) {
  GstDoviResolver *r = g_new0 (GstDoviResolver, 1);
  r->parser = av_dovi_rpu_parser_alloc (NULL);
  if (!r->parser) { g_free (r); return NULL; }
  r->epoch = 1;
  return r;
}
void gst_dovi_resolver_free (GstDoviResolver *r) {
  if (r) { av_dovi_rpu_parser_free (&r->parser); g_free (r); }
}
void gst_dovi_resolver_reset (GstDoviResolver *r) {
  av_dovi_rpu_parser_flush (r->parser); r->epoch++;
}
gboolean gst_dovi_resolver_configure (GstDoviResolver *r,
    const AVDOVIDecoderConfigurationRecord *config, gsize size, GError **error) {
  int ret;
  r->epoch++;
  r->config_known = FALSE;
  memset (&r->config, 0, sizeof (r->config));
  ret = av_dovi_rpu_parser_configure (r->parser, config, size);
  if (ret < 0) return gst_dovi_fail (error, "invalid authoritative Dolby stream configuration");
  if (config) {
    /* Copy only the public fields covered by configure's minimum size. */
#define COPY(field) r->config.field = config->field
    COPY(dv_version_major); COPY(dv_version_minor); COPY(dv_profile);
    COPY(dv_level); COPY(rpu_present_flag); COPY(el_present_flag);
    COPY(bl_present_flag); COPY(dv_bl_signal_compatibility_id); COPY(dv_md_compression);
#undef COPY
    r->config_known = TRUE;
  }
  return TRUE;
}
GstDoviPicture *gst_dovi_resolver_resolve (GstDoviResolver *r, GBytes *rpu,
    guint width, guint height, guint64 id, GError **error) {
  GstDoviGeometry geometry = { width, height, 0, 0, width, height };
  return gst_dovi_resolver_resolve_geometry (r, rpu, &geometry, id, error);
}
GstDoviPicture *gst_dovi_resolver_resolve_geometry (GstDoviResolver *r, GBytes *rpu,
    const GstDoviGeometry *geometry, guint64 id, GError **error) {
  gsize size, metadata_size = 0;
  const guint8 *raw = rpu ? g_bytes_get_data (rpu, &size) : NULL;
  AVDOVIMetadata *metadata = NULL;
  GstDoviPicture *p = NULL;
  int ret;
  if (!raw) { gst_dovi_fail (error, "picture has no original RPU"); return NULL; }
  ret = av_dovi_rpu_parser_parse (r->parser, raw, size, &metadata, &metadata_size);
  if (ret < 0) {
    gchar message[AV_ERROR_MAX_STRING_SIZE];
    av_strerror (ret, message, sizeof (message));
    gst_dovi_fail (error, message);
  } else {
    p = gst_dovi_picture_new (metadata, metadata_size,
        r->config_known ? &r->config : NULL, rpu, geometry, r->epoch, id, error);
    if (!p) gst_dovi_resolver_reset (r);
  }
  av_free (metadata);
  return p;
}
