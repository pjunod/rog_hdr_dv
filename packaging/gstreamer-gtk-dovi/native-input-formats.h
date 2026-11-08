/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GTK_DOVI_NATIVE_INPUT_FORMATS_H
#define GTK_DOVI_NATIVE_INPUT_FORMATS_H
/* Private source contract: actual CPU import and negotiation share one table.
 * The third field limits allocator-backed accelerator domains to the proven
 * NV12/P010 family. Standard GST_MAP_READ returns host staging for these CUDA
 * and VA allocators; no device-pointer map flag or accelerator SDK is used. */
#define GTK_DOVI_NATIVE_INPUT_FORMATS(F) \
  F(RGBA, RGBA, FALSE) \
  F(BGRA, BGRA, FALSE) \
  F(RGB, RGB24, FALSE) \
  F(BGR, BGR24, FALSE) \
  F(RGBx, RGB0, FALSE) \
  F(BGRx, BGR0, FALSE) \
  F(RGBA64_LE, RGBA64LE, FALSE) \
  F(NV12, NV12, TRUE) \
  F(P010_10LE, P010LE, TRUE) \
  F(I420, YUV420P, FALSE) \
  F(I420_10LE, YUV420P10LE, FALSE)
/* Public caps strings, kept private to avoid adding CUDA/VA SDK dependencies. */
#define GTK_DOVI_CUDA_MEMORY_FEATURE "memory:CUDAMemory"
#define GTK_DOVI_VA_MEMORY_FEATURE "memory:VAMemory"
#endif
