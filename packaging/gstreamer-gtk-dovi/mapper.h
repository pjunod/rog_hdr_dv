/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GST_GTK_DOVI_MAPPER_H
#define GST_GTK_DOVI_MAPPER_H
#include <gst/video/video.h>
typedef struct GstGtkDoviMapper GstGtkDoviMapper;
/* Caller serializes mapper on the streaming thread. Target is a copied GDK
 * snapshot, never a GdkSurface dereferenced from the streaming thread. */
typedef struct {
  guint64 generation;
  double primaries[8], min_nits, max_nits, reference_nits;
  gboolean valid;
} GstGtkDoviTarget;
GstGtkDoviMapper *gst_gtk_dovi_mapper_new (void);
void gst_gtk_dovi_mapper_free (GstGtkDoviMapper *self);
/* 1 mapped, 0 no usable DV/target, -1 eligible frame failed. On 0 caller uses
 * its unchanged stock renderer. Mapped result owns independent RGBA64_LE pixels
 * with RGB/full-range/BT2020/PQ VideoInfo, never stale Dolby metadata. */
int gst_gtk_dovi_mapper_render (GstGtkDoviMapper *self, GstBuffer *input,
    const GstVideoInfo *info, const GstGtkDoviTarget *target,
    GstBuffer **output, GstVideoInfo *output_info, GError **error);
#endif
