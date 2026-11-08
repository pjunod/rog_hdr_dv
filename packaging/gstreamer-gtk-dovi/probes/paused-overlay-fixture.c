/* SPDX-License-Identifier: MIT
 * Product-only fixture: metadata changes, never video pixel changes.
 * Build privately against the normal GTK/GStreamer SDK; do not install.
 */
#include <gst/base/gstbasetransform.h>
#include <gst/video/video.h>
#include <gtk/gtk.h>
#include <gmodule.h>

typedef struct {
  gint finalized;
  guint id, mode, ordinal;
  GstClockTime pts;
} Tracked;
static GMutex ledger_lock;
static GPtrArray *ledger;
static guint next_id;
static void finalized (gpointer data, GstMiniObject *object) {
  (void) object;
  g_atomic_int_set (&((Tracked *) data)->finalized, 1);
}
static void track (GstVideoOverlayComposition *composition, guint mode,
    guint ordinal, GstClockTime pts) {
  Tracked *entry = g_new0 (Tracked, 1);
  entry->mode = mode; entry->ordinal = ordinal; entry->pts = pts;
  g_mutex_lock (&ledger_lock);
  entry->id = ++next_id;
  g_ptr_array_add (ledger, entry);
  g_mutex_unlock (&ledger_lock);
  gst_mini_object_weak_ref ((GstMiniObject *) composition, finalized, entry);
}

typedef struct {
  GstBaseTransform parent;
  gint mode;
  GdkPaintable *paintable;
  GMutex lock;
  gchar *latest;
} ReviewOverlay;
typedef struct { GstBaseTransformClass parent; } ReviewOverlayClass;
G_DEFINE_TYPE (ReviewOverlay, review_overlay, GST_TYPE_BASE_TRANSFORM)
enum { PROP_0, PROP_MODE, PROP_PAINTABLE };
static guint capture_signal, metadata_signal, lifetime_signal;

static gchar *metadata (GstBuffer *buffer) {
  GString *s = g_string_new (NULL);
  gpointer state = NULL;
  GstMeta *meta;
  guint index = 0, rectangles = 0;
  g_string_append_printf (s, "{\"pts\":%" G_GUINT64_FORMAT ",\"metas\":[", GST_BUFFER_PTS (buffer));
  while ((meta = gst_buffer_iterate_meta_filtered (buffer, &state,
          GST_VIDEO_OVERLAY_COMPOSITION_META_API_TYPE))) {
    GstVideoOverlayComposition *c = ((GstVideoOverlayCompositionMeta *) meta)->overlay;
    if (index++) g_string_append_c (s, ',');
    g_string_append_c (s, '[');
    for (guint i = 0; i < gst_video_overlay_composition_n_rectangles (c); i++) {
      GstVideoOverlayRectangle *r = gst_video_overlay_composition_get_rectangle (c, i);
      gint x, y; guint width, height;
      gst_video_overlay_rectangle_get_render_rectangle (r, &x, &y, &width, &height);
      if (i) g_string_append_c (s, ',');
      g_string_append_printf (s,
          "{\"x\":%d,\"y\":%d,\"w\":%u,\"h\":%u,\"alpha\":%.9g}",
          x, y, width, height, gst_video_overlay_rectangle_get_global_alpha (r));
      rectangles++;
    }
    g_string_append_c (s, ']');
  }
  g_string_append_printf (s, "],\"meta_count\":%u,\"rectangles\":%u}", index, rectangles);
  return g_string_free (s, FALSE);
}

static void add_composition (GstBuffer *buffer, guint mode, guint ordinal) {
  GstVideoOverlayComposition *composition = NULL;
  /* Two overlapping rectangles in each composition. Distinct positions,
   * premultiplied pixels and global alpha make order/alpha observable. */
  for (guint i = 0; i < 2; i++) {
    GstBuffer *pixels = gst_buffer_new_allocate (NULL, 16 * 16 * 4, NULL);
    GstMapInfo map;
    g_assert (gst_buffer_map (pixels, &map, GST_MAP_WRITE));
    guint8 a = 128 + i * 64;
    for (guint j = 0; j < 16 * 16; j++) {
      map.data[j * 4 + 0] = (mode * 31 + ordinal * 19 + i * 23) % a;
      map.data[j * 4 + 1] = (mode * 53 + ordinal * 41 + i * 17) % a;
      map.data[j * 4 + 2] = (mode * 71 + ordinal * 29 + i * 13) % a;
      map.data[j * 4 + 3] = a;
    }
    gst_buffer_unmap (pixels, &map);
    gst_buffer_add_video_meta (pixels, GST_VIDEO_FRAME_FLAG_NONE,
        GST_VIDEO_OVERLAY_COMPOSITION_FORMAT_RGB, 16, 16);
    GstVideoOverlayRectangle *r = gst_video_overlay_rectangle_new_raw (pixels,
        64 + ordinal * 41 + i * 7, 72 + ordinal * 29 + i * 9,
        96 + i * 8, 80 + i * 12, GST_VIDEO_OVERLAY_FORMAT_FLAG_PREMULTIPLIED_ALPHA);
    gst_buffer_unref (pixels);
    gst_video_overlay_rectangle_set_global_alpha (r, i ? .75f : .375f);
    if (!composition) composition = gst_video_overlay_composition_new (r);
    else gst_video_overlay_composition_add_rectangle (composition, r);
    gst_video_overlay_rectangle_unref (r);
  }
  track (composition, mode, ordinal, GST_BUFFER_PTS (buffer));
  gst_buffer_add_video_overlay_composition_meta (buffer, composition);
  gst_video_overlay_composition_unref (composition);
}

static GstFlowReturn transform_ip (GstBaseTransform *base, GstBuffer *buffer) {
  ReviewOverlay *self = (ReviewOverlay *) base;
  guint mode = g_atomic_int_get (&self->mode);
  if (mode == 2 || mode == 3) {
    GstMeta *meta;
    while ((meta = gst_buffer_get_meta (buffer, GST_VIDEO_OVERLAY_COMPOSITION_META_API_TYPE)))
      gst_buffer_remove_meta (buffer, meta);
  }
  if (mode == 0) add_composition (buffer, mode, 0); /* stale pre-mapper source */
  if (mode == 1 || mode == 2) {
    add_composition (buffer, mode, 1);
    add_composition (buffer, mode, 2);
  }
  gchar *text = metadata (buffer);
  g_mutex_lock (&self->lock);
  g_free (self->latest); self->latest = text;
  g_mutex_unlock (&self->lock);
  return GST_FLOW_OK;
}

static GstCaps *transform_caps (GstBaseTransform *base, GstPadDirection direction,
    GstCaps *caps, GstCaps *filter) {
  /* The pre-mapper control is deliberately obsolete metadata, not an
   * instruction to render it. Only the downstream stage advertises overlays. */
  if (g_atomic_int_get (&((ReviewOverlay *) base)->mode) == 0) {
    return filter ? gst_caps_intersect_full (filter, caps, GST_CAPS_INTERSECT_FIRST)
                  : gst_caps_ref (caps);
  }
  GstCaps *result = gst_caps_new_empty ();
  for (guint i = 0; i < gst_caps_get_size (caps); i++) {
    const GstStructure *structure = gst_caps_get_structure (caps, i);
    GstCapsFeatures *features = gst_caps_features_copy (gst_caps_get_features (caps, i));
    if (!gst_caps_features_is_any (features)) {
      if (direction == GST_PAD_SINK)
        gst_caps_features_add (features, GST_CAPS_FEATURE_META_GST_VIDEO_OVERLAY_COMPOSITION);
      else {
        GstCapsFeatures *plain = gst_caps_features_copy (features);
        gst_caps_features_remove (plain, GST_CAPS_FEATURE_META_GST_VIDEO_OVERLAY_COMPOSITION);
        gst_caps_append_structure_full (result, gst_structure_copy (structure), plain);
      }
    }
    gst_caps_append_structure_full (result, gst_structure_copy (structure), features);
  }
  if (filter) {
    GstCaps *intersection = gst_caps_intersect_full (filter, result, GST_CAPS_INTERSECT_FIRST);
    gst_caps_unref (result); result = intersection;
  }
  return result;
}

static void texture (GString *s, GskRenderNode *node, GdkTexture *t, double alpha, guint *count) {
  graphene_rect_t bounds;
  gsk_render_node_get_bounds (node, &bounds);
  int w = gdk_texture_get_width (t), h = gdk_texture_get_height (t);
  g_assert (w > 0 && h > 0 && w <= 16384 && h <= 16384);
  gsize stride = (gsize) w * 4 * sizeof (float), size = stride * h;
  guint8 *pixels = g_malloc (size);
  GdkTextureDownloader *download = gdk_texture_downloader_new (t);
  gdk_texture_downloader_set_format (download, GDK_MEMORY_R32G32B32A32_FLOAT_PREMULTIPLIED);
  gdk_texture_downloader_set_color_state (download, gdk_texture_get_color_state (t));
  gdk_texture_downloader_download_into (download, pixels, stride);
  gdk_texture_downloader_free (download);
  gchar *sha = g_compute_checksum_for_data (G_CHECKSUM_SHA256, pixels, size);
  g_free (pixels);
  if ((*count)++) g_string_append_c (s, ',');
  g_string_append_printf (s,
      "{\"pixel_w\":%d,\"pixel_h\":%d,\"x\":%.9g,\"y\":%.9g,\"w\":%.9g,\"h\":%.9g,\"alpha\":%.9g,\"sha256\":\"%s\"}",
      w, h, bounds.origin.x, bounds.origin.y, bounds.size.width, bounds.size.height, alpha, sha);
  g_free (sha);
}
static void nodes (GString *s, GskRenderNode *node, double alpha, guint *count) {
  if (!node) return;
  switch (gsk_render_node_get_node_type (node)) {
    case GSK_CONTAINER_NODE:
      for (guint i = 0; i < gsk_container_node_get_n_children (node); i++)
        nodes (s, gsk_container_node_get_child (node, i), alpha, count);
      break;
    case GSK_TEXTURE_NODE: texture (s, node, gsk_texture_node_get_texture (node), alpha, count); break;
    case GSK_TEXTURE_SCALE_NODE: texture (s, node, gsk_texture_scale_node_get_texture (node), alpha, count); break;
    case GSK_OPACITY_NODE: nodes (s, gsk_opacity_node_get_child (node), alpha * gsk_opacity_node_get_opacity (node), count); break;
    case GSK_TRANSFORM_NODE: nodes (s, gsk_transform_node_get_child (node), alpha, count); break;
    case GSK_CLIP_NODE: nodes (s, gsk_clip_node_get_child (node), alpha, count); break;
    case GSK_ROUNDED_CLIP_NODE: nodes (s, gsk_rounded_clip_node_get_child (node), alpha, count); break;
    case GSK_COLOR_MATRIX_NODE: nodes (s, gsk_color_matrix_node_get_child (node), alpha, count); break;
    case GSK_DEBUG_NODE: nodes (s, gsk_debug_node_get_child (node), alpha, count); break;
    case GSK_MASK_NODE:
      nodes (s, gsk_mask_node_get_source (node), alpha, count);
      nodes (s, gsk_mask_node_get_mask (node), alpha, count);
      break;
    default: break;
  }
}
static gchar *capture (ReviewOverlay *self) {
  if (!self->paintable) return g_strdup ("{\"error\":\"no paintable\"}");
  GtkSnapshot *snapshot = gtk_snapshot_new ();
  gdk_paintable_snapshot (self->paintable, GDK_SNAPSHOT (snapshot), 2560, 1280);
  GskRenderNode *node = gtk_snapshot_free_to_node (snapshot);
  GString *s = g_string_new ("{\"textures\":["); guint count = 0;
  nodes (s, node, 1., &count);
  if (node) gsk_render_node_unref (node);
  g_string_append_printf (s, "],\"texture_count\":%u}", count);
  return g_string_free (s, FALSE);
}
static gchar *latest (ReviewOverlay *self) {
  g_mutex_lock (&self->lock);
  gchar *s = g_strdup (self->latest ? self->latest : "{}");
  g_mutex_unlock (&self->lock); return s;
}
static gchar *lifetimes (ReviewOverlay *self) {
  (void) self;
  GString *s = g_string_new ("[");
  g_mutex_lock (&ledger_lock);
  for (guint i = 0; i < ledger->len; i++) {
    Tracked *entry = g_ptr_array_index (ledger, i);
    if (i) g_string_append_c (s, ',');
    g_string_append_printf (s,
        "{\"id\":%u,\"mode\":%u,\"ordinal\":%u,\"pts\":%" G_GUINT64_FORMAT ",\"finalized\":%s}",
        entry->id, entry->mode, entry->ordinal, entry->pts,
        g_atomic_int_get (&entry->finalized) ? "true" : "false");
  }
  g_mutex_unlock (&ledger_lock);
  g_string_append_c (s, ']'); return g_string_free (s, FALSE);
}
static void set_property (GObject *object, guint id, const GValue *value, GParamSpec *pspec) {
  ReviewOverlay *self = (ReviewOverlay *) object;
  if (id == PROP_MODE) g_atomic_int_set (&self->mode, g_value_get_uint (value));
  else if (id == PROP_PAINTABLE) g_set_object (&self->paintable, g_value_get_object (value));
  else G_OBJECT_WARN_INVALID_PROPERTY_ID (object, id, pspec);
}
static void get_property (GObject *object, guint id, GValue *value, GParamSpec *pspec) {
  ReviewOverlay *self = (ReviewOverlay *) object;
  if (id == PROP_MODE) g_value_set_uint (value, g_atomic_int_get (&self->mode));
  else if (id == PROP_PAINTABLE) g_value_set_object (value, self->paintable);
  else G_OBJECT_WARN_INVALID_PROPERTY_ID (object, id, pspec);
}
static void dispose (GObject *object) {
  g_clear_object (&((ReviewOverlay *) object)->paintable);
  G_OBJECT_CLASS (review_overlay_parent_class)->dispose (object);
}
static void finalize (GObject *object) {
  ReviewOverlay *self = (ReviewOverlay *) object;
  g_free (self->latest); g_mutex_clear (&self->lock);
  G_OBJECT_CLASS (review_overlay_parent_class)->finalize (object);
}
static void review_overlay_init (ReviewOverlay *self) {
  g_mutex_init (&self->lock);
  gst_base_transform_set_in_place (GST_BASE_TRANSFORM (self), TRUE);
}
static void review_overlay_class_init (ReviewOverlayClass *klass) {
  GObjectClass *object = G_OBJECT_CLASS (klass);
  object->set_property = set_property; object->get_property = get_property;
  object->dispose = dispose; object->finalize = finalize;
  g_object_class_install_property (object, PROP_MODE, g_param_spec_uint ("mode", "Mode",
      "0 stale upstream, 1 add downstream, 2 replace downstream, 3 remove downstream", 0, 3, 0, G_PARAM_READWRITE));
  g_object_class_install_property (object, PROP_PAINTABLE, g_param_spec_object ("paintable", "Paintable",
      "Actual sink paintable for main-thread snapshot inspection", G_TYPE_OBJECT, G_PARAM_READWRITE));
  GstElementClass *element = GST_ELEMENT_CLASS (klass);
  gst_element_class_set_static_metadata (element, "Paused overlay product fixture", "Testing", "Metadata-only overlays and actual paintable snapshot", "ROG HDR contributors");
  GstCaps *caps = gst_caps_from_string ("video/x-raw(ANY)");
  gst_element_class_add_pad_template (element, gst_pad_template_new ("sink", GST_PAD_SINK, GST_PAD_ALWAYS, caps));
  gst_element_class_add_pad_template (element, gst_pad_template_new ("src", GST_PAD_SRC, GST_PAD_ALWAYS, caps));
  gst_caps_unref (caps);
  GstBaseTransformClass *base = GST_BASE_TRANSFORM_CLASS (klass);
  base->transform_ip = transform_ip; base->transform_caps = transform_caps;
  capture_signal = g_signal_new_class_handler ("capture", G_TYPE_FROM_CLASS (klass), G_SIGNAL_RUN_LAST | G_SIGNAL_ACTION,
      G_CALLBACK (capture), NULL, NULL, NULL, G_TYPE_STRING, 0);
  metadata_signal = g_signal_new_class_handler ("metadata", G_TYPE_FROM_CLASS (klass), G_SIGNAL_RUN_LAST | G_SIGNAL_ACTION,
      G_CALLBACK (latest), NULL, NULL, NULL, G_TYPE_STRING, 0);
  lifetime_signal = g_signal_new_class_handler ("lifetimes", G_TYPE_FROM_CLASS (klass), G_SIGNAL_RUN_LAST | G_SIGNAL_ACTION,
      G_CALLBACK (lifetimes), NULL, NULL, NULL, G_TYPE_STRING, 0);
}
static gboolean plugin_init (GstPlugin *plugin) {
  ledger = g_ptr_array_new ();
  GModule *module = g_module_open (gst_plugin_get_filename (plugin), G_MODULE_BIND_LAZY);
  if (module) { g_module_make_resident (module); g_module_close (module); }
  return gst_element_register (plugin, "reviewoverlay", GST_RANK_NONE, review_overlay_get_type ());
}
#define PACKAGE "paused-overlay-product-fixture"
GST_PLUGIN_DEFINE (GST_VERSION_MAJOR, GST_VERSION_MINOR, reviewoverlay, "Paused overlay product fixture",
    plugin_init, "1", "MIT/X11", PACKAGE, "https://example.invalid")
