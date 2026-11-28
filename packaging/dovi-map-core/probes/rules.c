/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* CPU-only checks of the core's qualification rules: no GPU, provider or
 * media. The implementation is included so its static rules are reachable. */
#include "../rog-dovi-map.c"
#include <assert.h>

static unsigned checks, failures;
static void require (bool ok, const char *name)
{ checks++; if (!ok) { failures++; fprintf (stderr, "FAIL %s\n", name); } }

static struct rog_dovi_stream_config config (uint8_t profile, uint8_t compat, uint8_t el)
{
  return (struct rog_dovi_stream_config) {.version_major = 1, .profile = profile, .level = 6,
      .rpu_present = 1, .bl_present = 1, .el_present = el, .bl_signal_compatibility_id = compat};
}

static void stream_rules (void)
{
  struct rog_dovi_stream_config c = config (5, 0, 0);
  require (rog_dovi_map_stream_profile (&c, 0) == 5, "Profile 5 compatibility 0");
  require (rog_dovi_map_profile5_has_no_base_fallback (&c), "Profile 5 has no base fallback");
  c = config (8, 1, 0);
  require (rog_dovi_map_stream_profile (&c, 0) == 8, "Profile 8 compatibility 1");
  require (!rog_dovi_map_profile5_has_no_base_fallback (&c), "Profile 8 keeps its base");
  c = config (8, 4, 0);
  require (!rog_dovi_map_stream_profile (&c, 0), "Profile 8.4 is not qualified");
  c = config (8, 2, 0);
  require (!rog_dovi_map_stream_profile (&c, 0), "Profile 8.2 is not qualified");
  c = config (5, 1, 0);
  require (!rog_dovi_map_stream_profile (&c, 0), "Profile 5 with a compatible base is not qualified");
  c = config (7, 6, 1);
  require (!rog_dovi_map_stream_profile (&c, 0) && rog_dovi_map_stream_profile (&c, 1) == 7,
      "Profile 7 only with a FEL decoder");
  c = config (8, 1, 0); c.version_minor = 1;
  require (!rog_dovi_map_stream_profile (&c, 0), "version 1.0 only");
  c = config (8, 1, 0); c.md_compression = 1;
  require (!rog_dovi_map_stream_profile (&c, 0), "compressed metadata is not qualified");
  c = config (8, 1, 0); c.rpu_present = 0;
  require (!rog_dovi_map_stream_profile (&c, 0), "RPU must be present");
  c = config (8, 1, 0); c.bl_present = 0;
  require (!rog_dovi_map_stream_profile (&c, 0), "base layer must be present");
  require (!rog_dovi_map_stream_profile (NULL, 1), "unknown configuration");
  struct rog_dovi_stream_config a = config (5, 0, 0), b = a;
  require (rog_dovi_map_same_config (&a, &b), "same configuration");
  b.level = 7;
  require (!rog_dovi_map_same_config (&a, &b), "level differs");
}

static void destination_rules (void)
{
  struct rog_dovi_stream_config p5 = config (5, 0, 0), p8 = config (8, 1, 0);
  for (uint32_t flags = 0; flags < 8; flags++) {
    struct rog_dovi_target t = {.struct_size = sizeof (t), .flags = flags};
    require (rog_dovi_map_profile5_destination_supported (&p5, ROG_DOVI_DESTINATION_DISPLAY_PQ, &t) == (flags == 7),
        "Profile 5 display needs the complete witness");
    require (rog_dovi_map_profile5_destination_supported (&p5, ROG_DOVI_DESTINATION_STANDARD_SDR_SRGB, &t),
        "Profile 5 SDR needs no witness");
    require (rog_dovi_map_profile5_destination_supported (&p8, ROG_DOVI_DESTINATION_DISPLAY_PQ, &t),
        "Profile 8 may fall back");
  }
  require (!rog_dovi_map_profile5_destination_supported (&p5, ROG_DOVI_DESTINATION_DISPLAY_PQ, NULL),
      "Profile 5 display without a target");
}

static void metadata_rules (void)
{
  size_t size = 0;
  AVDOVIMetadata *m = av_dovi_metadata_alloc (&size);
  require (m && metadata_valid (m, size), "allocator layout is valid");
  size_t last = m->color_offset + sizeof (AVDOVIColorMetadata);
  if (m->header_offset + sizeof (AVDOVIRpuDataHeader) > last) last = m->header_offset + sizeof (AVDOVIRpuDataHeader);
  if (m->mapping_offset + sizeof (AVDOVIDataMapping) > last) last = m->mapping_offset + sizeof (AVDOVIDataMapping);
  require (!metadata_valid (m, last - 1), "truncated blob");
  require (!metadata_valid ((uint8_t *) m + 1, size - 1), "misaligned blob");
  size_t saved = m->color_offset;
  m->color_offset = size;
  require (!metadata_valid (m, size), "colour block outside the blob");
  m->color_offset = 1;
  require (!metadata_valid (m, size), "colour block inside the header");
  m->color_offset = saved;
  m->num_ext_blocks = AV_DOVI_MAX_EXT_BLOCKS + 1;
  require (!metadata_valid (m, size), "too many extension blocks");
  m->num_ext_blocks = 1; m->ext_block_size = 1;
  require (!metadata_valid (m, size), "short extension block");
  m->num_ext_blocks = 0;
  struct rog_dovi_picture p = {.struct_size = sizeof (p), .libavutil_version = LIBAVUTIL_VERSION_INT,
      .metadata = m, .metadata_size = size};
  require (record_metadata (&p) == m, "current libavutil record");
  p.libavutil_version = AV_VERSION_INT (LIBAVUTIL_VERSION_MAJOR - 1, 0, 0);
  require (!record_metadata (&p), "another libavutil major is no record");
  av_free (m);
}

static void pitch_rules (void)
{
  /* GTK: probes/output-buffer-layout.c, gpu-pitch-selection. */
  require (download_row_pitch_ok (32, 8, 32), "exact pitch");
  require (download_row_pitch_ok (40, 8, 32), "padded aligned pitch");
  require (!download_row_pitch_ok (36, 8, 32), "unaligned pitch");
  require (!download_row_pitch_ok (-32, 8, 32), "bottom-up pitch");
  require (!download_row_pitch_ok (0, 8, 32), "zero pitch");
  require (!download_row_pitch_ok (16, 8, 32), "short pitch");
  require (!download_row_pitch_ok (32, 0, 32), "no texel alignment");
  require (download_row_pitch_ok (16, 4, 16), "eight-bit pitch");
}

/* ROG_DOVI_MAP_BASELINE_ON_DECLINE: Profile 8 without the flag declines
 * with no output; Profile 5 maps or fails, flag or no flag. Every case below
 * is decided before the core needs a GPU. */
static unsigned acquired;
static uint8_t host_pixels[4 * 4 * 8];
static int count_acquire (void *user, void **data, int32_t *stride)
{
  (void) user; acquired++; *data = host_pixels; *stride = 4 * 8; return 1;
}
struct baseline_case {
  const char *name;
  uint8_t profile, compat;
  enum rog_dovi_destination destination;
  uint32_t target_flags;
  double max_nits;
  uint32_t format;
  bool record;
};
static void baseline_rules (void)
{
  size_t size = 0;
  AVDOVIMetadata *m = av_dovi_metadata_alloc (&size);
  av_dovi_get_header (m)->bl_bit_depth = 10;
  static const uint8_t rpu[8] = {0x19, 1, 2, 3, 4, 5, 6, 7};
  static uint8_t luma[16 * 2], chroma[8 * 2];
  const uint32_t witness = ROG_DOVI_TARGET_VALID | ROG_DOVI_TARGET_COMPOSED | ROG_DOVI_TARGET_RENDER_READY;
  const struct baseline_case cases[] = {
    {"no record", 0, 0, ROG_DOVI_DESTINATION_STANDARD_SDR_SRGB, 0, 616, ROG_DOVI_FORMAT_P010LE, false},
    {"no witness", 0, 0, ROG_DOVI_DESTINATION_DISPLAY_PQ, ROG_DOVI_TARGET_VALID, 616, ROG_DOVI_FORMAT_P010LE, true},
    {"depth differs from the record", 0, 0, ROG_DOVI_DESTINATION_DISPLAY_PQ, witness, 616, ROG_DOVI_FORMAT_NV12, true},
    {"non-HDR target", 0, 0, ROG_DOVI_DESTINATION_DISPLAY_PQ, witness, 100, ROG_DOVI_FORMAT_P010LE, true},
  };
  for (unsigned c = 0; c < sizeof (cases) / sizeof (cases[0]); c++) {
    for (int profile = 5; profile <= 8; profile += 3) {
      for (uint32_t flags = 0; flags <= ROG_DOVI_MAP_BASELINE_ON_DECLINE; flags++) {
        const struct baseline_case *k = &cases[c];
        struct rog_dovi_picture record = {.struct_size = sizeof (record),
            .libavutil_version = LIBAVUTIL_VERSION_INT, .rpu = rpu, .rpu_size = sizeof (rpu),
            .metadata = k->record ? m : NULL, .metadata_size = size, .has_config = 1,
            .config = config ((uint8_t) profile, profile == 5 ? 0 : 1, 0), .profile = profile,
            .width = 4, .height = 4, .has_geometry = 1, .geometry = {4, 4, 0, 0, 4, 4}};
        struct rog_dovi_planes picture = {.struct_size = sizeof (picture), .format = k->format,
            .storage_width = 4, .storage_height = 4, .width = 4, .height = 4,
            .data = {luma, chroma}, .stride = {8, 8}, .color_range = 1, .colorspace = 9,
            .color_primaries = 9, .color_trc = 16};
        struct rog_dovi_target target = {.struct_size = sizeof (target), .flags = k->target_flags,
            .generation = 1, .primaries = {0.708, 0.292, 0.170, 0.797, 0.131, 0.046, 0.3127, 0.3290},
            .min_nits = 0.005, .max_nits = k->max_nits, .reference_nits = 203,
            .encoding_reference_nits = 203, .encoding_max_nits = 10000};
        bool sdr = k->destination == ROG_DOVI_DESTINATION_STANDARD_SDR_SRGB;
        struct rog_dovi_output out = {.struct_size = sizeof (out), .kind = ROG_DOVI_OUTPUT_HOST,
            .width = 4, .height = 4, .host_format = sdr ? ROG_DOVI_FORMAT_RGBA : ROG_DOVI_FORMAT_RGBA64LE,
            .acquire = count_acquire};
        rog_dovi_mapper *mapper = rog_dovi_mapper_new (NULL);
        const char *error = NULL;
        acquired = 0;
        int r = rog_dovi_map_planes (mapper, &picture, NULL, &record, k->destination, &target,
            &out, flags, &error);
        char name[160];
        if (profile == 5) {
          snprintf (name, sizeof (name), "Profile 5 %s fails, flag %u", k->name, flags);
          require (r == -1 && rog_dovi_map_last_failure (mapper) == ROG_DOVI_FAILURE_CONTENT &&
              error && !acquired, name);
        } else if (!flags) {
          snprintf (name, sizeof (name), "Profile 8 %s declines with no output", k->name);
          require (r == 0 && !acquired && rog_dovi_map_last_decline (mapper), name);
        }
        /* Profile 8 with the flag renders its baseline: a GPU case, checked
         * through the GTK element's result 2 on the ROG. */
        bool used_gpu = mapper->vk != NULL;
        rog_dovi_mapper_free (mapper);
        if (profile == 5 || !flags) require (!used_gpu, "decided without a GPU");
      }
    }
  }
  /* A DMABuf output without the flag carries no planes. */
  rog_dovi_mapper *mapper = rog_dovi_mapper_new (NULL);
  uint64_t linear = 0;
  struct rog_dovi_planes picture = {.struct_size = sizeof (picture), .format = ROG_DOVI_FORMAT_P010LE,
      .storage_width = 4, .storage_height = 4, .width = 4, .height = 4, .data = {luma, chroma}, .stride = {8, 8}};
  struct rog_dovi_output out = {.struct_size = sizeof (out), .kind = ROG_DOVI_OUTPUT_DMABUF,
      .width = 4, .height = 4, .drm_fourcc = DRM_FORMAT_ABGR2101010, .modifiers = &linear, .num_modifiers = 1,
      .num_planes = 3};
  int r = rog_dovi_map_planes (mapper, &picture, NULL, NULL, ROG_DOVI_DESTINATION_STANDARD_SDR_SRGB,
      NULL, &out, 0, NULL);
  require (r == 0 && out.num_planes == 0 && out.planes[0].fd == -1, "declined DMABuf output has no planes");
  rog_dovi_mapper_free (mapper);
  av_free (m);
}

static void decline_names (void)
{
  for (uint32_t bit = 1; bit <= ROG_DOVI_DECLINE_OUTPUT_IMPORT; bit <<= 1) {
    bool named = bit == 1 || bit == 2 || bit == 32 || bit == 64 || bit == 128 ||
        bit == 256 || bit == 512 || bit == 1024;
    require (!!rog_dovi_map_decline_reason (bit) == named, "every decline bit is named");
  }
}

int main (void)
{
  require (rog_dovi_map_abi () == ROG_DOVI_MAP_ABI, "ABI");
  stream_rules ();
  destination_rules ();
  metadata_rules ();
  pitch_rules ();
  baseline_rules ();
  decline_names ();
  printf ("{\"checks\": %u, \"failures\": %u}\n", checks, failures);
  return failures != 0;
}
