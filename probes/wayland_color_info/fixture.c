#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <wayland-server.h>
#include "color-management-server.h"

struct fixture { struct wl_display *display; struct wl_global *output; const char *scenario; unsigned version; int icc_write; };
static void destroy(struct wl_client *client, struct wl_resource *resource) { (void)client; wl_resource_destroy(resource); }
static const struct wl_output_interface output_impl={.release=destroy};
static void bind_output(struct wl_client *client, void *data, uint32_t version, uint32_t id) {
    (void)data;
    struct wl_resource *r=wl_resource_create(client,&wl_output_interface,version,id);
    wl_resource_set_implementation(r,&output_impl,data,NULL);
    wl_output_send_geometry(r,0,0,100,100,0,"PRIVATE-MAKE","PRIVATE-MODEL",0);
    wl_output_send_mode(r,WL_OUTPUT_MODE_CURRENT,192,108,24000);
    if (version>=2) wl_output_send_done(r);
}
static int check_icc(void *data) {
    struct fixture *f=data;
    struct pollfd p={.fd=f->icc_write,.events=POLLOUT};
    if (poll(&p,1,0)>=0 && (p.revents&POLLERR)) { puts("ICC_READ_END_CLOSED"); fflush(stdout); }
    close(f->icc_write); f->icc_write=-1;
    return 0;
}
static void information(struct wl_client *client, struct wl_resource *description, uint32_t id) {
    struct fixture *f=wl_resource_get_user_data(description);
    struct wl_resource *r=wl_resource_create(client,&wp_image_description_info_v1_interface,
        wl_resource_get_version(description),id);
    if (!strcmp(f->scenario,"icc") || !strcmp(f->scenario,"icc-hang")) {
        int p[2];
        if (pipe(p)<0) { wl_client_post_no_memory(client); return; }
        wp_image_description_info_v1_send_icc_file(r,p[0],123);
        close(p[0]);
        f->icc_write=p[1];
        struct wl_event_source *timer=wl_event_loop_add_timer(wl_display_get_event_loop(f->display),check_icc,f);
        wl_event_source_timer_update(timer,200);
        if (!strcmp(f->scenario,"icc-hang")) return;
    } else {
        wp_image_description_info_v1_send_primaries(r,640000,330000,300000,600000,150000,60000,312700,329000);
        wp_image_description_info_v1_send_primaries_named(r,1);
        wp_image_description_info_v1_send_tf_named(r,9);
        wp_image_description_info_v1_send_tf_power(r,22000);
        wp_image_description_info_v1_send_luminances(r,500,1000,203);
        if (!strcmp(f->scenario,"duplicate")) wp_image_description_info_v1_send_luminances(r,0,999,200);
        wp_image_description_info_v1_send_target_primaries(r,680000,320000,265000,690000,150000,60000,312700,329000);
        if (strcmp(f->scenario,"incomplete")) wp_image_description_info_v1_send_target_luminance(r,100,616);
        wp_image_description_info_v1_send_target_max_cll(r,600);
        wp_image_description_info_v1_send_target_max_fall(r,300);

    }
    if (!strcmp(f->scenario,"missing-done")) return;
    wp_image_description_info_v1_send_done(r);
    wl_resource_destroy(r);
}
static const struct wp_image_description_v1_interface description_impl={.destroy=destroy,.get_information=information};
static void get_description(struct wl_client *client, struct wl_resource *color, uint32_t id) {
    struct fixture *f=wl_resource_get_user_data(color);
    struct wl_resource *r=wl_resource_create(client,&wp_image_description_v1_interface,wl_resource_get_version(color),id);
    wl_resource_set_implementation(r,&description_impl,f,NULL);
    if (!strcmp(f->scenario,"hang")) return;
    if (!strcmp(f->scenario,"disconnect")) { wl_client_destroy(client); return; }
    if (!strcmp(f->scenario,"remove")) {
        wl_global_destroy(f->output); f->output=NULL;
        wp_image_description_v1_send_failed(r,1,"PRIVATE-SERVER-ERROR"); return;
    }
    if (!strcmp(f->scenario,"failed")) { wp_image_description_v1_send_failed(r,1,"PRIVATE-SERVER-ERROR"); return; }
    if (wl_resource_get_version(r)>=2) wp_image_description_v1_send_ready2(r,1,1234);
    else wp_image_description_v1_send_ready(r,1234);
    if (!strcmp(f->scenario,"changed")) wp_color_management_output_v1_send_image_description_changed(color);
}
static const struct wp_color_management_output_v1_interface color_impl={.destroy=destroy,.get_image_description=get_description};
static void get_output(struct wl_client *client, struct wl_resource *manager, uint32_t id, struct wl_resource *output) {
    (void)output;
    struct wl_resource *r=wl_resource_create(client,&wp_color_management_output_v1_interface,wl_resource_get_version(manager),id);
    wl_resource_set_implementation(r,&color_impl,wl_resource_get_user_data(manager),NULL);
    wp_color_management_output_v1_send_image_description_changed(r); /* Initial notification must be drained before acquisition. */
}
static const struct wp_color_manager_v1_interface manager_impl={.destroy=destroy,.get_output=get_output};
static void bind_manager(struct wl_client *client, void *data, uint32_t version, uint32_t id) {
    struct wl_resource *r=wl_resource_create(client,&wp_color_manager_v1_interface,version,id);
    wl_resource_set_implementation(r,&manager_impl,data,NULL);
    wp_color_manager_v1_send_supported_primaries_named(r,1);
    wp_color_manager_v1_send_supported_tf_named(r,9);
    wp_color_manager_v1_send_done(r);
}
int main(int argc, char **argv) {
    if (argc!=3) return 2;
    struct fixture f={.scenario=argv[1],.version=(unsigned)strtoul(argv[2],NULL,10),.icc_write=-1};
    if (f.version<1 || f.version>2) return 2;
    f.display=wl_display_create();
    if (!f.display || wl_display_add_socket(f.display,"fixture")) return 2;
    bool manager_first=!strcmp(f.scenario,"manager-first");
    if (manager_first) wl_global_create(f.display,&wp_color_manager_v1_interface,f.version,&f,bind_manager);
    unsigned count=!strcmp(f.scenario,"overflow")?33:1;
    for (unsigned i=0;i<count;i++) f.output=wl_global_create(f.display,&wl_output_interface,
        !strcmp(f.scenario,"output-v1")?1:2,&f,bind_output);
    if (!manager_first && strcmp(f.scenario,"absent")) wl_global_create(f.display,&wp_color_manager_v1_interface,f.version,&f,bind_manager);
    puts("READY"); fflush(stdout);
    wl_display_run(f.display);
    wl_display_destroy_clients(f.display); wl_display_destroy(f.display);
    if (f.icc_write>=0) close(f.icc_write);
    return 0;
}
