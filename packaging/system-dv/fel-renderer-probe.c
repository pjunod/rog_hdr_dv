/* Tests the renderer's native master and interpolation error contract. */
#include <libplacebo/renderer.h>
#include <libplacebo/vulkan.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

enum { W = 72, H = 40, VW = 64, VH = 36, DW = 50, DH = 29 };
struct observations { unsigned composed, mapped, bad_size, denied; };

static int observe(void *opaque, pl_gpu gpu, const uint8_t *raw, size_t size,
                   bool composed, const struct pl_color_space *target,
                   pl_tex master, pl_tex *mapped, struct pl_color_space *color)
{
    struct observations *obs = opaque;
    (void) gpu;
    if (size != 1 || !raw || !master)
        return -1;
    obs->composed += composed;
    obs->mapped++;
    obs->bad_size += master->params.w != VW || master->params.h != VH;
    *mapped = master;
    *color = *target;
    return 1;
}

static bool deny_acquire(pl_gpu gpu, struct pl_frame *frame)
{
    struct observations *obs = frame->user_data;
    (void) gpu;
    obs->denied++;
    return false;
}

int main(int argc, char **argv)
{
    if (argc != 2 || (strcmp(argv[1], "flip") && strcmp(argv[1], "nonref-acquire")))
        return 2;
    pl_vulkan vk = pl_vulkan_create(NULL, pl_vulkan_params(.allow_software = true));
    if (!vk)
        return 2;
    pl_gpu gpu = vk->gpu;
    pl_renderer rr = pl_renderer_create(NULL, gpu);
    pl_fmt fmt = pl_find_named_fmt(gpu, "rgba16");
    pl_tex stacks[3] = {0}, out = NULL;
    static uint16_t samples[3][H][W][4], screen[3][DH][DW][4];
    int result = 2;
    struct observations obs = {0};
    for (int y = 0; y < H; y++) {
        for (int x = 0; x < W; x++) {
            for (int c = 0; c < 4; c++) {
                samples[0][y][x][c] = c == 3 ? 65535 : 32000;
                samples[1][y][x][c] = c == 3 ? 65535 : 17000 + y * 750;
                samples[2][H - 1 - y][x][c] = samples[1][y][x][c];
            }
        }
    }
    if (!rr || !fmt)
        goto done;
    for (int i = 0; i < 3; i++) {
        stacks[i] = pl_tex_create(gpu, pl_tex_params(.w=W, .h=H, .format=fmt,
                .sampleable=true, .initial_data=samples[i]));
        if (!stacks[i])
            goto done;
    }
    out = pl_tex_create(gpu, pl_tex_params(.w=DW, .h=DH, .format=fmt,
                .sampleable=true, .renderable=true, .host_readable=true));
    if (!out)
        goto done;
    struct pl_dovi_metadata dm = {.nlq_active = true};
    dm.linear = dm.nonlinear = pl_matrix3x3_identity;
    for (int c = 0; c < 3; c++) {
        dm.comp[c].num_pivots = 2;
        dm.comp[c].pivots[1] = 1;
        dm.comp[c].poly_coeffs[0][1] = 1;
        dm.nlq[c].offset = 512;
        dm.nlq[c].deadzone_slope = 0.0003f;
        dm.nlq[c].hdr_in_max = 0.3f;
    }
    uint8_t raw = 1;
    struct pl_frame el = {.num_planes = 1,
        .planes={{.texture=stacks[1], .components=3, .component_mapping={0,1,2}}},
        .repr={.bits={.sample_depth=16,.color_depth=10,.bit_shift=6},
               .levels=PL_COLOR_LEVELS_FULL}, .user_data=&obs};
    struct pl_frame frame = {.num_planes=1,
        .planes={{.texture=stacks[0], .components=3,.component_mapping={0,1,2}}},
        .repr={.sys=PL_COLOR_SYSTEM_DOLBYVISION, .levels=PL_COLOR_LEVELS_FULL, .dovi=&dm},
        .color=pl_color_space_hdr10, .enhancement_layer=&el,
        .crop={4.5f,3.5f,54.5f,32.5f}, .dovi_master_width=VW,.dovi_master_height=VH,
        .dovi_rpu=&raw,.dovi_rpu_size=1};
    struct pl_frame target = {.num_planes=1,
        .planes={{.texture=out,.components=3,.component_mapping={0,1,2}}},
        .color=pl_color_space_hdr10,.repr=pl_color_repr_rgb};
    struct pl_render_params params = pl_render_default_params;
    params.dovi_map = observe;
    params.dovi_priv = &obs;
    if (!strcmp(argv[1], "nonref-acquire")) {
        struct pl_frame other = frame, inaccessible = el;
        inaccessible.acquire = deny_acquire;
        other.enhancement_layer = &inaccessible;
        struct pl_frame_mix mix = {.num_frames=2,
            .frames=(const struct pl_frame *[]){&frame,&other},
            .timestamps=(double[]){-.25f,.75f},.signatures=(uint64_t[]){7,8},.vsync_duration=1};
        params.frame_mixer = &pl_filter_oversample;
        result = pl_render_image_mix(rr,&mix,&target,&params) || !obs.denied || obs.bad_size;
    } else {
        params.upscaler = params.downscaler = &pl_filter_bilinear;
        for (int i = 0; i < 3; i++) {
            el.planes[0].texture = stacks[i == 0 ? 1 : 2];
            el.planes[0].flipped = i == 1;
            if (!pl_render_image(rr,&frame,&target,&params) ||
                !pl_tex_download(gpu,pl_tex_transfer_params(.tex=out,.ptr=screen[i])))
                goto done;
        }
        result = obs.composed != 3 || obs.bad_size ||
            memcmp(screen[0],screen[1],sizeof(screen[0])) != 0 ||
            memcmp(screen[0],screen[2],sizeof(screen[0])) == 0;
    }
done:
    fprintf(stderr, "%s mapped=%u composed=%u denied=%u bad_size=%u result=%d\n",
            argv[1],obs.mapped,obs.composed,obs.denied,obs.bad_size,result);
    pl_renderer_destroy(&rr);
    pl_tex_destroy(gpu,&out);
    for (int i=0;i<3;i++) pl_tex_destroy(gpu,&stacks[i]);
    pl_vulkan_destroy(&vk);
    return result;
}
