#ifndef DV_PROVIDER387_H
#define DV_PROVIDER387_H
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <libplacebo/gpu.h>
#include <libplacebo/log.h>
#include <libplacebo/colorspace.h>
#define DV_PROVIDER387_ABI 1
#define DV_PROVIDER387_API __attribute__((visibility("default")))
DV_PROVIDER387_API uint32_t dv_provider387_abi(void);
struct dv_provider387;
enum dv_provider387_primaries { DV_PROVIDER387_BT2020=0, DV_PROVIDER387_P3D65=1, DV_PROVIDER387_BT709=2 };
struct dv_provider387_target { double peak_nits, min_nits; enum dv_provider387_primaries primaries; bool cm4_trims, cm29_trims; };
/* Additive target v2. The v1 struct, ABI number and functions stay unchanged.
 * xy is Rx,Ry,Gx,Gy,Bx,By,Wx,Wy. RAW_XY requests validated physical primaries,
 * never source/mastering or nominal signal primaries. Named remains the
 * complete fallback when custom creative-gamut weighting is unavailable. */
#define DV_PROVIDER387_TARGET_V2_VERSION 2
#define DV_PROVIDER387_TARGET_RAW_XY 1u
struct dv_provider387_target_v2 {
 uint32_t struct_size, version;
 struct dv_provider387_target named;
 double xy[8];
 uint32_t flags, reserved;
};
enum dv_provider387_target_strategy {
 DV_PROVIDER387_TARGET_NAMED = 0,
 DV_PROVIDER387_TARGET_RAW_XY_NEUTRAL_CM4 = 1,
 DV_PROVIDER387_TARGET_NAMED_CREATIVE_FALLBACK = 2,
 DV_PROVIDER387_TARGET_NAMED_INVALID_XY_FALLBACK = 3,
};
/* Context is renderer-owned and serialized on its GPU thread. The source is a
 * fully reconstructed native-size BT.2020/PQ RGB texture, never decoded YUV.
 * RPU is FFmpeg DOVI_RPU_BUFFER bytes (without two-byte HEVC NAL header).
 * Returned texture is context-owned, valid until next render or destroy.
 * Output remains BT.2020/PQ, already mapped to target; disable further tone map.
 * enhancement_layer_composed must describe the current master after successful
 * native size base/enhancement reconstruction. Caller owns target selection. */
DV_PROVIDER387_API struct dv_provider387 *dv_provider387_create(pl_gpu gpu, pl_log log);
DV_PROVIDER387_API void dv_provider387_destroy(struct dv_provider387 **ctx);
DV_PROVIDER387_API pl_tex dv_provider387_render(struct dv_provider387 *ctx, const uint8_t *rpu, size_t size,
 bool enhancement_layer_composed, const struct dv_provider387_target *target,
 pl_tex master, const char **error);
/* Initialize struct_size=sizeof(target), version=TARGET_V2_VERSION and
 * reserved=0. Unknown flags/header versions are errors. Invalid raw xy and
 * unsupported creative-gamut models retain the complete named mapping. */
DV_PROVIDER387_API pl_tex dv_provider387_render_v2(struct dv_provider387 *ctx,
 const uint8_t *rpu, size_t size, bool enhancement_layer_composed,
 const struct dv_provider387_target_v2 *target, pl_tex master, const char **error);
/* Callback result: -1 mapping failure, 0 unsupported target, 1 mapped. */
DV_PROVIDER387_API int dv_provider387_map(void *priv, pl_gpu gpu, const uint8_t *rpu, size_t size,
 bool enhancement_layer_composed, const struct pl_color_space *target,
 pl_tex master, pl_tex *mapped,
 struct pl_color_space *mapped_color);
/* Same mapped-pixel contract as map(). NULL explicit_target selects physical
 * xy from target->hdr.prim and derives its named fallback normally. A non-NULL
 * explicit target retains the caller's named fallback. Callers must not
 * substitute source/mastering primaries for the actual physical display.
 * Discover this optional symbol at runtime; absence uses the v1 named path. */
DV_PROVIDER387_API int dv_provider387_map_v2(void *priv, pl_gpu gpu,
 const uint8_t *rpu, size_t size, bool enhancement_layer_composed,
 const struct pl_color_space *target, pl_tex master, pl_tex *mapped,
 struct pl_color_space *mapped_color,
 const struct dv_provider387_target_v2 *explicit_target);
DV_PROVIDER387_API uint32_t dv_provider387_last_target_strategy(const struct dv_provider387 *ctx);
DV_PROVIDER387_API void dv_provider387_reset(void *priv);
DV_PROVIDER387_API const char *dv_provider387_provenance(void);
#endif
