/* Separate OPEN diagnostic consumer, derived from headless_render.c at
 * 81d1255f12386db088f65d9cf439e84c7ba85456. Public utility code: LICENSES.md.
 * Upstream library licences unchanged. Not a consumer Dolby CM implementation.
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
#error "RGB-f32le requires little endian"
#endif
_Static_assert(sizeof(float) == 4 && FLT_RADIX == 2 && FLT_MANT_DIG == 24,
               "IEEE754 binary32 required");
_Static_assert(PL_MAJOR_VER == 7 && PL_API_VER == 362, "Private matched ABI362 required");
#if !defined(PL_HAVE_VULKAN) || !defined(PL_HAVE_DOVI)
#error "Private full Vulkan/DOVI build required"
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

static bool read_double(FILE *f, double min, double max, double *out)
{
    char buf[64], *end;
    if (!token(f, buf))
        return false;
    errno = 0;
    double n = strtod(buf, &end);
    if (errno || end == buf || *end || !isfinite(n) || n < min || n > max)
        return false;
    *out = n;
    return true;
}

static bool read_float(FILE *f, float min, float max, float *out)
{
    double n;
    if (!read_double(f, min, max, &n))
        return false;
    *out = (float) n;
    return isfinite(*out);
}

static bool read_l1(FILE *f, struct pl_dovi_dm_metadata *dm)
{
    double min, avg, max;
    // Check original parsed coordinates together before binary32 narrowing.
    // Equal decimal anchors must reach the explicit flat/collapsed policies;
    // genuinely descending coordinates reject even if they round to equal floats.
    if (!read_double(f, 0, 1, &min) || !read_double(f, min, 1, &avg) ||
        !read_double(f, avg, 1, &max))
        return false;
    dm->min_pq = (float) min;
    dm->avg_pq = (float) avg;
    dm->max_pq = (float) max;
    return true;
}

static bool read_volume(FILE *f, struct pl_hdr_metadata *hdr)
{
    struct pl_cie_xy *p[] = {&hdr->prim.red, &hdr->prim.green,
                            &hdr->prim.blue, &hdr->prim.white};
    if (!read_float(f, 0, 10000, &hdr->min_luma) ||
        !read_float(f, 0.000001f, 10000, &hdr->max_luma) ||
        hdr->min_luma >= hdr->max_luma)
        return false;
    for (int i = 0; i < 4; i++) {
        if (!read_float(f, 0.000001f, 0.999999f, &p[i]->x) ||
            !read_float(f, 0.000001f, 0.999999f, &p[i]->y) ||
            p[i]->x + p[i]->y > 1.000001f)
            return false;
    }
    double rx = p[0]->x, ry = p[0]->y, gx = p[1]->x, gy = p[1]->y;
    double bx = p[2]->x, by = p[2]->y, wx = p[3]->x, wy = p[3]->y;
    double det = (gy - by) * (rx - bx) + (bx - gx) * (ry - by);
    if (fabs(det) < 0.000001)
        return false;
    double r = ((gy - by) * (wx - bx) + (bx - gx) * (wy - by)) / det;
    double g = ((by - ry) * (wx - bx) + (rx - bx) * (wy - by)) / det;
    return r > 0 && g > 0 && r + g < 1;
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
        fprintf(stderr, "Usage: open-dm-render CONTROL INPUT-F32LE OUTPUT-F32LE\n");
        return 2;
    }
    int width = 0, height = 0, primaries = 0, variant = 0;
    struct pl_frame src = {.num_planes = 1}, dst = {.num_planes = 1};
    struct pl_dovi_dm_metadata *dm = &src.dovi_dm;
    struct pl_dovi_dm_sop factors = { .version = 1,
        .domain = PL_DOVI_DM_SOP_TARGET_NORMALIZED_PQ };
    FILE *control = fopen(argv[1], "r");
    char magic[64], trailing[64];
    bool valid = control && token(control, magic) && !strcmp(magic, "DVH3") &&
        read_int(control, 1, 4096, &width) && read_int(control, 1, 2160, &height) &&
        read_int(control, 1, 1, &primaries) &&
        read_volume(control, &src.color.hdr) && read_volume(control, &dst.color.hdr) &&
        read_l1(control, dm) &&
        read_int(control, 0, 2, &variant) &&
        read_float(control, 0.5f, 1.5f, &factors.slope) &&
        read_float(control, -0.5f, 0.5f, &factors.offset) &&
        read_float(control, 0.5f, 1.5f, &factors.power);
    if (valid && (token(control, trailing) || ferror(control)))
        valid = false;
    if (control && fclose(control))
        valid = false;
    if (variant != 2 && (factors.slope != 1 || factors.offset != 0 || factors.power != 1))
        valid = false;
    if (!valid) {
        fprintf(stderr, "Invalid DVH3 control protocol\n");
        return 2;
    }
    dm->version = 2;
    dm->origin = PL_DOVI_DM_OFFICIAL_XML;
    dm->has_l1 = true;
    dm->source = src.color.hdr;
    dm->curve = variant == 0 ? PL_DOVI_DM_ST2094_10 : PL_DOVI_DM_OPEN_HERMITE_PQ;
    if (variant == 2)
        dm->open_sop = factors;
    // Frame owns both complete values for this output's entire lifetime.
    dst.dovi_target = (struct pl_dovi_dm_target) {
        .version = 1, .generation = 1, .description_id = 27, .volume = dst.color.hdr };
    struct pl_tone_map_params tone = {.constants = {PL_TONE_MAP_CONSTANTS}, .lut_size = 256};
    enum pl_dovi_dm_status status = pl_dovi_dm_prepare(dm, &dst.dovi_target.volume, &tone);
    if (status != PL_DOVI_DM_L1 && status != PL_DOVI_DM_FLAT) {
        fprintf(stderr, "Explicit OPEN metadata rejected\n");
        return 2;
    }
    src.repr = dst.repr = (struct pl_color_repr) {
        .sys = PL_COLOR_SYSTEM_RGB, .levels = PL_COLOR_LEVELS_FULL, .alpha = PL_ALPHA_NONE };
    src.color.primaries = PL_COLOR_PRIM_DISPLAY_P3;
    dst.color.primaries = PL_COLOR_PRIM_BT_2020;
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
    if (!input || !output || !read_pixels(argv[2], count, input))
        goto cleanup;
    if (PL_FIX_VER != 1)
        goto cleanup;
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
    if (properties.deviceType != VK_PHYSICAL_DEVICE_TYPE_CPU)
        goto cleanup;
    printf("libplacebo=%s device=%s api=%u driver=%u vendor=%u device_id=%u OPEN_variant=%d\n",
           PL_VERSION, properties.deviceName, properties.apiVersion,
           properties.driverVersion, properties.vendorID, properties.deviceID, variant);
    pl_gpu gpu = vk->gpu;
    pl_fmt format = pl_find_fmt(gpu, PL_FMT_FLOAT, 4, 32, 32,
                               PL_FMT_CAP_SAMPLEABLE | PL_FMT_CAP_RENDERABLE);
    if (!format)
        goto cleanup;
    source_tex = pl_tex_create(gpu, pl_tex_params(
        .w = width, .h = height, .format = format, .sampleable = true, .initial_data = input));
    target_tex = pl_tex_create(gpu, pl_tex_params(
        .w = width, .h = height, .format = format, .renderable = true, .host_readable = true));
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
        fprintf(stderr, "No successful OPEN rendered output produced\n");
    return result;
}
