/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GST_DOVI_PICTURE_PRIVATE_H
#define GST_DOVI_PICTURE_PRIVATE_H
#include "gstdovipicture.h"
GstDoviPicture *gst_dovi_picture_new (const AVDOVIMetadata *metadata, gsize size,
    const AVDOVIDecoderConfigurationRecord *config, GBytes *rpu, const GstDoviGeometry *geometry, guint64 epoch, guint64 id, GError **error);
gboolean gst_dovi_fail (GError **error, const gchar *message);
#endif
