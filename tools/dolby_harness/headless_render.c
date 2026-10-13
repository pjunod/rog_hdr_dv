/* Headless libplacebo 7.360.1 baseline consumer. No RPU or trim fabrication.
 * Public utility code: see LICENSES.md; upstream libraries keep their licences.
 */
#include <errno.h>
#include <float.h>
#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libplacebo/renderer.h>
#include <libplacebo/vulkan.h>

#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "Stage-1 RGB-f32le transport requires a little-endian host"
#endif
_Static_assert(sizeof(float) == 4 && FLT_RADIX == 2 && FLT_MANT_DIG == 24,
               "IEEE754 binary32 required");
_Static_assert(PL_MAJOR_VER == 7 && PL_API_VER == 360, "Pinned API required");
#if !defined(PL_HAVE_VULKAN) || !defined(PL_HAVE_DOVI)
#error "The pinned consumer requires Vulkan and parsed Dolby reshaping support"
#endif

static bool token(FILE *f, char buf[64])
{
    return fscanf(f, "%63s", buf) == 1;
}

static bool read_int(FILE *f, int min, int max, int *out)
{
    char buf[64], *end;
    if (!token(f, buf))
        return false;
    errno = 0;
    long n = strtol(buf, &end, 10);
    if (errno || end == buf || *end || n < min || n > max)
        return false;
    *out = (int) n;
    return true;
}

static bool read_float(FILE *f, float min, float max, float *out)
{
    char buf[64], *end;
    if (!token(f, buf))
        return false;
    errno = 0;
    double n = strtod(buf, &end);
    if (errno || end == buf || *end || !isfinite(n) || n < min || n > max)
        return false;
    *out = (float) n;
    return isfinite(*out);
}

static bool read_volume(FILE *f, struct pl_hdr_metadata *hdr)
{
    struct pl_cie_xy *points[] = {&hdr->prim.red, &hdr->prim.green,
                                 &hdr->prim.blue, &hdr->prim.white};
    if (!read_float(f, 0, 10000, &hdr->min_luma) ||
        !read_float(f, 0.000001f, 10000, &hdr->max_luma) ||
        hdr->min_luma >= hdr->max_luma)
        return false;
    for (int i = 0; i < 4; i++) {
        if (!read_float(f, 0.000001f, 0.999999f, &points[i]->x) ||
            !read_float(f, 0.000001f, 0.999999f, &points[i]->y) ||
            points[i]->x + points[i]->y > 1.000001f)
            return false;
    }
    double rx = points[0]->x, ry = points[0]->y;
    double gx = points[1]->x, gy = points[1]->y;
    double bx = points[2]->x, by = points[2]->y;
    double wx = points[3]->x, wy = points[3]->y;
    double det = (gy - by) * (rx - bx) + (bx - gx) * (ry - by);
    if (fabs(det) < 0.000001)
        return false;
    double r = ((gy - by) * (wx - bx) + (bx - gx) * (wy - by)) / det;
    double g = ((by - ry) * (wx - bx) + (rx - bx) * (wy - by)) / det;
    return r > 0 && g > 0 && r + g < 1;
}

static bool read_dovi(FILE *f, struct pl_dovi_metadata *dovi)
{
    for (int i = 0; i < 3; i++) {
        if (!read_float(f, -1000000, 1000000, &dovi->nonlinear_offset[i]))
            return false;
    }
    pl_matrix3x3 *matrices[] = {&dovi->nonlinear, &dovi->linear};
    for (int i = 0; i < 2; i++) {
        for (int row = 0; row < 3; row++) {
            for (int col = 0; col < 3; col++) {
                if (!read_float(f, -1000000, 1000000, &matrices[i]->m[row][col]))
                    return false;
            }
        }
    }
    for (int c = 0; c < 3; c++) {
        struct pl_reshape_data *comp = &dovi->comp[c];
        int count;
        if (!read_int(f, 0, 9, &count) || count == 1)
            return false;
        comp->num_pivots = (uint8_t) count;
        for (int i = 0; i < count; i++) {
            if (!read_float(f, 0, 1, &comp->pivots[i]) ||
                (i && comp->pivots[i] <= comp->pivots[i - 1]))
                return false;
        }
        for (int i = 0; i < count - 1; i++) {
            int method;
            if (!read_int(f, 0, 1, &method))
                return false;
            comp->method[i] = (uint8_t) method;
            if (!method) {
                for (int j = 0; j < 3; j++) {
                    if (!read_float(f, -1000000, 1000000, &comp->poly_coeffs[i][j]))
                        return false;
                }
            } else {
                int order;
                if (!read_int(f, 1, 3, &order) ||
                    !read_float(f, -1000000, 1000000, &comp->mmr_constant[i]))
                    return false;
                comp->mmr_order[i] = (uint8_t) order;
                for (int j = 0; j < order; j++) {
                    for (int k = 0; k < 7; k++) {
                        if (!read_float(f, -1000000, 1000000, &comp->mmr_coeffs[i][j][k]))
                            return false;
                    }
                }
            }
        }
    }
    return true;
}

static bool read_pixels(const char *path, size_t count, float *rgba)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return false;
    bool ok = true;
    for (size_t i = 0; i < count; i++) {
        if (fread(rgba + 4 * i, sizeof(float), 3, f) != 3) {
            ok = false;
            break;
        }
        for (int c = 0; c < 3; c++) {
            float v = rgba[4 * i + c];
            if (!isfinite(v) || v < 0 || v > 1)
                ok = false;
        }
        rgba[4 * i + 3] = 1;
    }
    if (fgetc(f) != EOF || ferror(f))
        ok = false;
    if (fclose(f))
        ok = false;
    return ok;
}

static bool write_pixels(const char *path, size_t count, const float *rgba)
{
    /* Validate all readback before creating a deliverable; never clip errors. */
    for (size_t i = 0; i < count; i++) {
        for (int c = 0; c < 3; c++) {
            float v = rgba[4 * i + c];
            if (!isfinite(v) || v < 0 || v > 1)
                return false;
        }
    }
    FILE *f = fopen(path, "wbx");
    if (!f)
        return false;
    bool ok = true;
    for (size_t i = 0; i < count; i++) {
        if (fwrite(rgba + 4 * i, sizeof(float), 3, f) != 3) {
            ok = false;
            break;
        }
    }
    if (fclose(f))
        ok = false;
    if (!ok)
        remove(path);
    return ok;
}

int main(int argc, char **argv)
{
    if (argc != 4) {
        fprintf(stderr, "Usage: headless-render CONTROL INPUT-F32LE OUTPUT-F32LE\n");
        return 2;
    }
    int width = 0, height = 0, system = 0, range = 0, depth = 0;
    struct pl_frame src = {.num_planes = 1}, dst = {.num_planes = 1};
    struct pl_dovi_metadata dovi = {0};
    FILE *control = fopen(argv[1], "r");
    char magic[64];
    bool valid = control && token(control, magic) && !strcmp(magic, "DVH1") &&
        read_int(control, 1, 3840, &width) && read_int(control, 1, 2160, &height) &&
        read_int(control, 0, 2, &system) && read_int(control, 0, 1, &range) &&
        read_int(control, 8, 16, &depth) &&
        (depth == 8 || depth == 10 || depth == 12 || depth == 16) &&
        read_volume(control, &src.color.hdr) && read_volume(control, &dst.color.hdr) &&
        read_float(control, 0, 1, &src.color.hdr.max_pq_y) &&
        read_float(control, 0, src.color.hdr.max_pq_y, &src.color.hdr.avg_pq_y);
    if (valid && system == 2)
        valid = read_dovi(control, &dovi);
    char trailing[64];
    if (valid && (token(control, trailing) || ferror(control)))
        valid = false;
    if (control && fclose(control))
        valid = false;
    if (!valid) {
        fprintf(stderr, "Invalid native control protocol\n");
        return 2;
    }

    src.repr = (struct pl_color_repr) {
        .sys = system == 0 ? PL_COLOR_SYSTEM_RGB : system == 1 ?
               PL_COLOR_SYSTEM_BT_2020_NC : PL_COLOR_SYSTEM_DOLBYVISION,
        .levels = range ? PL_COLOR_LEVELS_LIMITED : PL_COLOR_LEVELS_FULL,
        .alpha = PL_ALPHA_NONE,
        .bits = {.sample_depth = depth, .color_depth = depth},
        .dovi = system == 2 ? &dovi : NULL,
    };
    dst.repr = (struct pl_color_repr) {
        .sys = PL_COLOR_SYSTEM_RGB, .levels = PL_COLOR_LEVELS_FULL,
        .alpha = PL_ALPHA_NONE,
    };
    src.color.primaries = dst.color.primaries = PL_COLOR_PRIM_BT_2020;
    src.color.transfer = dst.color.transfer = PL_COLOR_TRC_PQ;
    src.crop = dst.crop = (pl_rect2df) {0, 0, width, height};
    size_t count = (size_t) width * (size_t) height;
    float *input = calloc(count * 4, sizeof(float));
    float *output = calloc(count * 4, sizeof(float));
    int result = 1;
    pl_log log = NULL;
    pl_vulkan vk = NULL;
    pl_renderer renderer = NULL;
    pl_tex source_tex = NULL, target_tex = NULL;
    if (!input || !output || !read_pixels(argv[2], count, input)) {
        fprintf(stderr, "Invalid frame bytes or allocation failure\n");
        goto cleanup;
    }
    if (PL_FIX_VER != 1) {
        fprintf(stderr, "Pinned libplacebo 7.360.1 runtime required\n");
        goto cleanup;
    }
    log = pl_log_create(PL_API_VER, pl_log_params(
        .log_cb = pl_log_simple, .log_priv = stderr, .log_level = PL_LOG_INFO));
    vk = pl_vulkan_create(log, pl_vulkan_params(.allow_software = true));
    if (!vk)
        goto cleanup;
    PFN_vkGetPhysicalDeviceProperties get_properties = (PFN_vkGetPhysicalDeviceProperties)
        vk->get_proc_addr(vk->instance, "vkGetPhysicalDeviceProperties");
    if (!get_properties)
        goto cleanup;
    VkPhysicalDeviceProperties properties;
    get_properties(vk->phys_device, &properties);
    if (properties.deviceType != VK_PHYSICAL_DEVICE_TYPE_CPU) {
        fprintf(stderr, "Headless CPU Vulkan device required\n");
        goto cleanup;
    }
    printf("libplacebo=%s device=%s api=%u driver=%u vendor=%u device_id=%u\n",
           PL_VERSION, properties.deviceName, properties.apiVersion,
           properties.driverVersion, properties.vendorID, properties.deviceID);
    pl_gpu gpu = vk->gpu;
    pl_fmt format = pl_find_fmt(gpu, PL_FMT_FLOAT, 4, 32, 32,
                               PL_FMT_CAP_SAMPLEABLE | PL_FMT_CAP_RENDERABLE);
    if (!format)
        goto cleanup;
    source_tex = pl_tex_create(gpu, pl_tex_params(
        .w = width, .h = height, .format = format,
        .sampleable = true, .initial_data = input));
    target_tex = pl_tex_create(gpu, pl_tex_params(
        .w = width, .h = height, .format = format,
        .renderable = true, .host_readable = true));
    renderer = pl_renderer_create(log, gpu);
    if (!source_tex || !target_tex || !renderer)
        goto cleanup;
    src.planes[0] = (struct pl_plane) {
        .texture = source_tex, .components = 3, .component_mapping = {0, 1, 2, -1}};
    dst.planes[0] = (struct pl_plane) {
        .texture = target_tex, .components = 3, .component_mapping = {0, 1, 2, -1}};
    struct pl_render_params params = pl_render_default_params;
    params.peak_detect_params = NULL;
    params.dither_params = NULL;
    params.deband_params = NULL;
    params.sigmoid_params = NULL;
    params.upscaler = params.downscaler = NULL;
    if (!pl_render_image(renderer, &src, &dst, &params) ||
        pl_renderer_get_errors(renderer).errors != PL_RENDER_ERR_NONE ||
        !pl_tex_download(gpu, pl_tex_transfer_params(.tex = target_tex, .ptr = output)) ||
        !write_pixels(argv[3], count, output))
        goto cleanup;
    result = 0;
cleanup:
    if (renderer)
        pl_renderer_destroy(&renderer);
    if (vk) {
        pl_tex_destroy(vk->gpu, &source_tex);
        pl_tex_destroy(vk->gpu, &target_tex);
        pl_vulkan_destroy(&vk);
    }
    pl_log_destroy(&log);
    free(input);
    free(output);
    if (result)
        fprintf(stderr, "No successful rendered output produced\n");
    return result;
}
