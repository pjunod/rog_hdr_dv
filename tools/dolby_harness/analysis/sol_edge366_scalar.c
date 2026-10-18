/* Independent US10540920B2 paragraph0078 example hybrid on normalized PQ(Y).
 * Only derivative neighborhoods are newly prepared. No old Gaussian/output/metric.
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
#define N ((size_t)W*H)
#define NS ((W/16)*(H/16))
static double pq(double x) {
    if (!isfinite(x) || x<0 || x>10000) return NAN;
    double p=pow(x/10000,2610.0/16384);
    return pow((3424.0/4096+(2413.0/128)*p)/(1+(2392.0/128)*p),2523.0/32);
}
static double eotf(double q) {
    if (!isfinite(q) || q<0 || q>1) return NAN;
    double p=pow(q,32.0/2523);
    return 10000*pow(fmax(p-3424.0/4096,0)/(2413.0/128-(2392.0/128)*p),16384.0/2610);
}
static int edge(int x,int n) { return x<0?0:x>=n?n-1:x; }
static double mat[9],s,o,p,a,b,c;
static uint64_t source_bad,scalar_bad,prepared,zero_y,affine_neg,floor_n,rational_neg;
static double primitive(const float stored[3],double values[6]) {
    double lin[3],rgb[3];
    for (int j=0;j<3;j++) lin[j]=eotf(stored[j]);
    for (int j=0;j<3;j++) rgb[j]=mat[3*j]*lin[0]+mat[3*j+1]*lin[1]+mat[3*j+2]*lin[2];
    double Y=.2627*rgb[0]+.6780*rgb[1]+.0593*rgb[2];
    double io=pq(Y),im=NAN; int bad=0;
    for (int j=0;j<3;j++) bad |= !isfinite(rgb[j]) || rgb[j]<0 || rgb[j]>10000;
    if (bad || !isfinite(io)) source_bad++;
    else if (Y==0) { im=pq(0); zero_y++; }
    else {
        double affine=s*io+o;
        double power=pow(fmax(0,affine),p),q=fmax(1e-5,power);
        affine_neg+=affine<0; floor_n+=power<1e-5;
        if (!isfinite(affine) || affine>1 || !isfinite(q) || q>1) scalar_bad++;
        else {
            double yt=eotf(q),den=1+c*yt,raw=(a+b*yt)/den;
            rational_neg+=raw<0;
            if (!isfinite(raw) || den<=0) scalar_bad++;
            else { im=pq(fmax(0,raw)); if (!isfinite(im)) scalar_bad++; }
        }
    }
    for (int j=0;j<3;j++) values[j]=rgb[j];
    values[3]=Y; values[4]=io; values[5]=im;
    prepared++;
    return io-im;
}
int main(int argc,char **argv) {
    if (argc!=5) return 2;
    FILE *ctl=fopen(argv[1],"r"),*src=fopen(argv[2],"rb"),*old=fopen(argv[3],"rb");
    if (!ctl || !src || !old) return 3;
    for (int j=0;j<9;j++) if (fscanf(ctl,"%lf",&mat[j])!=1) return 4;
    if (fscanf(ctl,"%lf %lf %lf %lf %lf %lf",&s,&o,&p,&a,&b,&c)!=6) return 4;
    fclose(ctl);
    float (*pixels)[3]=malloc(N*sizeof(*pixels));
    double *delta=malloc(N*sizeof(*delta));
    unsigned char *seen=calloc(N,1);
    double (*prior)[8]=malloc(NS*sizeof(*prior)),(*out)[5]=malloc(NS*sizeof(*out));
    if (!pixels || !delta || !seen || !prior || !out) return 5;
    if (fread(pixels,sizeof(*pixels),N,src)!=N || fgetc(src)!=EOF || ferror(src)) return 6;
    if (fread(prior,sizeof(*prior),NS,old)!=NS || fgetc(old)!=EOF || ferror(old)) return 7;
    fclose(src); fclose(old);
    double h[11],d[11],sum=0,q0=pq(0),max_center_error=0;
    for (int k=-5;k<=5;k++) { h[k+5]=exp(-(double)(k*k)/8); sum+=h[k+5]; }
    for (int k=-5;k<=5;k++) { h[k+5]/=sum; d[k+5]=-k*h[k+5]/4; }
    uint64_t taps=0,replicated=0,spatial_bad=0,projected=0,center_mismatch=0;
    for (int y=0;y<H;y+=16) for (int x=0;x<W;x+=16) {
        size_t j=(size_t)(y/16)*(W/16)+x/16; double dx=0,dy=0;
        for (int l=-5;l<=5;l++) for (int k=-5;k<=5;k++) {
            int xx=edge(x+k,W),yy=edge(y+l,H); size_t i=(size_t)yy*W+xx;
            taps++; replicated+=(xx!=x+k || yy!=y+l);
            if (!seen[i]) {
                double v[6]; delta[i]=primitive(pixels[i],v); seen[i]=1;
                if (xx==x && yy==y) for (int z=0;z<6;z++) {
                    double error=fabs(v[z]-prior[j][z]);
                    if (!isfinite(v[z]) || !isfinite(prior[j][z]) || error!=0) center_mismatch++;
                    max_center_error=fmax(max_center_error,error);
                }
            }
            dx+=d[k+5]*h[l+5]*delta[i];
            dy+=h[k+5]*d[l+5]*delta[i];
        }
        double alpha=fmin(1,fmax(0,fabs(dx)+fabs(dy)));
        /* Recover the exact old filtered delta from PREprojection rawIs. */
        double io=prior[j][4],im=prior[j][5],filtered=io-prior[j][6];
        double raw=io-alpha*(io-im)-(1-alpha)*filtered,is=raw;
        if (is<q0) { is=q0; projected++; }
        spatial_bad+=!isfinite(dx) || !isfinite(dy) || !isfinite(raw) || !isfinite(is) || is>1;
        out[j][0]=dx; out[j][1]=dy; out[j][2]=alpha; out[j][3]=raw; out[j][4]=is;
    }
    FILE *dest=fopen(argv[4],"wbx"); if (!dest) return 8;
    if (fwrite(out,sizeof(*out),NS,dest)!=NS || fclose(dest)) return 9;
    printf("{\"schema\":\"le-f64-dx-dy-alpha-rawIs-projectedIs-v1\",\"source_invalid\":%llu,\"scalar_invalid\":%llu,\"spatial_invalid\":%llu,\"prepared_unique_neighborhood_pixels\":%llu,\"neighborhood_taps\":%llu,\"replicated_taps\":%llu,\"center_mismatch_components\":%llu,\"center_max_abs_error\":%.17g,\"Is_below_PQ0_projected_lattice\":%llu,\"Y_zero_neighborhood\":%llu,\"affine_negative\":%llu,\"pq_floor\":%llu,\"rational_negative\":%llu,\"h\":[",
        (unsigned long long)source_bad,(unsigned long long)scalar_bad,(unsigned long long)spatial_bad,
        (unsigned long long)prepared,(unsigned long long)taps,(unsigned long long)replicated,
        (unsigned long long)center_mismatch,max_center_error,(unsigned long long)projected,
        (unsigned long long)zero_y,(unsigned long long)affine_neg,(unsigned long long)floor_n,(unsigned long long)rational_neg);
    double hs=0,ds=0;
    for (int k=0;k<11;k++) { printf("%s%.17g",k?",":"",h[k]); hs+=h[k]; }
    printf("],\"d\":[");
    for (int k=0;k<11;k++) { printf("%s%.17g",k?",":"",d[k]); ds+=d[k]; }
    printf("],\"h_sum\":%.17g,\"d_sum\":%.17g,\"lattice_pixels\":%d}\n",hs,ds,NS);
    free(pixels);free(delta);free(seen);free(prior);free(out);return 0;
}
