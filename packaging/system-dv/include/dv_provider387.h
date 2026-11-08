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
/* Callback result: -1 mapping failure, 0 unsupported target, 1 mapped. */
DV_PROVIDER387_API int dv_provider387_map(void *priv, pl_gpu gpu, const uint8_t *rpu, size_t size,
 bool enhancement_layer_composed, const struct pl_color_space *target,
 pl_tex master, pl_tex *mapped,
 struct pl_color_space *mapped_color);
DV_PROVIDER387_API void dv_provider387_reset(void *priv);
DV_PROVIDER387_API const char *dv_provider387_provenance(void);
#endif
