/* Synthetic GPU checks for the frame contract. No private mapper is needed. */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <libplacebo/renderer.h>
#include <libplacebo/vulkan.h>

enum { WIDTH = 64, HEIGHT = 36 };
struct observation {
    unsigned seen;
    bool bad_geometry;
    pl_tex pattern;
};

static int inspect_frame(void *opaque, pl_gpu gpu, const uint8_t *rpu, size_t size,
                         const struct pl_color_space *target, pl_tex master,
                         pl_tex *mapped, struct pl_color_space *color)
{
    struct observation *obs = opaque;
    (void) gpu;
    if (size != 1 || rpu[0] > 1)
        return -1;
    obs->seen |= 1u << rpu[0];
    obs->bad_geometry |= master->params.w != WIDTH || master->params.h != HEIGHT;
    if (rpu[0] == 1)
        return -1;
    *mapped = obs->pattern;
    *color = *target;
    return 1;
}

int main(int argc, char **argv)
{
    if (argc != 2 || (strcmp(argv[1], "crop") && strcmp(argv[1], "crop-bilinear") &&
                      strcmp(argv[1], "mix-failure")))
        return 2;
    pl_vulkan vk = pl_vulkan_create(NULL, pl_vulkan_params(.allow_software = true));
    if (!vk)
        return 2;
    pl_gpu gpu = vk->gpu;
    pl_renderer rr = pl_renderer_create(NULL, gpu);
    pl_fmt fmt = pl_find_named_fmt(gpu, "rgba16");
    pl_tex src = NULL, dst = NULL, pattern = NULL;
    const bool scale = !strcmp(argv[1], "crop-bilinear");
    const int dst_w = scale ? WIDTH : 50, dst_h = scale ? HEIGHT : 29;
    uint16_t samples[HEIGHT][WIDTH][4] = {0};
    for (int y = 0; y < HEIGHT; y++) {
        for (int x = 0; x < WIDTH; x++) {
            /* Bright outside the crop, mid-grey inside. A full-frame blit
             * therefore cannot pass the edge probes on the destination. */
            uint16_t gray = x < 4 || x > 55 || y < 3 || y > 33 ? 50000 : 18000;
            for (int c = 0; c < 3; c++)
                samples[y][x][c] = gray;
            samples[y][x][3] = 65535;
        }
    }
    int result = 2;
    if (!rr || !fmt)
        goto done;
    src = pl_tex_create(gpu, pl_tex_params(.w = 72, .h = 40, .format = fmt,
                                            .sampleable = true, .renderable = true));
    pattern = pl_tex_create(gpu, pl_tex_params(.w = WIDTH, .h = HEIGHT, .format = fmt,
                                               .sampleable = true, .initial_data = samples));
    dst = pl_tex_create(gpu, pl_tex_params(.w = dst_w, .h = dst_h, .format = fmt,
                                            .host_readable = true,
                                            .sampleable = true, .renderable = true));
    if (!src || !dst || !pattern)
        goto done;
    struct pl_dovi_metadata reshape = {0};
    reshape.linear = reshape.nonlinear = pl_matrix3x3_identity;
    for (int c = 0; c < 3; c++) {
        reshape.comp[c].num_pivots = 2;
        reshape.comp[c].pivots[1] = 1;
        reshape.comp[c].poly_coeffs[0][1] = 1;
    }
    const uint8_t markers[] = {0, 1};
    struct pl_frame frame = {
        .num_planes = 1, .planes = {{.texture = src, .components = 3,
                                       .component_mapping = {0, 1, 2}}},
        .repr = {.sys = PL_COLOR_SYSTEM_DOLBYVISION, .levels = PL_COLOR_LEVELS_FULL,
                 .dovi = &reshape},
        .color = pl_color_space_hdr10,
        .crop = {4.5f, 3.5f, 54.5f, 32.5f},
        .dovi_master_width = WIDTH, .dovi_master_height = HEIGHT,
        .dovi_rpu = &markers[0], .dovi_rpu_size = 1,
    };
    struct pl_frame target = {
        .num_planes = 1, .planes = {{.texture = dst, .components = 3,
                                       .component_mapping = {0, 1, 2}}},
        .color = pl_color_space_hdr10, .repr = pl_color_repr_rgb,
    };
    struct observation obs = {.pattern = pattern};
    struct pl_render_params params = pl_render_default_params;
    params.dovi_map = inspect_frame;
    params.dovi_priv = &obs;
    if (strcmp(argv[1], "mix-failure")) {
        params.upscaler = params.downscaler = &pl_filter_bilinear;
        result = !(pl_render_image(rr, &frame, &target, &params) &&
                   obs.seen == 1 && !obs.bad_geometry);
        uint16_t pixels[WIDTH * HEIGHT * 4];
        if (!result && pl_tex_download(gpu, pl_tex_transfer_params(.tex = dst, .ptr = pixels))) {
            const int y = dst_h / 2;
            for (int x = 1; x < dst_w; x++) {
                int value = pixels[4 * (dst_w * y + x)];
                if (value < 17500 || value > 18500)
                    result = 1;
            }
        } else {
            result = 1;
        }
    } else {
        struct pl_frame other = frame;
        other.dovi_rpu = &markers[1];
        const struct pl_frame *frames[] = {&frame, &other};
        struct pl_frame_mix mix = {
            .num_frames = 2, .frames = frames,
            .timestamps = (float[]){-0.25f, 0.75f},
            .signatures = (uint64_t[]){1, 2}, .vsync_duration = 1,
        };
        params.frame_mixer = &pl_filter_oversample;
        result = !(!pl_render_image_mix(rr, &mix, &target, &params) &&
                   obs.seen == 3 && !obs.bad_geometry);
    }
    fprintf(stderr, "%s: visited=%u wrong-size=%d result=%d\n",
            argv[1], obs.seen, obs.bad_geometry, result);
done:
    pl_renderer_destroy(&rr);
    pl_tex_destroy(gpu, &pattern);
    pl_tex_destroy(gpu, &src);
    pl_tex_destroy(gpu, &dst);
    pl_vulkan_destroy(&vk);
    return result;
}
