/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GST_GTK_DOVI_SOURCE_LEASE_PRIVATE_H
#define GST_GTK_DOVI_SOURCE_LEASE_PRIVATE_H
#include "mapper.h"
GST_GTK_DOVI_API GstGtkDoviSourceLease *_gst_gtk_dovi_source_lease_new_selected (
    const GstCaps *, const gchar *, guint64 revision, guint64 selection);
GST_GTK_DOVI_API guint64 _gst_gtk_dovi_source_lease_selection (const GstGtkDoviSourceLease *);
#endif
