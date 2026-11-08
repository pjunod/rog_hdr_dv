/* SPDX-License-Identifier: MIT
 * Exact SPS conformance and bridge validation. No image-grade claim. */
#include <gst/gst.h>
#include <gstdovipicture.h>
#include <libavcodec/avcodec.h>
#include <libavcodec/dovi_parser.h>
#include <libavformat/avformat.h>
#include <libavutil/opt.h>
#include <stdio.h>
#include <stdlib.h>
#define REQUIRE(c) do { if (!(c)) { fprintf(stderr,"failed line %d: %s\n",__LINE__,#c); exit(1); } } while (0)
static void config_controls(void) {
  guint8 data[24]={1,0,16,53,16};
  GstCaps *caps=gst_caps_new_empty_simple("video/x-h265");
  GBytes *bytes=g_bytes_new(data,sizeof(data)),*copy=NULL;
  AVDOVIDecoderConfigurationRecord config;
  gst_dovi_caps_apply_stream_config(caps,bytes);
  REQUIRE(gst_dovi_caps_get_stream_config(caps,&config,&copy));
  REQUIRE(config.dv_profile==8 && config.dv_bl_signal_compatibility_id==1 && g_bytes_equal(bytes,copy));g_bytes_unref(copy);
  gst_dovi_caps_apply_stream_config(caps,NULL);
  REQUIRE(!gst_dovi_caps_get_stream_config(caps,&config,&copy) && !copy);
  GBytes *short_record=g_bytes_new(data,4);gst_dovi_caps_apply_stream_config(caps,short_record);
  REQUIRE(!gst_dovi_caps_get_stream_config(caps,&config,&copy) && copy && g_bytes_get_size(copy)==4);g_bytes_unref(copy);g_bytes_unref(short_record);
  data[5]=1;GBytes *invalid=g_bytes_new(data,24);gst_dovi_caps_apply_stream_config(caps,invalid);
  REQUIRE(!gst_dovi_caps_get_stream_config(caps,&config,&copy) && !copy);g_bytes_unref(invalid);data[5]=0;
  data[4]=16|(3<<2);GBytes *extended=g_bytes_new(data,24);gst_dovi_caps_apply_stream_config(caps,extended);
  REQUIRE(gst_dovi_caps_get_stream_config(caps,&config,&copy) && config.dv_md_compression==3);g_bytes_unref(copy);g_bytes_unref(extended);
  data[4]=16|(2<<2);invalid=g_bytes_new(data,24);gst_dovi_caps_apply_stream_config(caps,invalid);
  REQUIRE(!gst_dovi_caps_get_stream_config(caps,&config,&copy) && !copy);g_bytes_unref(invalid);g_bytes_unref(bytes);gst_caps_unref(caps);
}
int main(int argc,char **argv) {
  REQUIRE(argc==6 || argc==7);gst_init(NULL,NULL);config_controls();
  guint expected_x=atoi(argv[2]),expected_y=atoi(argv[3]),expected_width=atoi(argv[4]),expected_height=atoi(argv[5]);
  gboolean ignored=argc==7;
  AVFormatContext *format=NULL;REQUIRE(avformat_open_input(&format,argv[1],NULL,NULL)>=0);REQUIRE(avformat_find_stream_info(format,NULL)>=0);
  int stream=av_find_best_stream(format,AVMEDIA_TYPE_VIDEO,-1,-1,NULL,0);REQUIRE(stream>=0);
  AVCodecContext *ctx=avcodec_alloc_context3(avcodec_find_decoder(AV_CODEC_ID_HEVC));REQUIRE(ctx);
  REQUIRE(avcodec_parameters_to_context(ctx,format->streams[stream]->codecpar)>=0);ctx->thread_count=1;
  if(ignored) ctx->flags2|=AV_CODEC_FLAG2_IGNORE_CROP;
  REQUIRE(av_opt_set_int(ctx->priv_data,"dovi_metadata_strict",1,0)>=0);REQUIRE(avcodec_open2(ctx,NULL,NULL)>=0);
  AVPacket *packet=av_packet_alloc();AVFrame *frame=av_frame_alloc();guint frames=0,matched=0,negative_checks=0;
  while(frames<8 && av_read_frame(format,packet)>=0) {
    if(packet->stream_index==stream) {
      REQUIRE(avcodec_send_packet(ctx,packet)>=0);int ret;
      while((ret=avcodec_receive_frame(ctx,frame))>=0) {
        GstDoviPicture *picture=gst_dovi_picture_from_avframe(frame,NULL,1,frames,NULL);frames++;
        AVFrameSideData *raw=av_frame_get_side_data(frame,AV_FRAME_DATA_DOVI_RPU_BUFFER);
        if(ignored) REQUIRE(!picture);
        else if(raw) {
          REQUIRE(picture);const GstDoviGeometry *geometry=gst_dovi_picture_get_geometry(picture);
          REQUIRE(geometry->x==expected_x && geometry->y==expected_y && geometry->width==expected_width && geometry->height==expected_height);
          REQUIRE((guint)frame->width==expected_width && (guint)frame->height==expected_height);matched++;
          if(negative_checks==0) {
            AVFrame *bad=av_frame_clone(frame);REQUIRE(bad);AVFrameSideData *bad_raw=av_frame_get_side_data(bad,AV_FRAME_DATA_DOVI_RPU_BUFFER);
            REQUIRE(av_dict_set(&bad_raw->metadata,AV_DOVI_METADATA_GEOMETRY_PREFIX "x","1",0)>=0);
            GstDoviPicture *rejected=gst_dovi_picture_from_avframe(bad,NULL,1,0,NULL);REQUIRE(!rejected);negative_checks++;
            REQUIRE(av_dict_set(&bad_raw->metadata,AV_DOVI_METADATA_GEOMETRY_PREFIX "x","184467440737095516160",0)>=0);
            rejected=gst_dovi_picture_from_avframe(bad,NULL,1,0,NULL);REQUIRE(!rejected);negative_checks++;
            REQUIRE(av_dict_set(&bad_raw->metadata,AV_DOVI_METADATA_GEOMETRY_PREFIX "y",NULL,0)>=0);
            rejected=gst_dovi_picture_from_avframe(bad,NULL,1,0,NULL);REQUIRE(!rejected);negative_checks++;av_frame_free(&bad);
          }
        }
        gst_dovi_picture_unref(picture);av_frame_unref(frame);
      }
      REQUIRE(ret==AVERROR(EAGAIN));
    }
    av_packet_unref(packet);
  }
  REQUIRE(frames>=8 && (ignored || (matched>=7 && negative_checks==3)));
  printf("{\"state\":\"PASS\",\"frames\":%u,\"matched_active_pictures\":%u,\"geometry\":[%u,%u,%u,%u],\"ignore_crop_suppressed\":%s,\"geometry_negatives\":%u,\"config_complete_abbreviated_absent_reserved_extended_controls\":true}\n",frames,matched,expected_x,expected_y,expected_width,expected_height,ignored?"true":"false",negative_checks);
  av_frame_free(&frame);av_packet_free(&packet);avcodec_free_context(&ctx);avformat_close_input(&format);return 0;
}
