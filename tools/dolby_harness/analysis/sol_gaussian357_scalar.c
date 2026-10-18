/* Fixed US10540920B2 Eq5 hybrid on PQ(Y), NOT the full patent/IPT model.
 * Independently implemented diagnostic, no third-party implementation copied.
 * All arithmetic is binary64; source binary32 is only immutable storage.
 */
#include <float.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

_Static_assert(DBL_MANT_DIG == 53 && sizeof(double) == 8, "binary64 required");
_Static_assert(FLT_MANT_DIG == 24 && sizeof(float) == 4, "binary32 required");
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "little endian required"
#endif
#define W 4096
#define H 2160
#define N ((size_t)W * H)
#define NS ((W / 16) * (H / 16))
static double pq(double x) {
    if (!isfinite(x) || x < 0 || x > 10000) return NAN;
    double p = pow(x / 10000, 2610.0 / 16384);
    return pow((3424.0 / 4096 + (2413.0 / 128) * p) /
               (1 + (2392.0 / 128) * p), 2523.0 / 32);
}
static double eotf(double q) {
    if (!isfinite(q) || q < 0 || q > 1) return NAN;
    double p = pow(q, 32.0 / 2523);
    return 10000 * pow(fmax(p - 3424.0 / 4096, 0) /
                        (2413.0 / 128 - (2392.0 / 128) * p), 16384.0 / 2610);
}
static int edge(int x, int n) { return x < 0 ? 0 : x >= n ? n - 1 : x; }
int main(int argc, char **argv) {
    if (argc != 4) return 2;
    FILE *ctl = fopen(argv[1], "r"), *src = fopen(argv[2], "rb");
    if (!ctl || !src) return 3;
    double mat[9], s, o, p, a, b, c;
    for (int j = 0; j < 9; j++) if (fscanf(ctl, "%lf", &mat[j]) != 1) return 4;
    if (fscanf(ctl, "%lf %lf %lf %lf %lf %lf", &s,&o,&p,&a,&b,&c) != 6) return 4;
    fclose(ctl);
    double *io=malloc(N*sizeof(double)), *im=malloc(N*sizeof(double));
    double *tmp=malloc(N*sizeof(double)), *yy=malloc(N*sizeof(double));
    double (*sample)[8]=calloc(NS, sizeof(*sample));
    if (!io || !im || !tmp || !yy || !sample) return 5;
    uint64_t invalid=0, affine_neg=0, floor_n=0, rational_neg=0, zero_y=0;
    uint64_t scalar_bad=0, projected=0, spatial_bad=0, black_positive=0;
    uint64_t edge_pixels=0, taps_x=0, taps_y=0;
    double q0=pq(0), h[11], sum=0;
    for (int k=-5; k<=5; k++) { h[k+5]=exp(-(double)(k*k)/8); sum+=h[k+5]; }
    for (int k=0; k<11; k++) h[k]/=sum;
    for (int y=0; y<H; y++) for (int x=0; x<W; x++) {
        size_t i=(size_t)y*W+x; float stored[3]; double lin[3], rgb[3];
        if (fread(stored, sizeof(float), 3, src)!=3) return 6;
        for (int j=0; j<3; j++) lin[j]=eotf(stored[j]);
        for (int j=0; j<3; j++) rgb[j]=mat[3*j]*lin[0]+mat[3*j+1]*lin[1]+mat[3*j+2]*lin[2];
        double Y=.2627*rgb[0]+.6780*rgb[1]+.0593*rgb[2];
        yy[i]=Y; io[i]=pq(Y); im[i]=NAN;
        int bad=0;
        for (int j=0; j<3; j++) bad |= !isfinite(rgb[j]) || rgb[j]<0 || rgb[j]>10000;
        if (bad || !isfinite(io[i])) { invalid++; }
        else if (Y==0) { im[i]=q0; zero_y++; }
        else {
            double affine=s*io[i]+o;
            double power=pow(fmax(0,affine),p), q=fmax(1e-5,power);
            affine_neg+=affine<0; floor_n+=power<1e-5;
            if (!isfinite(affine) || affine>1 || !isfinite(q) || q>1) scalar_bad++;
            else {
                double yt=eotf(q), den=1+c*yt, raw=(a+b*yt)/den;
                rational_neg+=raw<0;
                if (!isfinite(raw) || den<=0) scalar_bad++;
                else { im[i]=pq(fmax(0,raw)); if (!isfinite(im[i])) scalar_bad++; }
            }
        }
        if (x%16==0 && y%16==0) {
            size_t j=(size_t)(y/16)*(W/16)+x/16;
            for (int k=0; k<3; k++) sample[j][k]=rgb[k];
            sample[j][3]=Y; sample[j][4]=io[i]; sample[j][5]=im[i];
        }
    }
    if (fgetc(src)!=EOF || ferror(src)) return 7;
    fclose(src);
    for (int y=0; y<H; y++) for (int x=0; x<W; x++) {
        double v=0;
        for (int k=-5; k<=5; k++) {
            int xx=edge(x+k,W); taps_x+=(xx!=x+k);
            size_t j=(size_t)y*W+xx; v+=h[k+5]*(io[j]-im[j]);
        }
        tmp[(size_t)y*W+x]=v;
    }
    for (int y=0; y<H; y++) for (int x=0; x<W; x++) {
        size_t i=(size_t)y*W+x; double v=0;
        edge_pixels+=(x<5 || x>=W-5 || y<5 || y>=H-5);
        for (int k=-5; k<=5; k++) {
            int y2=edge(y+k,H); taps_y+=(y2!=y+k); v+=h[k+5]*tmp[(size_t)y2*W+x];
        }
        double raw=io[i]-v, is=raw;
        if (is<q0) { is=q0; projected++; }
        spatial_bad+=(!isfinite(is) || is>1);
        black_positive+=(yy[i]==0 && is>q0 && is<=1);
        if (x%16==0 && y%16==0) {
            size_t j=(size_t)(y/16)*(W/16)+x/16;
            sample[j][6]=raw; sample[j][7]=is;
        }
    }
    FILE *out=fopen(argv[3], "wbx"); if (!out) return 8;
    if (fwrite(sample,sizeof(*sample),NS,out)!=NS || fclose(out)) return 9;
    printf("{\"source_invalid\":%llu,\"scalar_invalid\":%llu,\"spatial_invalid\":%llu,"
           "\"affine_negative\":%llu,\"pq_floor\":%llu,\"rational_negative\":%llu,"
           "\"Y_zero_achromatic_convention_pixels\":%llu,\"Y_zero_positive_map_pixels\":%llu,"
           "\"Is_below_PQ0_projected\":%llu,\"edge_replication_pixels\":%llu,"
           "\"horizontal_replicated_taps\":%llu,\"vertical_replicated_taps\":%llu,\"h\":[",
           (unsigned long long)invalid,(unsigned long long)scalar_bad,(unsigned long long)spatial_bad,
           (unsigned long long)affine_neg,(unsigned long long)floor_n,(unsigned long long)rational_neg,
           (unsigned long long)zero_y,(unsigned long long)black_positive,(unsigned long long)projected,
           (unsigned long long)edge_pixels,(unsigned long long)taps_x,(unsigned long long)taps_y);
    for (int k=0; k<11; k++) printf("%s%.17g",k?",":"",h[k]);
    sum=0; for (int k=0; k<11; k++) sum+=h[k];
    printf("],\"h_sum\":%.17g,\"full_scalar_pixels\":%zu,\"lattice_pixels\":%d}\n",sum,N,NS);
    free(sample);free(io);free(im);free(tmp);free(yy); return 0;
}
