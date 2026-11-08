/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <gtk/gtk.h>
#include <gdk/wayland/gdkwayland.h>
#include <glib-unix.h>
#include <signal.h>
#include <math.h>
#include <stdio.h>
#include <unistd.h>

static GtkWindow *window;
static GtkWidget *pattern;
static GdkTexture *texture;
static GdkWaylandHdrRendering *lease;
static GMainLoop *loop;
static guint serial;
static gboolean ready_reported;
typedef struct { GtkWidget parent; } Pattern;
typedef struct { GtkWidgetClass parent; } PatternClass;
G_DEFINE_TYPE(Pattern, pattern, GTK_TYPE_WIDGET)
static void snapshot(GtkWidget *self, GtkSnapshot *s) {
  graphene_rect_t bounds=GRAPHENE_RECT_INIT(0,0,gtk_widget_get_width(self),gtk_widget_get_height(self));
  gtk_snapshot_append_texture(s,texture,&bounds);
  GdkRGBA white={1,1,1,1};graphene_rect_t control=GRAPHENE_RECT_INIT(0,0,40,40);
  gtk_snapshot_append_color(s,&white,&control);
  printf("SNAPSHOT serial=%u texture=%p width=%d height=%d time=%ld\n",serial,(void*)texture,gtk_widget_get_width(self),gtk_widget_get_height(self),(long)g_get_monotonic_time());fflush(stdout);
}
static void pattern_class_init(PatternClass *c){GTK_WIDGET_CLASS(c)->snapshot=snapshot;}
static void pattern_init(Pattern *p){(void)p;}
static void set_texture(double nits) {
  double p=pow(nits/10000.,2610./16384.);
  double code=nits<=0?0:pow((3424./4096.+2413./128.*p)/(1+2392./128.*p),2523./32.);
  guint16 pixel[4]={(guint16)llround(code*65535),(guint16)llround(code*65535),(guint16)llround(code*65535),65535};
  GBytes *bytes=g_bytes_new(pixel,sizeof pixel);GdkMemoryTextureBuilder *b=gdk_memory_texture_builder_new();
  gdk_memory_texture_builder_set_width(b,1);gdk_memory_texture_builder_set_height(b,1);gdk_memory_texture_builder_set_stride(b,8);
  gdk_memory_texture_builder_set_format(b,GDK_MEMORY_R16G16B16A16_PREMULTIPLIED);gdk_memory_texture_builder_set_bytes(b,bytes);
  gdk_memory_texture_builder_set_color_state(b,gdk_color_state_get_rec2100_pq());
  GdkTexture *next=gdk_memory_texture_builder_build(b);g_object_unref(b);g_bytes_unref(bytes);
  g_clear_object(&texture);texture=next;
  printf("SCENE serial=%u nits=%g code=%u texture=%p time=%ld\n",serial,nits,pixel[0],(void*)texture,(long)g_get_monotonic_time());fflush(stdout);
}
static gboolean change(gpointer unused) {
  (void)unused;
  static const double levels[]={400,0,.001,.01,.1,1,10,100,400};
  serial++;set_texture(levels[serial % G_N_ELEMENTS(levels)]);
  if(g_getenv("PROBE_GEOMETRY"))gtk_window_set_default_size(window,serial%2?320:640,serial%2?180:360);
  gtk_widget_queue_draw(pattern);return G_SOURCE_CONTINUE;
}
static void changed(GdkWaylandHdrRendering *request,gpointer unused) {
  (void)unused;GdkWaylandHdrRenderState s;
  if(gdk_wayland_hdr_rendering_get_state(request,&s)&&!ready_reported){
    ready_reported=TRUE;
    printf("READY pid=%ld renderer=%s bits=%u/%u/%u float=%d generation=%lu reference=%g\n",(long)getpid(),G_OBJECT_TYPE_NAME(gtk_native_get_renderer(GTK_NATIVE(window))),s.red_bits,s.green_bits,s.blue_bits,s.floating_point,(unsigned long)s.generation,s.reference_luminance);fflush(stdout);
  }
}
static gboolean acquire(gpointer unused) {
  (void)unused;lease=gdk_wayland_surface_request_hdr_rendering(gtk_native_get_surface(GTK_NATIVE(window)));
  g_signal_connect(lease,"changed",G_CALLBACK(changed),NULL);gtk_widget_queue_draw(pattern);return G_SOURCE_REMOVE;
}
static void painted(GdkFrameClock *clock,gpointer unused){
 static gboolean requested;
 if(!requested){requested=TRUE;printf("LATE_LEASE_AFTER_FIRST_PAINT\n");fflush(stdout);g_idle_add(acquire,NULL);}
 (void)unused;printf("FRAME serial=%u counter=%ld time=%ld\n",serial,(long)gdk_frame_clock_get_frame_counter(clock),(long)g_get_monotonic_time());fflush(stdout);}
static gboolean finish(gpointer unused){(void)unused;g_main_loop_quit(loop);return G_SOURCE_REMOVE;}
int main(void) {
 gtk_init();set_texture(400);window=GTK_WINDOW(gtk_window_new());gtk_window_set_decorated(window,FALSE);gtk_window_set_default_size(window,640,360);
 pattern=g_object_new(pattern_get_type(),NULL);gtk_window_set_child(window,pattern);gtk_window_present(window);
 g_signal_connect(gtk_widget_get_frame_clock(GTK_WIDGET(window)),"after-paint",G_CALLBACK(painted),NULL);
 g_unix_signal_add(SIGUSR1,change,NULL);g_unix_signal_add(SIGUSR2,finish,NULL);g_timeout_add_seconds(90,finish,NULL);
 loop=g_main_loop_new(NULL,FALSE);g_main_loop_run(loop);g_clear_object(&lease);gtk_window_destroy(window);g_clear_object(&texture);g_main_loop_unref(loop);return 0;
}
