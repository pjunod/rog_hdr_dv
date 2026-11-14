/* SPDX-License-Identifier: MIT -- private ordinary GTK scene, no renderer selection. */
#define _GNU_SOURCE
#include <gtk/gtk.h>
#include <gdk/wayland/gdkwayland.h>
#include <wayland-client.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

static GtkApplication *application;
static GtkWidget *window, *area;
static FILE *receipt;
static gint64 started, last_frame = -1, presentation_time;
static guint after_paint, completed, draw_calls, generation;
static GdkFrameClock *observed_clock;
static gboolean written, scene_complete;
static char *expected_socket;
static gint64 expected_compositor_pid;
static struct ucred compositor;

static void
json_string (const char *text)
{
  fputc ('"', receipt);
  for (const unsigned char *p = (const unsigned char *) (text ? text : ""); *p; p++)
    {
      if (*p == '"' || *p == '\\')
        fprintf (receipt, "\\%c", *p);
      else if (*p < 32)
        fprintf (receipt, "\\u%04x", *p);
      else
        fputc (*p, receipt);
    }
  fputc ('"', receipt);
}

static void
finish (const char *status)
{
  if (written)
    return;
  written = TRUE;
  scene_complete = strcmp (status, "completed-private-frames") == 0;
  GskRenderer *renderer = window ? gtk_native_get_renderer (GTK_NATIVE (window)) : NULL;
  GdkSurface *surface = window ? gtk_native_get_surface (GTK_NATIVE (window)) : NULL;
  struct wl_surface *wl_surface = surface && GDK_IS_WAYLAND_SURFACE (surface)
                                ? gdk_wayland_surface_get_wl_surface (surface) : NULL;
  Dl_info library = { 0 };
  dladdr ((void *) gtk_window_new, &library);
  fprintf (receipt, "{\"status\":"); json_string (status);
  fprintf (receipt, ",\"renderer\":"); json_string (renderer ? G_OBJECT_TYPE_NAME (renderer) : NULL);
  fprintf (receipt, ",\"gtk_library\":"); json_string (library.dli_fname);
  fprintf (receipt, ",\"gtk_version\":[%u,%u,%u],\"pid\":%ld,\"wl_surface_id\":%u,",
           gtk_get_major_version (), gtk_get_minor_version (), gtk_get_micro_version (),
           (long) getpid (), wl_surface ? wl_proxy_get_id ((struct wl_proxy *) wl_surface) : 0);
  fprintf (receipt, "\"draw_calls\":%u,\"after_paint\":%u,\"gdk_complete_frames\":%u,\"last_complete_frame\":%lld,\"presentation_time_us\":%lld,\"elapsed_us\":%lld,",
           draw_calls, after_paint, completed, (long long) last_frame, (long long) presentation_time,
           (long long) (g_get_monotonic_time () - started));
  fprintf (receipt, "\"compositor_pid\":%ld,\"compositor_uid\":%u,", (long) compositor.pid, compositor.uid);
  fprintf (receipt, "\"scope\":\"GDK timing metadata on a private compositor; no physical presentation or optical claim\"}\n");
  fflush (receipt);
  fsync (fileno (receipt));
  if (window)
    gtk_window_destroy (GTK_WINDOW (window));
  g_application_quit (G_APPLICATION (application));
}

static void
paint (GtkDrawingArea *widget, cairo_t *cr, int width, int height, gpointer data)
{
  static const double colors[4][3] = { { .8,.1,.1 }, { .1,.7,.1 }, { .1,.1,.8 }, { .5,.5,.5 } };
  (void) widget; (void) data;
  draw_calls++;
  for (int i = 0; i < 4; i++)
    {
      cairo_set_source_rgb (cr, colors[i][0], colors[i][1], colors[i][2]);
      cairo_rectangle (cr, (i % 2) * width / 2.0, (i / 2) * height / 2.0, width / 2.0, height / 2.0);
      cairo_fill (cr);
    }
  cairo_set_source_rgb (cr, generation % 2, generation % 2, generation % 2);
  cairo_rectangle (cr, 0, 0, 16, 16);
  cairo_fill (cr);
}

static void
painted (GdkFrameClock *clock, gpointer data)
{
  (void) clock; (void) data;
  after_paint++;
}

static void
observe_clock (GdkFrameClock *clock)
{
  if (clock && clock != observed_clock)
    {
      observed_clock = clock;
      g_signal_connect (clock, "after-paint", G_CALLBACK (painted), NULL);
    }
}

static gboolean
tick (gpointer data)
{
  (void) data;
  if (!window || !area)
    {
      finish ("closed-before-completion");
      return G_SOURCE_REMOVE;
    }
  GdkFrameClock *clock = gtk_widget_get_frame_clock (window);
  observe_clock (clock);
  if (clock)
    {
      gint64 end = gdk_frame_clock_get_frame_counter (clock);
      gint64 begin = MAX (last_frame + 1, gdk_frame_clock_get_history_start (clock));
      for (gint64 frame = begin; frame <= end; frame++)
        {
          GdkFrameTimings *timing = gdk_frame_clock_get_timings (clock, frame);
          if (timing && gdk_frame_timings_get_complete (timing) &&
              gdk_frame_timings_get_presentation_time (timing) > 0)
            {
              completed++;
              last_frame = frame;
              presentation_time = gdk_frame_timings_get_presentation_time (timing);
            }
        }
    }
  if (completed >= 3 && after_paint >= 3 && draw_calls >= 3)
    {
      finish ("completed-private-frames");
      return G_SOURCE_REMOVE;
    }
  if (g_get_monotonic_time () - started >= 15 * G_USEC_PER_SEC)
    {
      finish ("completion-deadline");
      return G_SOURCE_REMOVE;
    }
  generation++;
  gtk_widget_queue_draw (area);
  return G_SOURCE_CONTINUE;
}

static void
activate (GtkApplication *app, gpointer data)
{
  (void) data;
  GdkDisplay *display = gdk_display_get_default ();
  if (!GDK_IS_WAYLAND_DISPLAY (display))
    { finish ("not-private-wayland"); return; }
  struct wl_display *wl_display = gdk_wayland_display_get_wl_display (display);
  int fd = wl_display_get_fd (wl_display);
  struct sockaddr_un peer = { 0 };
  socklen_t peer_len = sizeof peer, cred_len = sizeof compositor;
  int peer_error = getpeername (fd, (struct sockaddr *) &peer, &peer_len);
  peer.sun_path[sizeof peer.sun_path - 1] = '\0';
  if (peer_error || strcmp (peer.sun_path, expected_socket) ||
      getsockopt (fd, SOL_SOCKET, SO_PEERCRED, &compositor, &cred_len) ||
      compositor.pid != expected_compositor_pid || compositor.uid != getuid ())
    { finish ("private-compositor-identity-mismatch"); return; }
  window = gtk_application_window_new (app);
  g_object_add_weak_pointer (G_OBJECT (window), (gpointer *) &window);
  gtk_window_set_title (GTK_WINDOW (window), "Private GTK colour-owner fixture");
  gtk_window_set_default_size (GTK_WINDOW (window), 320, 240);
  area = gtk_drawing_area_new ();
  g_object_add_weak_pointer (G_OBJECT (area), (gpointer *) &area);
  gtk_drawing_area_set_draw_func (GTK_DRAWING_AREA (area), paint, NULL, NULL);
  gtk_window_set_child (GTK_WINDOW (window), area);
  gtk_window_present (GTK_WINDOW (window));
  GdkFrameClock *clock = gtk_widget_get_frame_clock (window);
  observe_clock (clock);
  g_timeout_add (100, tick, NULL);
}

int
main (int argc, char **argv)
{
  const char *runtime = g_getenv ("XDG_RUNTIME_DIR"), *display = g_getenv ("WAYLAND_DISPLAY");
  struct stat st;
  if (argc != 4 || !runtime || strcmp (runtime, argv[1]) || !display || strchr (display, '/') ||
      g_getenv ("GSK_RENDERER") || g_getenv ("GDK_DEBUG") || g_getenv ("WAYLAND_SOCKET") || g_getenv ("DISPLAY"))
    {
      fprintf (stderr, "Usage: scene EXACT_PRIVATE_RUNTIME EXPECTED_MUTTER_PID FRESH_RECEIPT; default renderer only\n");
      return 2;
    }
  char *end = NULL;
  expected_compositor_pid = g_ascii_strtoll (argv[2], &end, 10);
  if (!end || *end || expected_compositor_pid <= 0 || expected_compositor_pid > G_MAXINT)
    return 2;
  expected_socket = g_build_filename (runtime, display, NULL);
  gboolean owned = stat (runtime, &st) == 0 && S_ISDIR (st.st_mode) && st.st_uid == getuid () &&
                   stat (expected_socket, &st) == 0 && S_ISSOCK (st.st_mode) && st.st_uid == getuid ();
  if (!owned)
    return 2; /* External recipe must additionally prove this is the private compositor PID/socket. */
  int fd = open (argv[3], O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
  if (fd < 0)
    return 2;
  receipt = fdopen (fd, "w");
  if (!receipt)
    { close (fd); return 2; }
  started = g_get_monotonic_time ();
  application = gtk_application_new ("org.example.PrivateColourOwnerFixture", G_APPLICATION_NON_UNIQUE);
  g_signal_connect (application, "activate", G_CALLBACK (activate), NULL);
  int status = g_application_run (G_APPLICATION (application), 0, NULL);
  if (!written)
    finish ("application-exited-without-completion");
  g_object_unref (application);
  fclose (receipt);
  g_free (expected_socket);
  return status ? status : (scene_complete ? 0 : 1);
}
