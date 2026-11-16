/* Timestamped crop recorder, derived from Claude's November 15, 2026 pw-seq.c.
 * Usage: iq_pw_seq NODE OUT_PREFIX NFRAMES X Y W H
 * Accepts only xRGB_210LE with BT.2020 primaries and PQ transfer.
 * Writes exclusive OUT_PREFIX.raw and OUT_PREFIX.ts files; removes outputs it
 * created on failure. TS columns: ordinal, SPA PTS ns, SPA sequence, receive
 * CLOCK_MONOTONIC ns. Missing PTS/sequence are -1. Exit 0 means all crops and
 * timestamps were written and closed. This is damage-driven software capture,
 * not a refresh sampler or proof of physical panel cadence.
 */
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <pipewire/pipewire.h>
#include <spa/param/video/format-utils.h>
#include <spa/pod/builder.h>
#include <spa/buffer/meta.h>

struct capture {
    struct pw_main_loop *loop;
    struct pw_stream *stream;
    struct spa_video_info_raw info;
    FILE *raw, *ts;
    uint32_t want, got, x, y, w, h;
    int failed;
    int64_t last_receive, last_pts;
};

static void fail(struct capture *c, const char *message)
{
    fprintf(stderr, "%s\n", message);
    c->failed = 1;
    if (c->loop) pw_main_loop_quit(c->loop);
}

static int parse_u32(const char *text, uint32_t *out)
{
    char *end;
    if (!*text) return -1;
    for (const char *p = text; *p; p++)
        if (*p < '0' || *p > '9') return -1;
    errno = 0;
    unsigned long long value = strtoull(text, &end, 10);
    if (errno || *end || value > UINT32_MAX) return -1;
    *out = (uint32_t)value;
    return 0;
}

static void changed(void *data, uint32_t id, const struct spa_pod *param)
{
    struct capture *c = data;
    if (id != SPA_PARAM_Format || !param) return;
    if (spa_format_video_raw_parse(param, &c->info) < 0) {
        fail(c, "cannot parse negotiated format");
        return;
    }
    fprintf(stderr, "format=%d primaries=%d transfer=%d shape=%ux%u framerate=%u/%u max=%u/%u\n",
            c->info.format, c->info.color_primaries, c->info.transfer_function,
            c->info.size.width, c->info.size.height, c->info.framerate.num,
            c->info.framerate.denom, c->info.max_framerate.num, c->info.max_framerate.denom);
    uint8_t scratch[1024];
    struct spa_pod_builder builder = SPA_POD_BUILDER_INIT(scratch, sizeof scratch);
    const struct spa_pod *params[2];
    params[0] = spa_pod_builder_add_object(&builder, SPA_TYPE_OBJECT_ParamBuffers, SPA_PARAM_Buffers,
        SPA_PARAM_BUFFERS_dataType, SPA_POD_CHOICE_FLAGS_Int(1 << SPA_DATA_MemFd));
    params[1] = spa_pod_builder_add_object(&builder, SPA_TYPE_OBJECT_ParamMeta, SPA_PARAM_Meta,
        SPA_PARAM_META_type, SPA_POD_Id(SPA_META_Header),
        SPA_PARAM_META_size, SPA_POD_Int(sizeof(struct spa_meta_header)));
    if (!params[0] || !params[1] || pw_stream_update_params(c->stream, params, 2) < 0)
        fail(c, "cannot request capture buffers/metadata");
}

static void state(void *data, enum pw_stream_state old, enum pw_stream_state now, const char *error)
{
    (void)old;
    if (now == PW_STREAM_STATE_ERROR) fail(data, error ? error : "PipeWire stream error");
}

static void frame(void *data)
{
    struct capture *c = data;
    struct pw_buffer *p = pw_stream_dequeue_buffer(c->stream);
    if (!p) return;
    if (c->failed || c->got >= c->want) goto requeue;
    const struct spa_buffer *buffer = p->buffer;
    if (!buffer || buffer->n_datas != 1 || !buffer->datas || (buffer->n_metas && !buffer->metas)) goto requeue;
    const struct spa_data *s = &buffer->datas[0];
    uint32_t width = c->info.size.width, height = c->info.size.height;
    if (c->info.format != SPA_VIDEO_FORMAT_xRGB_210LE ||
        c->info.color_primaries != SPA_VIDEO_COLOR_PRIMARIES_BT2020 ||
        c->info.transfer_function != SPA_VIDEO_TRANSFER_SMPTE2084 ||
        !width || !height || width > INT32_MAX / 4 ||
        c->x > width || c->w > width - c->x || c->y > height || c->h > height - c->y ||
        !s->data || !s->chunk || !s->chunk->size ||
        (s->chunk->flags & (SPA_CHUNK_FLAG_CORRUPTED | SPA_CHUNK_FLAG_EMPTY)) || s->chunk->stride < (int32_t)(width * 4))
        goto requeue; /* e.g. cursor-only update, not a usable complete crop */
    uint64_t needed = (uint64_t)(height - 1) * (uint32_t)s->chunk->stride + (uint64_t)width * 4;
    if (s->chunk->offset > s->maxsize || s->chunk->size > s->maxsize - s->chunk->offset ||
        needed > s->chunk->size || needed > SIZE_MAX) goto requeue;
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) < 0 || now.tv_sec < 0 ||
        now.tv_nsec < 0 || now.tv_nsec >= 1000000000 ||
        (uint64_t)now.tv_sec > (uint64_t)(INT64_MAX - now.tv_nsec) / 1000000000) {
        fail(c, "invalid receive monotonic timestamp");
        goto requeue;
    }
    int64_t receive = (int64_t)now.tv_sec * 1000000000 + now.tv_nsec;
    struct spa_meta_header *header = spa_buffer_find_meta_data(buffer, SPA_META_Header, sizeof *header);
    if (header && (header->flags & (SPA_META_HEADER_FLAG_CORRUPTED | SPA_META_HEADER_FLAG_GAP))) goto requeue;
    if (header && header->seq > INT64_MAX) {
        fail(c, "SPA sequence exceeds timestamp-file signed range");
        goto requeue;
    }
    int64_t pts = header && header->pts >= 0 ? header->pts : -1;
    int64_t sequence = header ? (int64_t)header->seq : -1;
    if ((c->got && receive <= c->last_receive) || (pts >= 0 && c->last_pts >= 0 && pts <= c->last_pts)) {
        fail(c, "non-monotonic receive or available SPA PTS timestamp");
        goto requeue;
    }
    for (uint32_t row = 0; row < c->h; row++) {
        const uint8_t *pixels = (const uint8_t *)s->data + s->chunk->offset +
            (size_t)(c->y + row) * (uint32_t)s->chunk->stride + (size_t)c->x * 4;
        if (fwrite(pixels, 4, c->w, c->raw) != c->w) {
            fail(c, "cannot write crop pixels");
            goto requeue;
        }
    }
    if (fprintf(c->ts, "%u %" PRId64 " %" PRId64 " %" PRId64 "\n",
                c->got, pts, sequence, receive) < 0) {
        fail(c, "cannot write crop timestamp");
        goto requeue;
    }
    c->last_receive = receive;
    if (pts >= 0) c->last_pts = pts;
    c->got++;
    if (c->got == c->want) pw_main_loop_quit(c->loop);
requeue:
    if (pw_stream_queue_buffer(c->stream, p) < 0) fail(c, "cannot requeue capture buffer");
}

int main(int argc, char **argv)
{
    struct capture c = {.last_pts = -1};
    uint32_t node;
    if (argc != 8 || parse_u32(argv[1], &node) || parse_u32(argv[3], &c.want) ||
        parse_u32(argv[4], &c.x) || parse_u32(argv[5], &c.y) ||
        parse_u32(argv[6], &c.w) || parse_u32(argv[7], &c.h) ||
        !c.want || !c.w || !c.h || c.x > UINT32_MAX - c.w || c.y > UINT32_MAX - c.h ||
        c.w > INT32_MAX / 4 || (uint64_t)c.w * c.h > (uint64_t)INT64_MAX / 4 / c.want) {
        fprintf(stderr, "usage: %s NODE OUT_PREFIX NFRAMES X Y W H (bounded unsigned decimals)\n", argv[0]);
        return 2;
    }
    size_t length = strlen(argv[2]);
    if (!length || length > SIZE_MAX - 5) return 2;
    char *raw_path = malloc(length + 5), *ts_path = malloc(length + 5);
    int raw_created = 0, ts_created = 0, initialized = 0, result = 1;
    if (!raw_path || !ts_path) goto cleanup;
    memcpy(raw_path, argv[2], length);
    memcpy(raw_path + length, ".raw", 5);
    memcpy(ts_path, argv[2], length);
    memcpy(ts_path + length, ".ts", 4);
    c.raw = fopen(raw_path, "wbx");
    if (!c.raw) { perror("create raw output"); goto cleanup; }
    raw_created = 1;
    c.ts = fopen(ts_path, "wx");
    if (!c.ts) { perror("create timestamp output"); goto cleanup; }
    ts_created = 1;
    pw_init(NULL, NULL);
    initialized = 1;
    c.loop = pw_main_loop_new(NULL);
    if (!c.loop) goto cleanup;
    const struct pw_stream_events events = {PW_VERSION_STREAM_EVENTS,
        .state_changed = state, .param_changed = changed, .process = frame};
    c.stream = pw_stream_new_simple(pw_main_loop_get_loop(c.loop), "private-hdr-sequence",
        pw_properties_new(PW_KEY_MEDIA_TYPE, "Video", PW_KEY_MEDIA_CATEGORY, "Capture", NULL), &events, &c);
    if (!c.stream) goto cleanup;
    uint8_t scratch[1024];
    struct spa_pod_builder builder = SPA_POD_BUILDER_INIT(scratch, sizeof scratch);
    struct spa_video_info_raw info = {.format = SPA_VIDEO_FORMAT_xRGB_210LE,
        .color_primaries = SPA_VIDEO_COLOR_PRIMARIES_BT2020, .transfer_function = SPA_VIDEO_TRANSFER_SMPTE2084,
        .framerate = SPA_FRACTION(0, 1), .max_framerate = SPA_FRACTION(240, 1)};
    const struct spa_pod *format = spa_format_video_raw_build(&builder, SPA_PARAM_EnumFormat, &info);
    if (!format || pw_stream_connect(c.stream, PW_DIRECTION_INPUT, node,
        PW_STREAM_FLAG_AUTOCONNECT | PW_STREAM_FLAG_MAP_BUFFERS, &format, 1) < 0) goto cleanup;
    if (pw_main_loop_run(c.loop) < 0) c.failed = 1;
    result = c.failed || c.got != c.want;
cleanup:
    if (c.stream) pw_stream_destroy(c.stream);
    if (c.loop) pw_main_loop_destroy(c.loop);
    if (initialized) pw_deinit();
    /* Close both files even if the first close fails. Delayed write failures
     * invalidate the pair just like immediate fwrite/fprintf failures. */
    if (c.raw && fclose(c.raw)) result = 1;
    if (c.ts && fclose(c.ts)) result = 1;
    if (result) {
        if (raw_created && unlink(raw_path)) perror("remove partial raw output");
        if (ts_created && unlink(ts_path)) perror("remove partial timestamp output");
    }
    free(raw_path);
    free(ts_path);
    fprintf(stderr, "frames=%u/%u\n", c.got, c.want);
    return result;
}
