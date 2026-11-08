#include <stdlib.h>
#include <math.h>
#include <errno.h>
#include <assert.h>
#define AVERROR(x) (-(x))
static int parse_target_xy(const char *text, double xy[8])
{
    const char *p = text;
    for (int i = 0; i < 8; i++) {
        char *end;
        xy[i] = strtod(p, &end);
        if (end == p || !isfinite(xy[i]) || xy[i] < 0 || xy[i] > 1)
            return AVERROR(EINVAL);
        if (i < 7) {
            if (*end != '/') return AVERROR(EINVAL);
            p = end + 1;
        } else if (*end) {
            return AVERROR(EINVAL);
        }
    }
    for (int i = 0; i < 8; i += 2)
        if (xy[i + 1] <= 1e-9 || xy[i] + xy[i + 1] > 1.000001)
            return AVERROR(EINVAL);
    double ax = xy[0] - xy[4], ay = xy[1] - xy[5];
    double bx = xy[2] - xy[4], by = xy[3] - xy[5];
    double wx = xy[6] - xy[4], wy = xy[7] - xy[5];
    double det = ax * by - bx * ay;
    if (fabs(det) < 1e-9) return AVERROR(EINVAL);
    double a = (wx * by - bx * wy) / det;
    double b = (ax * wy - wx * ay) / det;
    if (a <= 0 || b <= 0 || a + b >= 1) return AVERROR(EINVAL);
    return 0;
}


int main(void) {
 double xy[8];
 assert(!parse_target_xy(".708/.292/.170/.797/.131/.046/.3127/.3290",xy));
 const char *bad[] = {
 "nan/.292/.170/.797/.131/.046/.3127/.3290",
 "inf/.292/.170/.797/.131/.046/.3127/.3290",
 ".708/0/.170/.797/.131/.046/.3127/.3290",
 ".708/.292/.708/.292/.131/.046/.3127/.3290",
 ".708/.292/.170/.797/.131/.046/.99/.001",
 ".708/.292/.170/.797/.131/.046/.3127",
 ".708/.292/.170/.797/.131/.046/.3127/.3290/1",
 ".708/.292/.170/.797/.131/.046/.3127/.3290x",
 "-.708/.292/.170/.797/.131/.046/.3127/.3290",
 ".708/.4/.170/.797/.131/.046/.3127/.3290",
 };
 for (unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++) assert(parse_target_xy(bad[i],xy)<0);
 return 0;
}
