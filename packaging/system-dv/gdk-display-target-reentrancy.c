/* SPDX-License-Identifier: MIT */
/* Real native GdkSurface lifecycle negatives. Run only after independent review.
 * Requires a Wayland compositor advertising parametric color management.
 */
#include <gtk/gtk.h>
#include <gdk/wayland/gdkwayland.h>
#include <stdio.h>
#include <string.h>

struct observation {
  GMainLoop *loop;
  GdkSurface *owned_surface;
  gboolean constructing;
  gboolean ready_mode;
  gboolean destroying;
  gboolean reentered;
  gboolean finalized;
  gboolean destroyed_before_reentry;
  gboolean native_gone_before_reentry;
  gboolean cleared_at_destruction;
  guint construction_signals;
  guint ready_signals;
  guint destruction_signals;
  guint late_signals;
  guint64 last_live_generation;
  guint64 destroyed_generation;
};

static gboolean
construction_hook (GSignalInvocationHint *hint, guint n_values,
                   const GValue *values, gpointer data)
{
  struct observation *o = data;
  (void) hint;
  (void) n_values;
  (void) values;
  if (o->constructing)
    o->construction_signals++;
  return TRUE;
}

static void
finalized (gpointer data, GObject *object)
{
  struct observation *o = data;
  (void) object;
  o->finalized = TRUE;
  g_main_loop_quit (o->loop);
}

static gboolean
snapshot_is_cleared (const GdkWaylandColorTarget *target)
{
  if (target->identity != 0 || target->min_luminance != 0 ||
      target->max_luminance != 0 || target->reference_luminance != 0)
    return FALSE;
  for (guint i = 0; i < G_N_ELEMENTS (target->primaries); i++)
    if (target->primaries[i] != 0)
      return FALSE;
  return TRUE;
}

static void
changed (GdkSurface *surface, gpointer data)
{
  struct observation *o = data;
  GdkWaylandColorTarget target;
  gboolean ready = gdk_wayland_surface_get_color_target (surface, &target);

  if (o->finalized)
    o->late_signals++;
  if (o->destroying)
    {
      o->destruction_signals++;
      o->destroyed_generation = target.generation;
      o->cleared_at_destruction = !ready && snapshot_is_cleared (&target);
      if (!o->reentered)
        {
          o->reentered = TRUE;
          o->destroyed_before_reentry = gdk_surface_is_destroyed (surface);
          o->native_gone_before_reentry =
            gdk_wayland_surface_get_wl_surface (surface) == NULL;
          /* destroy() consumes a reference even for an already-destroyed
           * surface. Supply our own reference, rather than consuming the
           * signal's borrowed instance. This must not reenter native teardown. */
          gdk_surface_destroy (g_object_ref (surface));
        }
      return;
    }

  o->last_live_generation = target.generation;
  if (ready)
    {
      o->ready_signals++;
      if (o->ready_mode)
        {
          /* Consume our only owned surface reference from inside the async
           * ready signal. The emitter must keep itself alive until return. */
          o->destroying = TRUE;
          o->owned_surface = NULL;
          gdk_surface_destroy (surface);
        }
    }
}

static gboolean
quit_loop (gpointer data)
{
  g_main_loop_quit (data);
  return G_SOURCE_REMOVE;
}

int
main (int argc, char **argv)
{
  if (argc != 2 || (strcmp (argv[1], "pending") && strcmp (argv[1], "ready")))
    {
      g_printerr ("usage: %s pending|ready\n", argv[0]);
      return 2;
    }
  gtk_init ();
  GdkDisplay *display = gdk_display_get_default ();
  if (!GDK_IS_WAYLAND_DISPLAY (display))
    {
      g_printerr ("native Wayland required\n");
      return 2;
    }

  struct observation o = { .ready_mode = !strcmp (argv[1], "ready") };
  o.loop = g_main_loop_new (NULL, FALSE);
  gpointer klass = g_type_class_ref (GDK_TYPE_WAYLAND_SURFACE);
  guint signal_id = g_signal_lookup ("color-target-changed", GDK_TYPE_WAYLAND_SURFACE);
  g_assert_cmpuint (signal_id, !=, 0);
  gulong hook = g_signal_add_emission_hook (signal_id, 0, construction_hook, &o, NULL);
  o.constructing = TRUE;
  o.owned_surface = gdk_surface_new_toplevel (display);
  o.constructing = FALSE;
  g_type_class_unref (klass);
  g_object_weak_ref (G_OBJECT (o.owned_surface), finalized, &o);
  g_signal_connect (o.owned_surface, "color-target-changed", G_CALLBACK (changed), &o);

  GdkWaylandColorTarget initial;
  gboolean initial_ready = gdk_wayland_surface_get_color_target (o.owned_surface, &initial);
  o.last_live_generation = initial.generation;
  if (initial_ready || initial.generation == 0 || !snapshot_is_cleared (&initial))
    {
      g_printerr ("expected an outstanding parametric query; ready=%d generation=%"
                  G_GUINT64_FORMAT "\n", initial_ready, initial.generation);
      return 2;
    }

  if (o.ready_mode)
    {
      GSource *timeout = g_timeout_source_new_seconds (5);
      g_source_set_callback (timeout, quit_loop, o.loop, NULL);
      g_source_attach (timeout, NULL);
      g_main_loop_run (o.loop);
      g_source_destroy (timeout);
      g_source_unref (timeout);
    }
  if (o.owned_surface)
    {
      GdkSurface *surface = o.owned_surface;
      o.owned_surface = NULL;
      o.destroying = TRUE;
      gdk_surface_destroy (surface);
    }

  /* Dispatch replies from the cancelled query after finalization. They must
   * neither deliver a target nor resurrect the surface or its notification. */
  g_timeout_add (150, quit_loop, o.loop);
  g_main_loop_run (o.loop);
  g_signal_remove_emission_hook (signal_id, hook);
  g_main_loop_unref (o.loop);

  gboolean pass = o.construction_signals == 0 && o.reentered && o.finalized &&
                  o.destruction_signals == 1 && o.late_signals == 0 &&
                  o.destroyed_before_reentry && o.native_gone_before_reentry &&
                  o.cleared_at_destruction &&
                  o.destroyed_generation > o.last_live_generation &&
                  (o.ready_mode ? o.ready_signals == 1 : o.ready_signals == 0);
  printf ("%s mode=%s construction=%u ready=%u destroy=%u reentered=%d "
          "published_destroyed=%d native_gone=%d cleared=%d finalized=%d late=%u\n",
          pass ? "PASS" : "FAIL", argv[1], o.construction_signals, o.ready_signals,
          o.destruction_signals, o.reentered, o.destroyed_before_reentry,
          o.native_gone_before_reentry, o.cleared_at_destruction, o.finalized,
          o.late_signals);
  return pass ? 0 : 1;
}
