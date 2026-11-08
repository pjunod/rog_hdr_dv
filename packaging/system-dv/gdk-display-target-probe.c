/* SPDX-License-Identifier: MIT */
/* Native GTK/Wayland target observer. Compile-only until independent review.
 * This observes GDK's existing surface; it creates no Wayland color objects.
 */
#include <gtk/gtk.h>
#include <gdk/wayland/gdkwayland.h>
#include <stdio.h>

static void
report_target (GdkSurface *surface, gpointer user_data)
{
  GdkWaylandColorTarget target;
  (void) user_data;
  gboolean ready = gdk_wayland_surface_get_color_target (surface, &target);

  printf ("{\"generation\":%" G_GUINT64_FORMAT ",\"ready\":%s",
          target.generation, ready ? "true" : "false");
  if (ready)
    {
      printf (",\"identity\":%u,\"xy\":[", target.identity);
      for (guint i = 0; i < G_N_ELEMENTS (target.primaries); i++)
        printf ("%s%.6f", i ? "," : "", target.primaries[i]);
      printf ("],\"black_cd_m2\":%.4f,\"peak_cd_m2\":%.0f,"
              "\"reference_white_cd_m2\":%.0f",
              target.min_luminance, target.max_luminance,
              target.reference_luminance);
    }
  puts ("}");
  fflush (stdout);
}

static void
on_realize (GtkWidget *widget, gpointer user_data)
{
  GdkSurface *surface = gtk_native_get_surface (GTK_NATIVE (widget));
  (void) user_data;
  if (!GDK_IS_WAYLAND_SURFACE (surface))
    {
      g_printerr ("A native Wayland GDK surface is required.\n");
      return;
    }

  /* Object connection disconnects before widget ownership ends. The snapshot
   * is copied on the GTK main context; no display object crosses threads. */
  g_signal_connect_object (surface, "color-target-changed",
                           G_CALLBACK (report_target), widget, 0);
  report_target (surface, NULL);
}

static void
activate (GtkApplication *application, gpointer user_data)
{
  (void) user_data;
  GtkWidget *window = gtk_application_window_new (application);
  gtk_window_set_title (GTK_WINDOW (window), "GDK target observation");
  gtk_window_set_default_size (GTK_WINDOW (window), 640, 360);
  g_signal_connect (window, "realize", G_CALLBACK (on_realize), NULL);
  gtk_window_present (GTK_WINDOW (window));
}

int
main (int argc, char **argv)
{
  g_autoptr (GtkApplication) application =
    gtk_application_new ("org.example.GdkTargetObservation", G_APPLICATION_NON_UNIQUE);
  g_signal_connect (application, "activate", G_CALLBACK (activate), NULL);
  return g_application_run (G_APPLICATION (application), argc, argv);
}
