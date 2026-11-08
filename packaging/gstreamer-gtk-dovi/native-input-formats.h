/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef GTK_DOVI_NATIVE_INPUT_FORMATS_H
#define GTK_DOVI_NATIVE_INPUT_FORMATS_H
/* Private source contract: the CPU importer and negotiation expand this same
 * table. GPU-memory caps are deliberately excluded until an importer exists. */
#define GTK_DOVI_NATIVE_INPUT_FORMATS(F) \
  F(RGBA, RGBA) \
  F(BGRA, BGRA) \
  F(RGB, RGB24) \
  F(BGR, BGR24) \
  F(RGBx, RGB0) \
  F(BGRx, BGR0) \
  F(RGBA64_LE, RGBA64LE) \
  F(NV12, NV12) \
  F(P010_10LE, P010LE) \
  F(I420, YUV420P) \
  F(I420_10LE, YUV420P10LE)
#endif
