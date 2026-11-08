/* Test-only libweston module. Load explicitly in an owned headless compositor.
 * Commands on $XDG_RUNTIME_DIR/physical-target-control: A, B, ABA, D, E, N.
 * No user desktop, installed configuration or display hardware is touched.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <libweston/libweston.h>
#include <libweston/colorimetry.h>
#include <libweston/windowed-output-api.h>

struct fixture {
    struct weston_compositor *compositor;
    struct weston_output *output;
    struct weston_color_profile *a, *b;
    struct wl_event_source *input, *timer;
    struct wl_listener destroy, output_destroy;
    char *fifo;
    int fd;
    unsigned serial;
    bool second_created;
    char pending[128];
    size_t used;
};

static float setting(const char *name, float fallback)
{
    const char *text = getenv(name);
    char *end;
    float value;
    if (!text) return fallback;
    value = strtof(text, &end);
    return *end || !isfinite(value) || value < 0 ? NAN : value;
}

static struct weston_color_profile *make_b(struct fixture *s)
{
    struct weston_color_profile_param_builder *b;
    struct weston_color_gamut gamut = {0};
    const char *xy = getenv("DV_TEST_B_XY");
    if (xy) {
        char extra;
        if (sscanf(xy, "%f,%f,%f,%f,%f,%f,%f,%f%c",
                   &gamut.primary[0].x, &gamut.primary[0].y,
                   &gamut.primary[1].x, &gamut.primary[1].y,
                   &gamut.primary[2].x, &gamut.primary[2].y,
                   &gamut.white_point.x, &gamut.white_point.y, &extra) != 8)
            return NULL;
    }
    enum weston_color_profile_param_builder_error error;
    char *message = NULL;
    struct weston_color_profile *profile;
    float ref = setting("DV_TEST_B_REFERENCE", 71);
    float black = setting("DV_TEST_B_BLACK", .0002f);
    float peak = setting("DV_TEST_B_PEAK", 308);
    float encoding_min = setting("DV_TEST_B_ENCODING_MIN", .0025f);
    b = weston_color_profile_param_builder_create(s->compositor);
    if (!b) return NULL;
    weston_color_profile_param_builder_set_primaries_named(b, WESTON_PRIMARIES_CICP_BT2020);
    weston_color_profile_param_builder_set_tf_named(b, WESTON_TF_ST2084_PQ);
    weston_color_profile_param_builder_set_primary_luminance(b, ref, encoding_min, 10000);
    if (xy)
        weston_color_profile_param_builder_set_target_primaries(b, &gamut);
    else
        weston_color_profile_param_builder_set_target_primaries_named(b, WESTON_PRIMARIES_CICP_DISPLAY_P3);
    weston_color_profile_param_builder_set_target_luminance(b, black, peak);
    /* create_color_profile consumes builder, including on failure. */
    profile = weston_color_profile_param_builder_create_color_profile(b, "physical-test-B", &error, &message);
    if (!profile) weston_log("target-fixture: profile-B failed %d: %s\n", error, message ? message : "unknown");
    free(message);
    return profile;
}

static void output_destroyed(struct wl_listener *listener, void *data)
{
    struct fixture *s = wl_container_of(listener, s, output_destroy);
    (void)data;
    wl_list_remove(&s->output_destroy.link);
    wl_list_init(&s->output_destroy.link);
    s->output = NULL;
}

static struct weston_output *find_output(struct fixture *s)
{
    struct weston_output *out;
    wl_list_for_each(out, &s->compositor->output_list, link)
        if (!strcmp(out->name, "headless")) return out;
    wl_list_for_each(out, &s->compositor->pending_output_list, link)
        if (!strcmp(out->name, "headless")) return out;
    return NULL;
}

static void track_output(struct fixture *s, struct weston_output *out)
{
    if (s->output == out) return;
    if (!wl_list_empty(&s->output_destroy.link)) wl_list_remove(&s->output_destroy.link);
    wl_list_init(&s->output_destroy.link);
    s->output = out;
    if (out) {
        s->output_destroy.notify = output_destroyed;
        wl_signal_add(&out->destroy_signal, &s->output_destroy);
    }
}

static int initialize(void *data)
{
    struct fixture *s = data;
    struct weston_output *out;
    wl_list_for_each(out, &s->compositor->output_list, link) {
        /* Refuse to attach to a real display even if loaded accidentally. */
        if (strcmp(out->name, "headless") != 0) continue;
        track_output(s, out);
        s->a = weston_color_profile_ref(out->color_profile);
        s->b = make_b(s);
        if (!s->b) return 0;
        weston_log("target-fixture: READY fifo=%s; A=existing; B=controlled; serial=0\n", s->fifo);
        return 0;
    }
    wl_event_source_timer_update(s->timer, 50);
    return 0;
}

static void select_profile(struct fixture *s, bool b)
{
    track_output(s, find_output(s));
    if (!s->output || !s->a || !s->b) return;
    bool ok = weston_output_set_color_profile(s->output, b ? s->b : s->a);
    if (ok && s->output->enabled) weston_output_schedule_repaint(s->output);
    weston_log("target-fixture: PROFILE %c serial=%u ok=%d enabled=%d\n",
               b ? 'B' : 'A', ++s->serial, ok, s->output->enabled);
}

static void command(struct fixture *s, const char *text)
{
    track_output(s, find_output(s));
    if (!strcmp(text,"A")) select_profile(s, false);
    else if (!strcmp(text,"B")) select_profile(s, true);
    else if (!strcmp(text,"ABA")) {
        select_profile(s, false); select_profile(s, true); select_profile(s, false);
    } else if (!strcmp(text,"D") && s->output) {
        if (s->output->enabled) weston_output_disable(s->output);
        weston_log("target-fixture: DISABLED serial=%u\n", ++s->serial);
    } else if (!strcmp(text,"E") && s->output) {
        int ret = s->output->enabled ? 0 : weston_output_enable(s->output);
        weston_log("target-fixture: ENABLED serial=%u result=%d\n", ++s->serial, ret);
    } else if (!strcmp(text,"N") && !s->second_created) {
        const struct weston_windowed_output_api *api = weston_windowed_output_get_api(s->compositor, WESTON_WINDOWED_OUTPUT_HEADLESS);
        int ret = api ? api->create_head(s->compositor->primary_backend, "target-second") : -1;
        s->second_created = ret == 0;
        weston_log("target-fixture: SECOND serial=%u result=%d\n", ++s->serial, ret);
    } else weston_log("target-fixture: refused command %s\n", text);
}

static int input(int fd, uint32_t mask, void *data)
{
    struct fixture *s = data;
    char bytes[128];
    ssize_t count;
    (void)mask;
    while ((count = read(fd, bytes, sizeof(bytes))) > 0) {
        for (ssize_t i = 0; i < count; i++) {
            if (bytes[i] == '\n') {
                s->pending[s->used] = 0;
                command(s, s->pending); s->used = 0;
            } else if (s->used + 1 < sizeof(s->pending)) s->pending[s->used++] = bytes[i];
            else s->used = 0;
        }
    }
    return 0;
}

static void destroy(struct wl_listener *listener, void *data)
{
    struct fixture *s = wl_container_of(listener, s, destroy);
    (void)data;
    if (s->input) wl_event_source_remove(s->input);
    if (s->timer) wl_event_source_remove(s->timer);
    wl_list_remove(&s->destroy.link);
    if (!wl_list_empty(&s->output_destroy.link)) wl_list_remove(&s->output_destroy.link);
    if (s->a) weston_color_profile_unref(s->a);
    if (s->b) weston_color_profile_unref(s->b);
    if (s->fd >= 0) close(s->fd);
    if (s->fifo) unlink(s->fifo);
    free(s->fifo); free(s);
}

WL_EXPORT int wet_module_init(struct weston_compositor *compositor, int *argc, char *argv[])
{
    struct fixture *s;
    struct wl_event_loop *loop;
    const char *runtime = getenv("XDG_RUNTIME_DIR");
    (void)argc; (void)argv;
    if (!runtime || runtime[0] != '/') return -1;
    s = calloc(1, sizeof(*s));
    if (!s) return -1;
    s->fd = -1; s->compositor = compositor;
    wl_list_init(&s->output_destroy.link);
    if (asprintf(&s->fifo, "%s/physical-target-control", runtime) < 0) { free(s); return -1; }
    if (mkfifo(s->fifo, 0600) < 0) { free(s->fifo); free(s); return -1; }
    s->fd = open(s->fifo, O_RDWR | O_NONBLOCK | O_CLOEXEC);
    if (s->fd < 0) { unlink(s->fifo); free(s->fifo); free(s); return -1; }
    loop = wl_display_get_event_loop(compositor->wl_display);
    s->input = wl_event_loop_add_fd(loop, s->fd, WL_EVENT_READABLE, input, s);
    s->timer = wl_event_loop_add_timer(loop, initialize, s);
    if (!s->input || !s->timer) {
        if (s->input) wl_event_source_remove(s->input);
        if (s->timer) wl_event_source_remove(s->timer);
        close(s->fd); unlink(s->fifo); free(s->fifo); free(s); return -1;
    }
    weston_compositor_add_destroy_listener_once(compositor, &s->destroy, destroy);
    wl_event_source_timer_update(s->timer, 1);
    return 0;
}
