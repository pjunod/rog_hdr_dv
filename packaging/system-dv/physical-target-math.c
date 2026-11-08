/* Source-level regression for the mpv physical-to-signal transport.
 * Build against the independently replayed mpv source; no private engine needed.
 * Compile/run only in the reviewed qualification batch.
 */
#include <assert.h>
#include <float.h>
#include <math.h>
#include "video/out/dovi_physical.h"

static double compositor_inverse(double signal, double display_ref,
                                  double display_encoding_max)
{
    /* Mutter add_luminance_mapping_op, with PQ EOTF normalized to its maximum. */
    return signal * display_ref / 203.0 * 10000.0 / display_encoding_max;
}

int main(void)
{
    float gain;
    assert(mp_dovi_transport_gain(142, 10000, .0004f, 616, &gain));
    assert(fabs((double)gain - 203.0 / 142.0) < 1e-7);
    assert(fabs(compositor_inverse(616.0 * gain, 142, 10000) - 616) < .0001);
    assert(fabs(compositor_inverse(.0004 * gain, 142, 10000) - .0004) < 1e-10);
    /* The old affine interpretation destroys this independently declared black. */
    assert((.0004 - .005) * (203.0 - 1e-6) / (142 - .005) + 1e-6 < 0);

    assert(mp_dovi_transport_gain(203, 10000, .0004f, 616, &gain));
    assert(gain == 1.0f);  /* No GPU PQ roundtrip is needed. */
    assert(mp_dovi_transport_gain(71, 10000, .0002f, 308, &gain));
    assert(fabs(compositor_inverse(308.0 * gain, 71, 10000) - 308) < .0001);
    /* A physical target change can keep normalized working headroom identical.
     * Renderer identity must therefore include the preserved physical generation.
     */
    assert(fabs(308.0 * gain - 616.0 * 203.0 / 142.0) < .0001);

    assert(!mp_dovi_transport_gain(0, 10000, .0004f, 616, &gain));
    assert(!mp_dovi_transport_gain(NAN, 10000, .0004f, 616, &gain));
    assert(!mp_dovi_transport_gain(INFINITY, 10000, .0004f, 616, &gain));
    assert(!mp_dovi_transport_gain(142, 0, .0004f, 616, &gain));
    assert(!mp_dovi_transport_gain(142, 10000, -1, 616, &gain));
    assert(!mp_dovi_transport_gain(142, 10000, 616, 616, &gain));
    assert(!mp_dovi_transport_gain(1, 10000, .0004f, 616, &gain));
    assert(!mp_dovi_transport_gain(FLT_MAX, 10000, FLT_MIN, 1, &gain));
    assert(mp_dovi_transport_gain(203, 10000, 0, 616, &gain));
    return 0;
}
