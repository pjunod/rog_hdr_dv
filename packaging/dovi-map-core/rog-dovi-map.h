/* SPDX-License-Identifier: LGPL-2.1-or-later */
/* librog-dovi-map: the project's Dolby Vision per-picture mapping core.
 *
 * One owner of the qualification and mapping rules that the GTK element and
 * Firefox both use (docs/FIREFOX_DOLBY_VISION.md, section 4). A decoded
 * picture, its own Dolby record and a destination go in; a mapped RGB picture
 * comes out. No GLib or GStreamer types cross this ABI.
 *
 * Conventions:
 * - Every struct starts with struct_size; set it to sizeof the struct. The
 *   core rejects a struct smaller than the one it was built with.
 * - Call rog_dovi_map_abi() before anything else and compare it with
 *   ROG_DOVI_MAP_ABI.
 * - Colour fields use the ITU-T H.273 code points (the values of FFmpeg's
 *   AVCOL_* enums); chroma_location uses FFmpeg's AVChromaLocation values.
 * - One mapper is used by one thread at a time. Different mappers may be used
 *   concurrently; they share one Vulkan device per render node.
 * - Results: 1 mapped; 0 declined (no output unless the caller asked for
 *   ROG_DOVI_MAP_BASELINE_ON_DECLINE; never returned for Profile 5); -1
 *   failure, *error set to a static string. */
#ifndef ROG_DOVI_MAP_H
#define ROG_DOVI_MAP_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define ROG_DOVI_MAP_ABI 1
#define ROG_DOVI_MAP_API __attribute__((visibility("default")))

typedef struct rog_dovi_mapper rog_dovi_mapper;

enum rog_dovi_destination {
  /* BT.2020/PQ, reference white 203 cd/m2 and maximum 10000, already mapped
   * to the physical target. Requires the caller's per-view native render
   * witness (target flags VALID, COMPOSED and RENDER_READY). */
  ROG_DOVI_DESTINATION_DISPLAY_PQ = 0,
  /* Graded once to a logical 100 cd/m2 BT.709 target and emitted as
   * full-range sRGB. Needs no display target. */
  ROG_DOVI_DESTINATION_STANDARD_SDR_SRGB = 1,
};

/* Host-memory picture layouts: the GTK native input table. */
enum rog_dovi_format {
  ROG_DOVI_FORMAT_NONE = 0,
  ROG_DOVI_FORMAT_RGBA, ROG_DOVI_FORMAT_BGRA, ROG_DOVI_FORMAT_RGB24,
  ROG_DOVI_FORMAT_BGR24, ROG_DOVI_FORMAT_RGB0, ROG_DOVI_FORMAT_BGR0,
  ROG_DOVI_FORMAT_RGBA64LE, ROG_DOVI_FORMAT_NV12, ROG_DOVI_FORMAT_P010LE,
  ROG_DOVI_FORMAT_YUV420P, ROG_DOVI_FORMAT_YUV420P10LE,
};

/* Device selection. A node is the st_rdev of a /dev/dri/renderD* node; 0
 * means "no node". With no nodes at all the core uses libplacebo's default
 * Vulkan device selection (what the GTK element has always done). Otherwise
 * the mapper renders on the input node's device if one is given, else on the
 * output node's. DMABuf output is allocated on the output node; when it
 * differs from the rendering device the output is linear and must be
 * importable by the output node, otherwise the picture is declined. */
struct rog_dovi_mapper_params {
  uint32_t struct_size, reserved;
  uint64_t input_node, output_node;
};

/* The public fields of the stream's Dolby decoder configuration record. */
struct rog_dovi_stream_config {
  uint8_t version_major, version_minor, profile, level;
  uint8_t rpu_present, el_present, bl_present, bl_signal_compatibility_id;
  uint8_t md_compression, reserved[3];
};

enum rog_dovi_enhancement {
  ROG_DOVI_ENHANCEMENT_NOT_REQUIRED = 0,
  ROG_DOVI_ENHANCEMENT_UNRECONSTRUCTED = 1,
  ROG_DOVI_ENHANCEMENT_VERIFIED = 2,
};

/* Exact source geometry in luma pixels, before conformance cropping. */
struct rog_dovi_geometry {
  uint32_t coded_width, coded_height, x, y, width, height;
};

/* The picture's own Dolby record. Never a previous picture's: pass NULL for a
 * picture without one. metadata is a self-contained AVDOVIMetadata blob (as
 * av_dovi_metadata_alloc lays it out) produced with libavutil
 * libavutil_version (LIBAVUTIL_VERSION_INT); a blob from another libavutil
 * major, or with any part outside metadata_size, is treated as no record. */
struct rog_dovi_picture {
  uint32_t struct_size, libavutil_version;
  const uint8_t *rpu; size_t rpu_size;      /* DOVI_RPU_BUFFER bytes */
  const void *metadata; size_t metadata_size;
  uint32_t has_config;                      /* 0: configuration unknown */
  struct rog_dovi_stream_config config;
  uint32_t profile;                         /* the RPU's own profile */
  uint32_t enhancement;                     /* enum rog_dovi_enhancement */
  uint32_t width, height;                   /* native picture dimensions */
  uint32_t has_geometry;
  struct rog_dovi_geometry geometry;
};

#define ROG_DOVI_PICTURE_INTERLACED 1u      /* not a progressive picture */
#define ROG_DOVI_PICTURE_CORRUPTED 2u
#define ROG_DOVI_PICTURE_ALT_LINE_CHROMA 4u

/* A picture in host memory. storage_* is the allocated picture, width/height
 * the visible one; crop (when has_crop) places the visible picture inside the
 * storage. data/stride address each plane's first row of the storage. */
struct rog_dovi_planes {
  uint32_t struct_size, format;             /* enum rog_dovi_format */
  uint32_t storage_width, storage_height, width, height;
  uint32_t has_crop, crop_x, crop_y, crop_width, crop_height;
  const uint8_t *data[4];
  int32_t stride[4];
  int32_t color_range, colorspace, color_primaries, color_trc, chroma_location;
  int32_t sar_num, sar_den;
  uint32_t flags;                           /* ROG_DOVI_PICTURE_* */
};

/* A picture in DMABuf memory: DRM_FORMAT_NV12 or DRM_FORMAT_P010, two planes
 * (luma, interleaved chroma), one modifier. width/height are the visible
 * size; plane offsets and pitches may describe a larger allocation. The core
 * never takes ownership of the fds. */
struct rog_dovi_dmabuf_plane { int32_t fd; uint32_t offset, pitch; };
struct rog_dovi_dmabuf {
  uint32_t struct_size, width, height, drm_fourcc;
  uint64_t modifier;
  uint32_t num_planes, flags;               /* ROG_DOVI_PICTURE_* */
  struct rog_dovi_dmabuf_plane planes[4];
  int32_t color_range, colorspace, color_primaries, color_trc, chroma_location;
};

/* The physical target of the surface that presents the picture. primaries:
 * Rx Ry Gx Gy Bx By Wx Wy. encoding_*: the PQ buffer declaration (203 and
 * 10000 are the only qualified values). Ignored for the SDR destination. */
#define ROG_DOVI_TARGET_VALID 1u
#define ROG_DOVI_TARGET_COMPOSED 2u
#define ROG_DOVI_TARGET_RENDER_READY 4u
struct rog_dovi_target {
  uint32_t struct_size, flags;
  uint64_t generation;
  double primaries[8], min_nits, max_nits, reference_nits;
  double encoding_reference_nits, encoding_max_nits;
};

/* Output. HOST: the caller's memory, in host_format ROG_DOVI_FORMAT_RGBA64LE
 * for DISPLAY_PQ or ROG_DOVI_FORMAT_RGBA for the SDR destination. The core
 * calls acquire once, when it needs the memory; acquire returns nonzero and
 * fills data (first row) and stride (bytes, negative for bottom-up rows).
 * DMABUF: the core allocates with GBM on the output node, choosing from the
 * caller's modifiers (the compositor's), in drm_fourcc
 * DRM_FORMAT_ABGR2101010 or ABGR16161616 (DISPLAY_PQ) or ABGR2101010 or
 * ABGR8888 (SDR, full-range sRGB). On 1 (or a baseline 0) it fills modifier,
 * num_planes and planes; the caller owns and closes the fds. The picture is
 * complete (the GPU has finished) when the call returns. */
enum rog_dovi_output_kind { ROG_DOVI_OUTPUT_HOST = 1, ROG_DOVI_OUTPUT_DMABUF = 2 };
typedef int (*rog_dovi_acquire_host_fn)(void *user, void **data, int32_t *stride);
struct rog_dovi_output {
  uint32_t struct_size, kind;
  uint32_t width, height;
  int32_t color_range;                      /* DISPLAY_PQ host output only */
  uint32_t host_format;
  rog_dovi_acquire_host_fn acquire;
  void *acquire_user;
  uint32_t drm_fourcc, num_modifiers;
  const uint64_t *modifiers;
  uint64_t modifier;                        /* out */
  uint32_t num_planes, reserved;            /* out */
  struct rog_dovi_dmabuf_plane planes[4];   /* out */
};

/* What a declined Profile 8 (or Profile 7) picture produces.
 *
 * Flag set (the GTK element): the core renders the picture's ordinary
 * interpretation, as its decoder declared it, into the output in the
 * destination's encoding (BT.2020/PQ for DISPLAY_PQ, sRGB for the SDR
 * destination) and returns 0 with the output filled. The element reports
 * this as its result 2, "baseline re-encoded to the negotiated output".
 *
 * Flag unset (Firefox): the core returns 0 with no output. A host output's
 * acquire callback is not called, or its memory is left unwritten when the
 * decline is found after acquisition; a DMABuf output has num_planes 0 and no
 * fds. The caller presents its own decoded picture.
 *
 * Profile 5 never has an ordinary interpretation: with or without the flag,
 * a Profile 5 picture is mapped (1) or fails (-1, failure class
 * ROG_DOVI_FAILURE_CONTENT), and no output is produced for a failure. */
#define ROG_DOVI_MAP_BASELINE_ON_DECLINE 1u

/* Decline reasons (rog_dovi_map_last_decline bits). */
#define ROG_DOVI_DECLINE_NOT_ELIGIBLE 1u    /* no record, not native YUV, not progressive, depth, no witness */
#define ROG_DOVI_DECLINE_UNQUALIFIED 2u     /* per-picture metadata/geometry/enhancement */
#define ROG_DOVI_DECLINE_TARGET 32u         /* invalid or non-HDR target */
#define ROG_DOVI_DECLINE_PROVIDER 64u       /* provider declined */
#define ROG_DOVI_DECLINE_TRANSPORT 128u     /* render declaration/transport */
#define ROG_DOVI_DECLINE_ENHANCEMENT 256u   /* enhancement planes unavailable */
#define ROG_DOVI_DECLINE_COMPOSITION 512u   /* Profile 7 master not reconstructed */
#define ROG_DOVI_DECLINE_OUTPUT_IMPORT 1024u /* output node cannot import the output */

enum rog_dovi_failure {
  ROG_DOVI_FAILURE_NONE = 0,
  ROG_DOVI_FAILURE_CONTENT = 1,             /* the picture cannot be shown (Profile 5) */
  ROG_DOVI_FAILURE_INTERNAL = 2,
};

enum rog_dovi_log_level {
  ROG_DOVI_LOG_ERROR = 1, ROG_DOVI_LOG_WARN, ROG_DOVI_LOG_INFO,
  ROG_DOVI_LOG_DEBUG, ROG_DOVI_LOG_TRACE,
};
typedef void (*rog_dovi_log_fn)(void *user, int level, const char *message);

ROG_DOVI_MAP_API uint32_t rog_dovi_map_abi(void);
/* Process-wide. Messages above max_level are not produced; libplacebo's
 * own messages are forwarded at their level. fn may be NULL. */
ROG_DOVI_MAP_API void rog_dovi_map_set_log(rog_dovi_log_fn fn, void *user, int max_level);

/* Never NULL for valid params: the Vulkan device is created with the first
 * picture. NULL params is the same as no nodes. */
ROG_DOVI_MAP_API rog_dovi_mapper *rog_dovi_mapper_new(const struct rog_dovi_mapper_params *params);
ROG_DOVI_MAP_API void rog_dovi_mapper_free(rog_dovi_mapper *mapper);
/* Flush and seek: resets the provider's per-stream state. */
ROG_DOVI_MAP_API void rog_dovi_mapper_reset(rog_dovi_mapper *mapper);

ROG_DOVI_MAP_API int rog_dovi_map_planes(rog_dovi_mapper *mapper,
    const struct rog_dovi_planes *picture, const struct rog_dovi_planes *enhancement,
    const struct rog_dovi_picture *record, enum rog_dovi_destination destination,
    const struct rog_dovi_target *target, struct rog_dovi_output *output,
    uint32_t flags, const char **error);
ROG_DOVI_MAP_API int rog_dovi_map_dmabuf(rog_dovi_mapper *mapper,
    const struct rog_dovi_dmabuf *picture, const struct rog_dovi_planes *enhancement,
    const struct rog_dovi_picture *record, enum rog_dovi_destination destination,
    const struct rog_dovi_target *target, struct rog_dovi_output *output,
    uint32_t flags, const char **error);

/* Reasons (ROG_DOVI_DECLINE_* bits) and failure class of the last call. */
ROG_DOVI_MAP_API uint32_t rog_dovi_map_last_decline(const rog_dovi_mapper *mapper);
ROG_DOVI_MAP_API int rog_dovi_map_last_failure(const rog_dovi_mapper *mapper);
/* The named reason for one decline bit, or NULL. */
ROG_DOVI_MAP_API const char *rog_dovi_map_decline_reason(uint32_t bit);

/* Bit (1u << profile) for each profile the core and the installed provider
 * can map on the device params selects, established by creating a provider.
 * Profile 7 needs a decoded enhancement picture. 0 if none. */
ROG_DOVI_MAP_API uint32_t rog_dovi_map_profiles(const struct rog_dovi_mapper_params *params);

/* Stream qualification: 5 (compatibility 0), 8 (compatibility 1), 7
 * (compatibility 6 with enhancement layer, only with a FEL decoder) or 0.
 * Version 1.0, RPU and base layer present, uncompressed metadata. */
ROG_DOVI_MAP_API uint32_t rog_dovi_map_stream_profile(
    const struct rog_dovi_stream_config *config, int fel_decoder);
/* Profile 5 single layer: no ordinary base-layer interpretation exists. */
ROG_DOVI_MAP_API int rog_dovi_map_profile5_has_no_base_fallback(
    const struct rog_dovi_stream_config *config);
/* Profile 5 shows only on the SDR destination or with the per-view native
 * render witness (target flags VALID, RENDER_READY and COMPOSED). */
ROG_DOVI_MAP_API int rog_dovi_map_profile5_destination_supported (
    const struct rog_dovi_stream_config *config, enum rog_dovi_destination destination,
    const struct rog_dovi_target *physical);
/* Every public field equal (never struct padding). */
ROG_DOVI_MAP_API int rog_dovi_map_same_config(const struct rog_dovi_stream_config *a,
    const struct rog_dovi_stream_config *b);
#ifdef __cplusplus
}
#endif
#endif
