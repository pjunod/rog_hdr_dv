#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <poll.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>
#include "color-management-client.h"

#define OUTPUT_CAP 32
#define EVENT_CAP 8192
#define BYTE_CAP (1024u * 1024u)
#define DEADLINE_MS 5000
/* All report strings are compile-time allowlisted; no server strings are stored. */
enum field_id { PRIMARIES, PRIMARIES_NAMED, TF_POWER, TF_NAMED, LUMINANCES,
                TARGET_PRIMARIES, TARGET_LUMINANCE, MAX_CLL, MAX_FALL, ICC, FIELD_COUNT };
static const char *const field_names[] = { "primaries", "primaries_named", "tf_power", "tf_named",
    "luminances", "target_primaries", "target_luminance", "target_max_cll", "target_max_fall", "icc_size" };
struct field { bool present; unsigned count; int64_t raw[8]; };
struct app;
struct output {
    struct app *app;
    uint32_t global, version;
    struct wl_output *proxy;
    struct wp_color_management_output_v1 *color;
    struct wp_image_description_v1 *description;
    struct wp_image_description_info_v1 *info;
    struct field fields[FIELD_COUNT];
    uint32_t identity_hi, identity_lo, failure_cause;
    bool removed, output_done, ready, info_done, malformed, failed, changed;
};
struct app {
    struct wl_display *display;
    struct wl_registry *registry;
    struct wp_color_manager_v1 *manager;
    struct wl_callback *sync;
    uint32_t manager_global, manager_version;
    struct output outputs[OUTPUT_CAP];
    unsigned count, events;
    size_t bytes;
    int64_t deadline;
    bool manager_done, manager_removed, discovery_done, acquiring, sync_done, unstable;
    const char *error;
};
static int64_t now_ms(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts)) return -1;
    return (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}
static bool event(struct app *a, size_t bytes) {
    if (++a->events > EVENT_CAP || bytes > BYTE_CAP - a->bytes) a->error = "event_cap";
    else a->bytes += bytes;
    return !a->error;
}
static void ignored_string(struct app *a, const char *value) {
    size_t n = value ? strnlen(value, BYTE_CAP + 1u) : 0;
    event(a, n + 1);
}
static void save(struct output *o, enum field_id id, unsigned n, const int64_t *values) {
    struct field *f = &o->fields[id];
    event(o->app, n * 4u + 8u);
    /* The protocol promises exactly one matching event. Even equal duplicates are malformed. */
    if (f->present || o->info_done) { o->malformed = true; return; }
    f->present = true; f->count = n;
    memcpy(f->raw, values, n * sizeof(*values));
}
/* Report only limited, explicit semantic checks, preserving unknown future enums. */
static const char *tf_pair_status(struct output *o) {
    struct field *named=&o->fields[TF_NAMED], *power=&o->fields[TF_POWER];
    if (!named->present || !power->present) return "single_representation";
    int64_t expected=0;
    switch (named->raw[0]) {
    case WP_COLOR_MANAGER_V1_TRANSFER_FUNCTION_GAMMA22: expected=22000; break;
    case WP_COLOR_MANAGER_V1_TRANSFER_FUNCTION_GAMMA28: expected=28000; break;
    case WP_COLOR_MANAGER_V1_TRANSFER_FUNCTION_EXT_LINEAR: expected=10000; break;
    case WP_COLOR_MANAGER_V1_TRANSFER_FUNCTION_ST240:
    case WP_COLOR_MANAGER_V1_TRANSFER_FUNCTION_LOG_100:
    case WP_COLOR_MANAGER_V1_TRANSFER_FUNCTION_LOG_316:
    case WP_COLOR_MANAGER_V1_TRANSFER_FUNCTION_XVYCC:
    case WP_COLOR_MANAGER_V1_TRANSFER_FUNCTION_SRGB:
    case WP_COLOR_MANAGER_V1_TRANSFER_FUNCTION_EXT_SRGB:
    case WP_COLOR_MANAGER_V1_TRANSFER_FUNCTION_ST2084_PQ:
    case WP_COLOR_MANAGER_V1_TRANSFER_FUNCTION_HLG:
    case WP_COLOR_MANAGER_V1_TRANSFER_FUNCTION_COMPOUND_POWER_2_4:
        return "contradictory";
    default: return "unverified";
    }
    return power->raw[0]==expected?"consistent":"contradictory";
}
static void info_done(void *data, struct wp_image_description_info_v1 *proxy) {
    struct output *o = data;
    event(o->app, 8);
    if (o->info_done) o->malformed = true;
    o->info_done = true;
    wp_image_description_info_v1_destroy(proxy); /* local destroy: done is a server destructor */
    o->info = NULL;
    if (!strcmp(tf_pair_status(o),"contradictory") ||
        (o->fields[TF_NAMED].present && !o->fields[TF_NAMED].raw[0])) o->malformed=true;
    bool parametric=false;
    for (unsigned f=0;f<ICC;f++) parametric |= o->fields[f].present;
    if ((!o->fields[ICC].present || parametric) && !(o->fields[PRIMARIES].present &&
        (o->fields[TF_POWER].present || o->fields[TF_NAMED].present) &&
        o->fields[LUMINANCES].present && o->fields[TARGET_PRIMARIES].present &&
        o->fields[TARGET_LUMINANCE].present)) o->malformed = true;
}
static void icc_file(void *data, struct wp_image_description_info_v1 *proxy, int32_t fd, uint32_t size) {
    (void)proxy;
    struct output *o = data;
    if (fd >= 0) close(fd); /* Ownership ends immediately; never inspect profile bytes. */
    else o->malformed = true;
    int64_t raw[] = {size}; save(o, ICC, 1, raw);
}
#define COORD_HANDLER(name, id) \
static void name(void *data, struct wp_image_description_info_v1 *proxy, \
int32_t rx, int32_t ry, int32_t gx, int32_t gy, int32_t bx, int32_t by, int32_t wx, int32_t wy) { \
(void)proxy; int64_t raw[] = {rx,ry,gx,gy,bx,by,wx,wy}; save(data,id,8,raw); }
COORD_HANDLER(primaries, PRIMARIES)
COORD_HANDLER(target_primaries, TARGET_PRIMARIES)
#define UINT_HANDLER(name, id) \
static void name(void *data, struct wp_image_description_info_v1 *proxy, uint32_t value) { \
(void)proxy; int64_t raw[] = {value}; save(data,id,1,raw); }
UINT_HANDLER(primaries_named, PRIMARIES_NAMED)
UINT_HANDLER(tf_power, TF_POWER)
UINT_HANDLER(tf_named, TF_NAMED)
UINT_HANDLER(max_cll, MAX_CLL)
UINT_HANDLER(max_fall, MAX_FALL)
static void luminances(void *data, struct wp_image_description_info_v1 *proxy, uint32_t min, uint32_t max, uint32_t reference) {
    (void)proxy; int64_t raw[] = {min,max,reference}; save(data,LUMINANCES,3,raw);
}
static void target_luminance(void *data, struct wp_image_description_info_v1 *proxy, uint32_t min, uint32_t max) {
    (void)proxy; int64_t raw[] = {min,max}; save(data,TARGET_LUMINANCE,2,raw);
}
static const struct wp_image_description_info_v1_listener info_listener = {
    .done=info_done, .icc_file=icc_file, .primaries=primaries, .primaries_named=primaries_named,
    .tf_power=tf_power, .tf_named=tf_named, .luminances=luminances, .target_primaries=target_primaries,
    .target_luminance=target_luminance, .target_max_cll=max_cll, .target_max_fall=max_fall
};
static void ready_common(struct output *o, uint32_t hi, uint32_t lo, uint32_t version) {
    event(o->app, 16);
    if (o->ready || o->failed || (!hi && !lo) || o->app->manager_version != version) {
        o->malformed = true; return;
    }
    o->ready = true; o->identity_hi = hi; o->identity_lo = lo;
    if (o->removed || o->app->manager_removed || o->app->error) return;
    o->info = wp_image_description_v1_get_information(o->description);
    if (!o->info || wp_image_description_info_v1_add_listener(o->info,&info_listener,o)) o->app->error="allocation";
}
static void ready(void *data, struct wp_image_description_v1 *proxy, uint32_t identity) {
    (void)proxy; ready_common(data,0,identity,1);
}
static void ready2(void *data, struct wp_image_description_v1 *proxy, uint32_t hi, uint32_t lo) {
    (void)proxy; ready_common(data,hi,lo,2);
}
static void failed(void *data, struct wp_image_description_v1 *proxy, uint32_t cause, const char *message) {
    (void)proxy; struct output *o=data;
    ignored_string(o->app,message); event(o->app,8);
    if (o->ready || o->failed) o->malformed=true;
    o->failed=true; o->failure_cause=cause;
}
static const struct wp_image_description_v1_listener description_listener = { .failed=failed, .ready=ready, .ready2=ready2 };
static void changed(void *data, struct wp_color_management_output_v1 *proxy) {
    (void)proxy; struct output *o=data; event(o->app,8);
    if (o->app->acquiring) { o->changed=true; o->app->unstable=true; }
}
static const struct wp_color_management_output_v1_listener color_listener = { .image_description_changed=changed };
static void geometry(void *data, struct wl_output *proxy, int32_t x, int32_t y, int32_t w, int32_t h,
    int32_t subpixel, const char *make, const char *model, int32_t transform) {
    (void)proxy;(void)x;(void)y;(void)w;(void)h;(void)subpixel;(void)transform;
    struct output *o=data; event(o->app,32); ignored_string(o->app,make); ignored_string(o->app,model);
}
static void mode(void *data, struct wl_output *proxy, uint32_t flags, int32_t w, int32_t h, int32_t refresh) {
    (void)proxy;(void)flags;(void)w;(void)h;(void)refresh; event(((struct output *)data)->app,24);
}
static void output_done(void *data, struct wl_output *proxy) {
    (void)proxy; struct output *o=data; event(o->app,8); o->output_done=true;
}
static void scale(void *data, struct wl_output *proxy, int32_t value) {
    (void)proxy;(void)value; event(((struct output *)data)->app,12);
}
static const struct wl_output_listener output_listener = { .geometry=geometry,.mode=mode,.done=output_done,.scale=scale };
static void capability(void *data, struct wp_color_manager_v1 *proxy, uint32_t value) {
    (void)proxy;(void)value; event(data,12);
}
static void manager_done(void *data, struct wp_color_manager_v1 *proxy) {
    (void)proxy; struct app *a=data; event(a,8);
    if (a->manager_done) a->error="malformed_manager";
    a->manager_done=true;
}
static const struct wp_color_manager_v1_listener manager_listener = { .supported_intent=capability,
    .supported_feature=capability,.supported_tf_named=capability,.supported_primaries_named=capability,.done=manager_done };
static void global(void *data, struct wl_registry *registry, uint32_t name, const char *interface, uint32_t version) {
    struct app *a=data; ignored_string(a,interface); event(a,16);
    bool relevant=!strcmp(interface,"wl_output") || !strcmp(interface,"wp_color_manager_v1");
    if (a->discovery_done && relevant) { a->unstable=true; return; }
    if (a->error) return;
    if (!strcmp(interface,"wl_output")) {
        if (a->count==OUTPUT_CAP) { a->error="output_cap"; return; }
        struct output *o=&a->outputs[a->count++]; o->app=a; o->global=name;
        o->version=version<2?version:2;
        if (!o->version) { a->error="unsupported_output"; return; }
        o->proxy=wl_registry_bind(registry,name,&wl_output_interface,o->version);
        if (!o->proxy || wl_output_add_listener(o->proxy,&output_listener,o)) a->error="allocation";
    } else if (!strcmp(interface,"wp_color_manager_v1")) {
        if (a->manager) { a->error="manager_cap"; return; }
        a->manager_version=version<2?version:2; a->manager_global=name;
        if (!a->manager_version) { a->error="unsupported_protocol"; return; }
        a->manager=wl_registry_bind(registry,name,&wp_color_manager_v1_interface,a->manager_version);
        if (!a->manager || wp_color_manager_v1_add_listener(a->manager,&manager_listener,a)) a->error="allocation";
    }
}
static void removed(void *data, struct wl_registry *registry, uint32_t name) {
    (void)registry; struct app *a=data; event(a,12);
    if (name==a->manager_global && a->manager) {
        a->manager_removed=true; a->unstable=true; if (!a->error) a->error="manager_removed";
    }
    for (unsigned i=0;i<a->count;i++) if (a->outputs[i].global==name) {
        a->outputs[i].removed=true; a->unstable=true;
    }
}
static const struct wl_registry_listener registry_listener = { .global=global,.global_remove=removed };
static void synced(void *data, struct wl_callback *callback, uint32_t serial) {
    (void)serial; struct app *a=data; event(a,12); a->sync_done=true;
    wl_callback_destroy(callback); a->sync=NULL;
}
static const struct wl_callback_listener sync_listener = { .done=synced };
static int remaining(struct app *a) {
    int64_t now=now_ms();
    if (now<0) { a->error="clock"; return 0; }
    int64_t delta=a->deadline-now;
    if (delta<=0) { a->error="deadline"; return 0; }
    return delta>INT_MAX?INT_MAX:(int)delta;
}
/* Exactly one prepared read is either consumed or cancelled on every path. */
static bool pump(struct app *a) {
    while (wl_display_prepare_read(a->display)!=0) {
        if (wl_display_dispatch_pending(a->display)<0) { a->error="disconnect"; return false; }
        if (a->error || !remaining(a)) return false;
    }
    int timeout=remaining(a);
    if (!timeout || a->error) { wl_display_cancel_read(a->display); return false; }
    short wanted=POLLIN;
    if (wl_display_flush(a->display)<0) {
        if (errno==EAGAIN) wanted|=POLLOUT;
        else { wl_display_cancel_read(a->display); a->error="disconnect"; return false; }
    }
    struct pollfd p={.fd=wl_display_get_fd(a->display),.events=wanted};
    int result=poll(&p,1,timeout);
    if (result<0) {
        wl_display_cancel_read(a->display);
        if (errno==EINTR) return true;
        a->error="transport"; return false;
    }
    if (!result) { wl_display_cancel_read(a->display); a->error="deadline"; return false; }
    if (p.revents&POLLIN) {
        if (wl_display_read_events(a->display)<0) { a->error="disconnect"; return false; }
    } else wl_display_cancel_read(a->display);
    if (p.revents&(POLLERR|POLLHUP|POLLNVAL)) { a->error="disconnect"; return false; }
    if (wl_display_dispatch_pending(a->display)<0) { a->error="disconnect"; return false; }
    return !a->error;
}
static bool barrier(struct app *a) {
    a->sync_done=false; a->sync=wl_display_sync(a->display);
    if (!a->sync || wl_callback_add_listener(a->sync,&sync_listener,a)) { a->error="allocation"; return false; }
    while (!a->sync_done && !a->error) if (!pump(a)) break;
    return a->sync_done && !a->error;
}
/* Avoid a blocking Unix connect extending the total acquisition deadline. */
static struct wl_display *connect_display(struct app *a) {
    const char *inherited=getenv("WAYLAND_SOCKET");
    int fd=-1;
    if (inherited) {
        char *end=NULL; errno=0; long value=strtol(inherited,&end,10);
        if (errno || !*inherited || *end || value<0 || value>INT_MAX) { a->error="connection"; return NULL; }
        fd=fcntl((int)value,F_DUPFD_CLOEXEC,3);
    } else {
        const char *name=getenv("WAYLAND_DISPLAY"), *runtime=getenv("XDG_RUNTIME_DIR");
        if (!name) name="wayland-0";
        struct sockaddr_un address={.sun_family=AF_UNIX};
        int n=name[0]=='/' ? snprintf(address.sun_path,sizeof(address.sun_path),"%s",name) :
            (runtime?snprintf(address.sun_path,sizeof(address.sun_path),"%s/%s",runtime,name):-1);
        if (n<0 || (size_t)n>=sizeof(address.sun_path)) { a->error="connection"; return NULL; }
        fd=socket(AF_UNIX,SOCK_STREAM|SOCK_NONBLOCK|SOCK_CLOEXEC,0);
        if (fd>=0 && connect(fd,(struct sockaddr *)&address,sizeof(address))<0) {
            if (errno!=EINPROGRESS && errno!=EAGAIN) { close(fd); fd=-1; }
            else {
                struct pollfd p={.fd=fd,.events=POLLOUT};
                int result;
                do { result=poll(&p,1,remaining(a)); } while (result<0 && errno==EINTR && !a->error);
                int error=0; socklen_t length=sizeof(error);
                if (result<=0 || getsockopt(fd,SOL_SOCKET,SO_ERROR,&error,&length)<0 || error) { close(fd); fd=-1; }
            }
        }
    }
    if (fd<0) { if (!a->error) a->error="connection"; return NULL; }
    int flags=fcntl(fd,F_GETFL);
    if (flags<0 || fcntl(fd,F_SETFL,flags|O_NONBLOCK)<0) { close(fd); a->error="connection"; return NULL; }
    struct wl_display *display=wl_display_connect_to_fd(fd);
    /* Pinned libwayland1.26.0 consumes fd on success AND failure. */
    if (!display) a->error="connection";
    return display;
}
static bool finished(struct app *a) {
    for (unsigned i=0;i<a->count;i++) {
        struct output *o=&a->outputs[i];
        if (!o->removed && !o->malformed && !o->failed && !o->info_done) return false;
    }
    return true;
}
static const char *output_status(struct output *o) {
    if (o->removed) return "removed";
    if (o->changed) return "unstable";
    if (o->malformed) return "malformed";
    if (o->failed) return "description_failed";
    if (!o->ready || !o->info_done || (o->version>=2 && !o->output_done)) return "incomplete";
    return "complete";
}
static void report(struct app *a, bool success) {
    printf("{\"schema\":1,\"status\":\"%s\",\"reason\":\"%s\",\"identifier_scope\":\"session_local\",\"semantic_checks\":\"required_fields_and_known_tf_pairs_only\","
        "\"snapshot_consistency\":\"%s\",\"manager_version\":%u,\"manager_done\":%s,\"manager_removed\":%s,"
        "\"limits\":{\"outputs\":32,\"events\":8192,\"event_bytes\":1048576,\"deadline_ms\":5000},"
        "\"scales\":{\"chromaticity\":1000000,\"tf_power\":10000,\"minimum_luminance\":10000,"
        "\"other_luminance\":1},\"luminance_unit\":\"cd/m2\","
        "\"protocol_pin\":\"wayland-protocols1.48\",\"raw_order\":{"
        "\"primaries_and_target_primaries\":[\"red_x\",\"red_y\",\"green_x\",\"green_y\","
        "\"blue_x\",\"blue_y\",\"white_x\",\"white_y\"],"
        "\"luminances\":[\"min\",\"max\",\"reference\"],\"target_luminance\":[\"min\",\"max\"]},\"outputs\":[",
        success?"complete":"incomplete",a->error?a->error:(a->unstable?"unstable":(success?"none":"output_incomplete")),
        a->unstable?"unstable":"bounded_observation",a->manager_version,a->manager_done?"true":"false",a->manager_removed?"true":"false");
    for (unsigned i=0;i<a->count;i++) {
        struct output *o=&a->outputs[i];
        printf("%s{\"ordinal\":%u,\"global\":%u,\"wl_output_version\":%u,\"status\":\"%s\","
            "\"description_identity\":{\"present\":%s,\"hi\":%u,\"lo\":%u},\"information_done\":%s,"
            "\"tf_pair_consistency\":\"%s\",\"failure_cause\":%s",i?",":"",i,o->global,o->version,output_status(o),
            o->ready?"true":"false",o->identity_hi,o->identity_lo,o->info_done?"true":"false",tf_pair_status(o),o->failed?"":"null");
        if (o->failed) printf("%u",o->failure_cause);
        for (unsigned f=0;f<FIELD_COUNT;f++) {
            struct field *field=&o->fields[f];
            printf(",\"%s\":{\"present\":%s,\"raw\":[",field_names[f],field->present?"true":"false");
            for (unsigned k=0;k<field->count;k++) printf("%s%" PRId64,k?",":"",field->raw[k]);
            printf("]}");
        }
        printf("}");
    }
    printf("]}\n");
}
#define LOCAL_DESTROY(proxy) do { if (proxy) wl_proxy_destroy((struct wl_proxy *)(proxy)); } while (0)
static void cleanup(struct app *a) {
    for (unsigned i=0;i<a->count;i++) {
        struct output *o=&a->outputs[i];
        LOCAL_DESTROY(o->info); LOCAL_DESTROY(o->description); LOCAL_DESTROY(o->color); LOCAL_DESTROY(o->proxy);
    }
    LOCAL_DESTROY(a->sync); LOCAL_DESTROY(a->manager); LOCAL_DESTROY(a->registry);
    if (a->display) wl_display_disconnect(a->display);
}
/* libwayland can log raw protocol errors; suppress its process-local logger. */
static void quiet_log(const char *format, va_list args) { (void)format;(void)args; }
int main(int argc, char **argv) {
    (void)argv;
    struct app a={0};
    if (argc!=1) { a.error="arguments"; report(&a,false); return 2; }
    int64_t start=now_ms(); a.deadline=start+DEADLINE_MS;
    if (start<0) a.error="clock";
    wl_log_set_handler_client(quiet_log);
    /* Debug tracing can include private metadata, independently of error logging. */
    if (unsetenv("WAYLAND_DEBUG")) a.error="privacy_environment";
    if (!a.error) a.display=connect_display(&a);
    if (a.display) {
        a.registry=wl_display_get_registry(a.display);
        if (!a.registry || wl_registry_add_listener(a.registry,&registry_listener,&a)) a.error="allocation";
        if (!a.error && barrier(&a)) {
            a.discovery_done=true;
            if (!a.manager) a.error="unsupported_protocol";
            else if (!a.count) a.error="no_outputs";
        }
        if (!a.error && barrier(&a)) {
            if (!a.manager_done) a.error="incomplete_manager";
            if (!a.manager_removed) for (unsigned i=0;i<a.count && !a.error;i++) {
                struct output *o=&a.outputs[i];
                if (o->removed) continue;
                o->color=wp_color_manager_v1_get_output(a.manager,o->proxy);
                if (!o->color || wp_color_management_output_v1_add_listener(o->color,&color_listener,o)) a.error="allocation";
            }
        }
        if (!a.error && barrier(&a)) {
            a.acquiring=true;
            if (!a.manager_removed) for (unsigned i=0;i<a.count && !a.error;i++) {
                struct output *o=&a.outputs[i];
                if (o->removed || !o->color) continue;
                o->description=wp_color_management_output_v1_get_image_description(o->color);
                if (!o->description || wp_image_description_v1_add_listener(o->description,&description_listener,o)) a.error="allocation";
            }
            while (!a.error && !finished(&a)) if (!pump(&a)) break;
            /* Drain already queued changes/removals and bound the end of observation. */
            if (!a.error) barrier(&a);
        }
    }
    bool success=!a.error && !a.unstable && a.manager_done && !a.manager_removed && a.count;
    for (unsigned i=0;i<a.count;i++) if (strcmp(output_status(&a.outputs[i]),"complete")) success=false;
    report(&a,success); cleanup(&a);
    return success?0:1;
}
