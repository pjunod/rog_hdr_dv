/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "gstdovipicture-private.h"
#include <gst/video/gstvideodecoder.h>
#include <string.h>
/* Native decoder fallback: derive association from this AU's own encoded
 * bytes, even when a demuxer connects straight to the decoder. This does not
 * parse RPU metadata; the public FFmpeg resolver remains authoritative. */
static gboolean start_code (const guint8 *data, gsize size, gsize from,
    gsize *begin, gsize *payload) {
  for (gsize i = from; i + 2 < size; i++)
    if (!data[i] && !data[i + 1] && data[i + 2] == 1) {
      *begin = i; *payload = i + 3; return TRUE;
    }
  return FALSE;
}
static gboolean collect (const guint8 *data, gsize size, GBytes **rpu,
    guint *first_slices, GByteArray *el, guint *el_slices, gboolean *irap) {
  if (size < 2 || (data[0] & 0x80) || !(data[1] & 7)) return FALSE;
  guint type = (data[0] >> 1) & 63;
  guint layer = ((data[0] & 1) << 5) | (data[1] >> 3);
  if (type <= 31) {
    if (layer || size < 3) return FALSE;
    if (data[2] & 0x80) (*first_slices)++;
  }
  if (type == 63 && el) {
    static const guint8 prefix[] = { 0, 0, 0, 1 };
    if (layer || size < 5 || (data[2] & 0x81) || (data[3] >> 3) || !(data[3] & 7))
      return FALSE;
    guint inner = (data[2] >> 1) & 63;
    if (inner >= 48 || size > 16 * 1024 * 1024 ||
        el->len + sizeof (prefix) > 16 * 1024 * 1024 - (size - 2)) return FALSE;
    if (inner < 32) {
      if (data[4] & 0x80) {
        (*el_slices)++;
        *irap = inner >= 16 && inner <= 21;
      } else if (!*el_slices) {
        return FALSE;
      }
    }
    g_byte_array_append (el, prefix, sizeof (prefix));
    g_byte_array_append (el, data + 2, size - 2);
  }
  if (type != 62) return TRUE;
  /* Annex-B trailing_zero_8bits do not belong to the RPU payload. */
  while (size > 2 && !data[size - 1]) size--;
  if (*rpu || layer || size < 9 || size - 2 > GST_DOVI_MAX_RPU_SIZE || data[2] != 0x19)
    return FALSE;
  *rpu = g_bytes_new (data + 2, size - 2);
  return TRUE;
}
static int extract_au (GstBuffer *buffer, const GstVideoCodecState *state,
    GBytes **rpu, GByteArray *el, gboolean *irap, GError **error) {
  GstMapInfo map;
  gboolean valid = TRUE;
  guint slices = 0, el_slices = 0, length_size = 0;
  const GstStructure *structure;
  const gchar *format, *alignment;
  *rpu = NULL;
  if (!state || !state->caps || gst_caps_get_size (state->caps) != 1 ||
      gst_buffer_get_size (buffer) > 64 * 1024 * 1024)
    goto fail;
  structure = gst_caps_get_structure (state->caps, 0);
  format = gst_structure_get_string (structure, "stream-format");
  alignment = gst_structure_get_string (structure, "alignment");
  /* hvc1/hev1 demux buffers are AU-aligned by the caps contract. Byte-stream
   * input must say so explicitly; a first slice alone cannot carry later RPU. */
  if (!format || (alignment && strcmp (alignment, "au")) ||
      (!strcmp (format, "byte-stream") && !alignment)) goto fail;
  if (!strcmp (format, "hvc1") || !strcmp (format, "hev1")) {
    GstMapInfo config;
    if (!state->codec_data || !gst_buffer_map (state->codec_data, &config, GST_MAP_READ)) goto fail;
    valid = config.size >= 23 && config.data[0] == 1;
    if (valid) length_size = (config.data[21] & 3) + 1;
    gst_buffer_unmap (state->codec_data, &config);
    if (!valid) goto fail;
  } else if (strcmp (format, "byte-stream")) goto fail;
  if (!gst_buffer_map (buffer, &map, GST_MAP_READ)) goto fail;
  if (length_size) {
    gsize offset = 0;
    while (offset < map.size) {
      guint32 size = 0;
      if (map.size - offset < length_size) { valid = FALSE; break; }
      for (guint i = 0; i < length_size; i++) size = (size << 8) | map.data[offset++];
      if (size > map.size - offset || !collect (map.data + offset, size, rpu, &slices, el, &el_slices, irap)) {
        valid = FALSE; break;
      }
      offset += size;
    }
  } else {
    gsize begin, payload;
    valid = start_code (map.data, map.size, 0, &begin, &payload);
    if (valid) {
      for (gsize i = 0; i < begin; i++) if (map.data[i]) valid = FALSE;
      while (valid) {
        gsize next, next_payload;
        gboolean more = start_code (map.data, map.size, payload, &next, &next_payload);
        gsize end = more ? next : map.size;
        valid = collect (map.data + payload, end - payload, rpu, &slices, el, &el_slices, irap);
        if (!more) break;
        payload = next_payload;
      }
    }
  }
  gst_buffer_unmap (buffer, &map);
  if (!valid || slices != 1 || (el && el_slices != 1)) goto fail;
  return *rpu ? 1 : 0;
fail:
  g_clear_pointer (rpu, g_bytes_unref);
  gst_dovi_fail (error, "malformed, ambiguous or non-AU HEVC picture");
  return -1;
}

int gst_dovi_extract_hevc_rpu (GstBuffer *buffer, const GstVideoCodecState *state,
    GBytes **rpu, GError **error) {
  return extract_au (buffer, state, rpu, NULL, NULL, error);
}

GBytes *gst_dovi_extract_fel (GstBuffer *buffer, const GstVideoCodecState *state,
    GstDoviPicture *picture, gboolean *irap) {
  GBytes *rpu = NULL;
  GByteArray *el = g_byte_array_new ();
  *irap = FALSE;
  gboolean valid = extract_au (buffer, state, &rpu, el, irap, NULL) == 1 &&
      g_bytes_equal (rpu, gst_dovi_picture_get_rpu (picture));
  g_clear_pointer (&rpu, g_bytes_unref);
  if (valid) return g_byte_array_free_to_bytes (el);
  g_byte_array_unref (el);
  return NULL;
}
