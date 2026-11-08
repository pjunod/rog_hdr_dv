/* SPDX-License-Identifier: MIT */
/* Sample one pixel from an already accessible Mutter PipeWire monitor node. */
#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <pipewire/pipewire.h>
#include <spa/param/video/format-utils.h>
#include <spa/pod/builder.h>

struct layout {
    const char *name;
    enum spa_video_format format;
    unsigned int bytes;
    enum spa_video_color_primaries primaries;
    enum spa_video_transfer_function transfer;
};

static const struct layout layouts[] = {
    { "xr30", SPA_VIDEO_FORMAT_xRGB_210LE, 4, SPA_VIDEO_COLOR_PRIMARIES_BT2020, SPA_VIDEO_TRANSFER_SMPTE2084 },
    { "xb30", SPA_VIDEO_FORMAT_xBGR_210LE, 4, SPA_VIDEO_COLOR_PRIMARIES_BT2020, SPA_VIDEO_TRANSFER_SMPTE2084 },
    { "rgba-f16", SPA_VIDEO_FORMAT_RGBA_F16, 8, SPA_VIDEO_COLOR_PRIMARIES_BT2020, SPA_VIDEO_TRANSFER_SMPTE2084 },
    { "bgrx", SPA_VIDEO_FORMAT_BGRx, 4, SPA_VIDEO_COLOR_PRIMARIES_BT709, SPA_VIDEO_TRANSFER_GAMMA22 },
};

struct capture {
    struct pw_main_loop *loop;
    struct pw_stream *stream;
    struct spa_video_info_raw info;
    const struct layout *layout;
    uint32_t x, y;
    int result;
};

static int parse_uint(const char *s, uint32_t *out)
{
    char *end;
    unsigned long value;
    if (!*s || strspn(s, "0123456789") != strlen(s))
        return -1;
    errno = 0;
    value = strtoul(s, &end, 10);
    if (errno || *end || value > UINT32_MAX)
        return -1;
    *out = (uint32_t)value;
    return 0;
}

static float half_to_float(const uint8_t *data)
{
    uint16_t value;
    memcpy(&value, data, sizeof(value));
    unsigned int exponent = (value >> 10) & 31, fraction = value & 1023;
    float magnitude;
    if (!exponent)
        magnitude = ldexpf((float)fraction, -24);
    else if (exponent == 31)
        magnitude = fraction ? NAN : INFINITY;
    else
        magnitude = ldexpf((float)(1024 + fraction), (int)exponent - 25);
    return value & 0x8000 ? -magnitude : magnitude;
}

static void print_pixel(const struct capture *capture, const uint8_t *p)
{
    enum spa_video_format format = capture->layout->format;
    if (format == SPA_VIDEO_FORMAT_RGBA_F16) {
        printf("%.9g %.9g %.9g\n", half_to_float(p), half_to_float(p + 2), half_to_float(p + 4));
    } else if (format == SPA_VIDEO_FORMAT_BGRx) {
        printf("%u %u %u\n", (unsigned)p[2], (unsigned)p[1], (unsigned)p[0]);
    } else {
        uint32_t bits = (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
                        ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
        unsigned int high = (bits >> 20) & 1023, low = bits & 1023;
        printf("%u %u %u\n", format == SPA_VIDEO_FORMAT_xRGB_210LE ? high : low,
               (bits >> 10) & 1023, format == SPA_VIDEO_FORMAT_xRGB_210LE ? low : high);
    }
}

static void on_format(void *data, uint32_t id, const struct spa_pod *param)
{
    struct capture *c = data;
    uint8_t storage[512];
    struct spa_pod_builder builder = SPA_POD_BUILDER_INIT(storage, sizeof(storage));
    if (id != SPA_PARAM_Format || !param)
        return;
    if (spa_format_video_raw_parse(param, &c->info) < 0 ||
        c->info.format != c->layout->format || c->info.color_primaries != c->layout->primaries ||
        c->info.transfer_function != c->layout->transfer ||
        c->x >= c->info.size.width || c->y >= c->info.size.height) {
        fprintf(stderr, "Unexpected format, color encoding, or coordinates outside the stream\n");
        pw_main_loop_quit(c->loop);
        return;
    }
    const struct spa_pod *buffers = spa_pod_builder_add_object(&builder,
        SPA_TYPE_OBJECT_ParamBuffers, SPA_PARAM_Buffers,
        SPA_PARAM_BUFFERS_dataType, SPA_POD_CHOICE_FLAGS_Int(1 << SPA_DATA_MemFd));
    if (pw_stream_update_params(c->stream, &buffers, 1) < 0)
        pw_main_loop_quit(c->loop);
}

static void on_frame(void *data)
{
    struct capture *c = data;
    struct pw_buffer *buffer = pw_stream_dequeue_buffer(c->stream);
    if (!buffer)
        return;
    if (buffer->buffer->n_datas && c->info.size.width) {
        const struct spa_data *plane = &buffer->buffer->datas[0];
        const struct spa_chunk *chunk = plane->chunk;
        if (plane->type == SPA_DATA_MemFd && plane->data && chunk && chunk->stride > 0 &&
            !(chunk->flags & (SPA_CHUNK_FLAG_CORRUPTED | SPA_CHUNK_FLAG_EMPTY)) &&
            (uint64_t)chunk->stride >= (uint64_t)c->info.size.width * c->layout->bytes) {
            uint64_t offset = (uint64_t)c->y * chunk->stride + (uint64_t)c->x * c->layout->bytes;
            uint64_t end = offset + c->layout->bytes;
            if (end <= chunk->size && chunk->offset + end <= plane->maxsize) {
                print_pixel(c, (const uint8_t *)plane->data + chunk->offset + offset);
                c->result = 0;
                pw_main_loop_quit(c->loop);
            }
        }
    }
    pw_stream_queue_buffer(c->stream, buffer);
}

static void on_state(void *data, enum pw_stream_state old, enum pw_stream_state state, const char *error)
{
    struct capture *c = data;
    (void)old;
    if (state == PW_STREAM_STATE_ERROR) {
        fprintf(stderr, "PipeWire stream: %s\n", error ? error : "error");
        pw_main_loop_quit(c->loop);
    }
}

static void on_timeout(void *data, uint64_t expirations)
{
    struct capture *c = data;
    (void)expirations;
    fprintf(stderr, "Timed out waiting for a matching MemFd frame\n");
    pw_main_loop_quit(c->loop);
}

int main(int argc, char **argv)
{
    struct capture c = { .result = 1 };
    uint32_t node;
    if (argc == 5) {
        for (size_t i = 0; i < sizeof(layouts) / sizeof(layouts[0]); i++)
            if (strcmp(argv[2], layouts[i].name) == 0)
                c.layout = &layouts[i];
    }
    if (!c.layout || parse_uint(argv[1], &node) || node == PW_ID_ANY ||
        parse_uint(argv[3], &c.x) || parse_uint(argv[4], &c.y)) {
        fprintf(stderr, "Usage: %s NODE {xr30|xb30|rgba-f16|bgrx} X Y\n", argv[0]);
        return 2;
    }
    pw_init(NULL, NULL);
    c.loop = pw_main_loop_new(NULL);
    if (!c.loop)
        return 1;
    struct pw_loop *loop = pw_main_loop_get_loop(c.loop);
    struct spa_source *timer = pw_loop_add_timer(loop, on_timeout, &c);
    struct timespec timeout = { .tv_sec = 10 };
    if (!timer || pw_loop_update_timer(loop, timer, &timeout, NULL, false) < 0)
        goto done;
    static const struct pw_stream_events events = {
        PW_VERSION_STREAM_EVENTS, .state_changed = on_state, .param_changed = on_format, .process = on_frame
    };
    c.stream = pw_stream_new_simple(loop, "Mutter screen pixel",
        pw_properties_new(PW_KEY_MEDIA_TYPE, "Video", PW_KEY_MEDIA_CATEGORY, "Capture", NULL), &events, &c);
    if (c.stream) {
        uint8_t storage[512];
        struct spa_pod_builder builder = SPA_POD_BUILDER_INIT(storage, sizeof(storage));
        struct spa_video_info_raw info = { .format = c.layout->format,
            .color_primaries = c.layout->primaries, .transfer_function = c.layout->transfer };
        const struct spa_pod *format = spa_format_video_raw_build(&builder, SPA_PARAM_EnumFormat, &info);
        if (pw_stream_connect(c.stream, PW_DIRECTION_INPUT, node,
                PW_STREAM_FLAG_AUTOCONNECT | PW_STREAM_FLAG_MAP_BUFFERS, &format, 1) >= 0)
            pw_main_loop_run(c.loop);
        pw_stream_destroy(c.stream);
    }
done:
    if (timer)
        pw_loop_destroy_source(loop, timer);
    pw_main_loop_destroy(c.loop);
    pw_deinit();
    return c.result;
}
