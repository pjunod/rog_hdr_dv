#ifndef DV_PROVIDER_H
#define DV_PROVIDER_H
#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>
#include <libplacebo/gpu.h>
#include <libplacebo/log.h>
#include <libplacebo/colorspace.h>
#define DV_PROVIDER_ABI 1
#define DV_PROVIDER_API __attribute__((visibility("default")))
DV_PROVIDER_API uint32_t dv_provider_abi(void);
struct dv_provider;
enum dv_provider_primaries { DV_PROVIDER_BT2020=0, DV_PROVIDER_P3D65=1, DV_PROVIDER_BT709=2 };
struct dv_provider_target { double peak_nits, min_nits; enum dv_provider_primaries primaries; bool cm4_trims, cm29_trims; };
/* Context is renderer-owned and serialized on its GPU thread. The source is a
 * fully reconstructed native-size BT.2020/PQ RGB texture, never decoded YUV.
 * RPU is FFmpeg DOVI_RPU_BUFFER bytes (without two-byte HEVC NAL header).
 * Returned texture is context-owned, valid until next render or destroy.
 * Output remains BT.2020/PQ, already mapped to target; disable further tone map.
 * Caller owns profile/enhancement-layer reconstruction and target selection. */
DV_PROVIDER_API struct dv_provider *dv_provider_create(pl_gpu gpu, pl_log log);
DV_PROVIDER_API void dv_provider_destroy(struct dv_provider **ctx);
DV_PROVIDER_API pl_tex dv_provider_render(struct dv_provider *ctx, const uint8_t *rpu, size_t size,
 const struct dv_provider_target *target, pl_tex master, const char **error);
/* Callback result: -1 mapping failure, 0 unsupported target, 1 mapped. */
DV_PROVIDER_API int dv_provider_map(void *priv, pl_gpu gpu, const uint8_t *rpu, size_t size,
 const struct pl_color_space *target, pl_tex master, pl_tex *mapped,
 struct pl_color_space *mapped_color);
DV_PROVIDER_API void dv_provider_reset(void *priv);
DV_PROVIDER_API const char *dv_provider_provenance(void);
#endif
