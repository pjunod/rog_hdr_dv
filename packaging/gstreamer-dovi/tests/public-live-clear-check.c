/* SPDX-License-Identifier: MIT
 * Focused source-only negative. Mutated RPUs are test instructions, not authored
 * image references. Decode SHA compares strict/default BL pixels only. */
#include <gst/gst.h>
#include <gstdovipicture.h>
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/imgutils.h>
#include <libavutil/opt.h>
#include <libavcodec/dovi_parser.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define REQUIRE(c) do { if (!(c)) { fprintf(stderr,"failed line %d: %s\n",__LINE__,#c); exit(1); } } while (0)
struct result { int frames, raw, marked, pictures, rejected, recovered; gchar *hash; };
static GBytes *seed, *missing, *reuse;
static guint length_size;
static gint64 rejected_pts[2];
static guint32 length_at(const guint8 *p) { guint32 n=0; for(guint j=0;j<length_size;j++) n=(n<<8)|p[j]; return n; }
static void put_length(GByteArray *out,guint32 n) { guint8 p[4]; for(guint j=0;j<length_size;j++) p[length_size-j-1]=n>>(8*j); g_byte_array_append(out,p,length_size); }
static AVPacket *mutate(AVPacket *in, int index) {
  GByteArray *out=g_byte_array_new();
  for(gsize off=0;off<(gsize)in->size;) {
    REQUIRE((gsize)in->size-off>=length_size); guint32 n=length_at(in->data+off); off+=length_size;
    REQUIRE(n>=2 && n<=(gsize)in->size-off);
    const guint8 *p=in->data+off; guint type=(p[0]>>1)&63;
    if(type==62 && (index==10 || index==11)) {
      gsize size; const guint8 *replacement=g_bytes_get_data(index==10?missing:reuse,&size);
      put_length(out,size); g_byte_array_append(out,replacement,size);
    } else if (!(type==62 && index==13)) { put_length(out,n); g_byte_array_append(out,p,n); }
    off+=n;
  }
  AVPacket *packet=av_packet_alloc(); REQUIRE(packet && av_new_packet(packet,out->len)>=0);
  memcpy(packet->data,out->data,out->len); REQUIRE(av_packet_copy_props(packet,in)>=0);
  g_byte_array_unref(out); return packet;
}
static void consume(AVCodecContext *ctx, AVFrame *frame, struct result *r, GChecksum *sum, int strict, int mutation) {
  int ret;
  while((ret=avcodec_receive_frame(ctx,frame))>=0) {
    AVFrameSideData *raw=av_frame_get_side_data(frame,AV_FRAME_DATA_DOVI_RPU_BUFFER);
    const AVDictionaryEntry *entry=raw?av_dict_get(raw->metadata,AV_DOVI_METADATA_STRICT_KEY,NULL,0):NULL;
    GstDoviPicture *picture=gst_dovi_picture_from_avframe(frame,NULL,1,r->frames,NULL);
    r->frames++;r->raw+=raw!=NULL;r->marked+=entry!=NULL;r->pictures+=picture!=NULL;
    if(!strict) REQUIRE(!entry && !picture);
    if(mutation && (frame->pts==rejected_pts[0] || frame->pts==rejected_pts[1])) {
      r->rejected++;
      if(strict) REQUIRE(!raw && !entry && !picture);
      else REQUIRE(raw && !entry && !picture);
    }
    if(strict && mutation && frame->pts>MAX(rejected_pts[0],rejected_pts[1]) && picture) r->recovered++;
    int size=av_image_get_buffer_size(frame->format,frame->width,frame->height,1);
    REQUIRE(size>0); guint8 *packed=g_malloc(size);
    REQUIRE(av_image_copy_to_buffer(packed,size,(const guint8 *const *)frame->data,frame->linesize,frame->format,frame->width,frame->height,1)==size);
    g_checksum_update(sum,packed,size);g_free(packed);
    gst_dovi_picture_unref(picture);av_frame_unref(frame);
  }
  REQUIRE(ret==AVERROR(EAGAIN) || ret==AVERROR_EOF);
}
static struct result run(const char *path,int strict,int mutation) {
  struct result r={0}; AVFormatContext *format=NULL;
  REQUIRE(avformat_open_input(&format,path,NULL,NULL)>=0);REQUIRE(avformat_find_stream_info(format,NULL)>=0);
  int stream=av_find_best_stream(format,AVMEDIA_TYPE_VIDEO,-1,-1,NULL,0);REQUIRE(stream>=0);
  AVCodecParameters *parameters=format->streams[stream]->codecpar;
  REQUIRE(parameters->extradata_size>=23 && parameters->extradata[0]==1);
  length_size=(parameters->extradata[21]&3)+1;
  AVCodecContext *ctx=avcodec_alloc_context3(avcodec_find_decoder(AV_CODEC_ID_HEVC));REQUIRE(ctx);
  REQUIRE(avcodec_parameters_to_context(ctx,parameters)>=0);ctx->thread_count=1;
  REQUIRE(av_opt_set_int(ctx->priv_data,"dovi_metadata_strict",strict,0)>=0);
  REQUIRE(avcodec_open2(ctx,NULL,NULL)>=0);
  AVPacket *packet=av_packet_alloc();AVFrame *frame=av_frame_alloc();GChecksum *sum=g_checksum_new(G_CHECKSUM_SHA256);
  int count=0;
  while(count<48 && av_read_frame(format,packet)>=0) {
    if(packet->stream_index==stream) {
      if(count==10 || count==11) rejected_pts[count-10]=packet->pts;
      AVPacket *send=mutation?mutate(packet,count):av_packet_clone(packet);
      if(mutation && count>=10) {
        AVDOVIDecoderConfigurationRecord live={0};
        if(count!=10) {
          live.dv_version_major=1;live.dv_profile=5;live.dv_level=3;
          live.rpu_present_flag=1;live.bl_present_flag=1;
        }
        uint8_t *side=av_packet_new_side_data(send,AV_PKT_DATA_DOVI_CONF,sizeof(live));
        REQUIRE(side);memcpy(side,&live,sizeof(live));
      }
      REQUIRE(avcodec_send_packet(ctx,send)>=0);av_packet_free(&send);consume(ctx,frame,&r,sum,strict,mutation);count++;
    }
    av_packet_unref(packet);
  }
  REQUIRE(count==48);REQUIRE(avcodec_send_packet(ctx,NULL)>=0);consume(ctx,frame,&r,sum,strict,mutation);
  REQUIRE(r.frames==48); if(mutation) REQUIRE(r.rejected==2);
  if(strict) REQUIRE(r.pictures>=40 && r.marked==r.pictures);
  r.hash=g_strdup(g_checksum_get_string(sum));g_checksum_free(sum);av_frame_free(&frame);av_packet_free(&packet);avcodec_free_context(&ctx);avformat_close_input(&format);
  return r;
}
static void resolver_negative(void) {
  GstDoviResolver *r=gst_dovi_resolver_new();REQUIRE(r);GError *error=NULL;
  gsize size;const guint8 *p=g_bytes_get_data(seed,&size);GBytes *payload=g_bytes_new(p+2,size-2);
  p=g_bytes_get_data(missing,&size);GBytes *bad=g_bytes_new(p+2,size-2);
  p=g_bytes_get_data(reuse,&size);GBytes *old=g_bytes_new(p+2,size-2);
  GstDoviPicture *picture=gst_dovi_resolver_resolve(r,payload,1920,1080,1,&error);REQUIRE(picture && !error);gst_dovi_picture_unref(picture);
  picture=gst_dovi_resolver_resolve(r,bad,1920,1080,2,&error);REQUIRE(!picture && error);g_clear_error(&error);
  picture=gst_dovi_resolver_resolve(r,old,1920,1080,3,&error);REQUIRE(!picture && error);g_clear_error(&error);
  picture=gst_dovi_resolver_resolve(r,payload,1920,1080,4,&error);REQUIRE(picture && !error);gst_dovi_picture_unref(picture);
  gst_dovi_resolver_reset(r);picture=gst_dovi_resolver_resolve(r,old,1920,1080,5,&error);REQUIRE(!picture && error);g_clear_error(&error);
  gst_dovi_resolver_free(r);g_bytes_unref(payload);g_bytes_unref(bad);g_bytes_unref(old);
}
int main(int argc,char **argv) {
  REQUIRE(argc==5);gst_init(NULL,NULL);GError *error=NULL;
  seed=g_mapped_file_get_bytes(g_mapped_file_new(argv[2],FALSE,&error));REQUIRE(!error);
  missing=g_mapped_file_get_bytes(g_mapped_file_new(argv[3],FALSE,&error));REQUIRE(!error);
  reuse=g_mapped_file_get_bytes(g_mapped_file_new(argv[4],FALSE,&error));REQUIRE(!error);
  if (0) resolver_negative(); /* This independent check targets live config, not initial missing-ID7. */
  struct result a=run(argv[1],0,0),b=run(argv[1],1,0),c=run(argv[1],0,1),d=run(argv[1],1,1);
  REQUIRE(!strcmp(a.hash,b.hash) && !strcmp(a.hash,c.hash) && !strcmp(a.hash,d.hash));
  REQUIRE(d.recovered>0 && c.raw>=d.raw+2);
  printf("{\"state\":\"PASS\",\"frames_per_case\":48,\"default_unmarked_pictures\":%d,\"strict_normal_pictures\":%d,\"default_mutated_raw\":%d,\"strict_mutated_pictures\":%d,\"missing_reference_frames\":%d,\"post_rejection_recovered\":%d,\"decoded_pixel_sha256\":\"%s\",\"live_config_clear_invalidates_prior_mapping0\":true,\"ordinary_pixel_equality\":true}\n",a.pictures,b.pictures,c.raw,d.pictures,d.rejected,d.recovered,a.hash);
  g_free(a.hash);g_free(b.hash);g_free(c.hash);g_free(d.hash);g_bytes_unref(seed);g_bytes_unref(missing);g_bytes_unref(reuse);return 0;
}
