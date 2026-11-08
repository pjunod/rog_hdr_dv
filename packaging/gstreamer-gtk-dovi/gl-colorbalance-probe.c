/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include <gst/gst.h>
#include <gst/app/gstappsrc.h>
#include <gst/app/gstappsink.h>
#include <gst/gl/gl.h>
#include <string.h>

typedef struct { guint seen, with_meta, rgba16; } Witness;
static GstPadProbeReturn witness (GstPad *pad, GstPadProbeInfo *info, gpointer data)
{
  Witness *w=data; GstBuffer *b=GST_PAD_PROBE_INFO_BUFFER(info); (void)pad;
  if (!b) return GST_PAD_PROBE_OK;
  w->seen++;
  w->with_meta += gst_buffer_get_custom_meta(b,"QualificationColorProvenance")!=NULL;
  if (gst_buffer_n_memory(b)>0) {
    GstMemory *m=gst_buffer_peek_memory(b,0);
    if (gst_is_gl_memory(m))
      w->rgba16 += gst_gl_memory_get_texture_format((GstGLMemory*)m)==GST_GL_RGBA16;
  }
  return GST_PAD_PROBE_OK;
}
int main(int argc,char **argv)
{
  gst_init(&argc,&argv);
  const char *mode=argc>1?argv[1]:"neutral";
  const char *property=!strcmp(mode,"brightness")?"brightness=0.1":
      !strcmp(mode,"contrast")?"contrast=1.1":
      !strcmp(mode,"saturation")?"saturation=0.5":"";
  gboolean neutral=!strcmp(mode,"neutral");
  if (!neutral && !*property) return 2;
  const gchar *tags[]={GST_META_TAG_VIDEO_STR,GST_META_TAG_VIDEO_SIZE_STR,
      GST_META_TAG_VIDEO_COLORSPACE_STR,NULL};
  gst_meta_register_custom("QualificationColorProvenance",tags,NULL,NULL,NULL);
  gchar *desc=g_strdup_printf("appsrc name=src format=time ! "
      "video/x-raw,format=RGBA64_LE,width=256,height=16,framerate=1/1 ! "
      "glupload name=upload ! glcolorbalance name=balance %s ! "
      "video/x-raw(memory:GLMemory),format=RGBA64_LE ! "
      "gldownload ! video/x-raw,format=RGBA64_LE ! appsink name=out sync=false",property);
  GError *error=NULL; GstElement *p=gst_parse_launch(desc,&error);g_free(desc);
  if (!p || error) {g_printerr("parse: %s\n",error?error->message:"NULL");return 3;}
  GstElement *src=gst_bin_get_by_name(GST_BIN(p),"src");
  GstElement *out=gst_bin_get_by_name(GST_BIN(p),"out");
  GstElement *upload=gst_bin_get_by_name(GST_BIN(p),"upload");
  GstElement *balance=gst_bin_get_by_name(GST_BIN(p),"balance");
  Witness before={0},after={0};
  GstPad *pad=gst_element_get_static_pad(upload,"src");
  gst_pad_add_probe(pad,GST_PAD_PROBE_TYPE_BUFFER,witness,&before,NULL);gst_object_unref(pad);
  pad=gst_element_get_static_pad(balance,"src");
  gst_pad_add_probe(pad,GST_PAD_PROBE_TYPE_BUFFER,witness,&after,NULL);gst_object_unref(pad);
  GstBuffer *b=gst_buffer_new_allocate(NULL,4096*8,NULL);GstMapInfo m;
  gst_buffer_map(b,&m,GST_MAP_WRITE);
  guint16 *reference=g_new(guint16,4096*4);
  for(guint i=0;i<4096;i++) {
    reference[i*4]=GUINT16_TO_LE(8192+i*8);
    reference[i*4+1]=GUINT16_TO_LE(12288+i*6);
    reference[i*4+2]=GUINT16_TO_LE(16384+i*4);
    reference[i*4+3]=GUINT16_TO_LE(65535);
  }
  memcpy(m.data,reference,m.size);gst_buffer_unmap(b,&m);
  gst_buffer_add_custom_meta(b,"QualificationColorProvenance");GST_BUFFER_PTS(b)=0;
  GST_BUFFER_DURATION(b)=GST_SECOND;
  gst_element_set_state(p,GST_STATE_PLAYING);
  GstFlowReturn pushed=gst_app_src_push_buffer(GST_APP_SRC(src),b);
  gst_app_src_end_of_stream(GST_APP_SRC(src));
  GstSample *sample=gst_app_sink_try_pull_sample(GST_APP_SINK(out),15*GST_SECOND);
  guint changed=0,lowbits=0,unique=0,max_delta=0;gboolean values[65536]={FALSE};
  if(sample && gst_buffer_map(gst_sample_get_buffer(sample),&m,GST_MAP_READ)) {
    if(m.size==4096*8) for(guint i=0;i<4096;i++) {
      const guint16 *v=(const guint16*)m.data;
      guint x=GUINT16_FROM_LE(v[i*4]);
      lowbits+=(x%257)!=0; if(!values[x]){values[x]=TRUE;unique++;}
      for(guint c=0;c<3;c++) {
        guint a=GUINT16_FROM_LE(v[i*4+c]),z=GUINT16_FROM_LE(reference[i*4+c]);
        guint d=a>z?a-z:z-a;changed+=d>1;max_delta=MAX(max_delta,d);
      }
    }
    gst_buffer_unmap(gst_sample_get_buffer(sample),&m);
  }
  gboolean pass=pushed==GST_FLOW_OK && sample && before.seen==1 && before.with_meta==1 &&
      before.rgba16==1 && after.seen==1 && after.rgba16==1 &&
      after.with_meta==(neutral?1u:0u) && unique>256 && lowbits>256 &&
      (neutral?max_delta<=1:changed>100);
  g_print("{\"mode\":\"%s\",\"pass\":%s,\"input_meta\":%u,\"output_meta\":%u,"
      "\"input_rgba16\":%u,\"output_rgba16\":%u,\"unique_red\":%u,"
      "\"red_not_8bit_replicated\":%u,\"changed_components\":%u,\"max_delta\":%u}\n",
      mode,pass?"true":"false",before.with_meta,after.with_meta,before.rgba16,
      after.rgba16,unique,lowbits,changed,max_delta);
  if(!sample) {GstBus *bus=gst_element_get_bus(p);GstMessage *msg=gst_bus_pop_filtered(bus,GST_MESSAGE_ERROR);
    if(msg){gchar *debug=NULL;gst_message_parse_error(msg,&error,&debug);g_printerr("%s: %s\n",error->message,debug?debug:"");g_free(debug);g_error_free(error);gst_message_unref(msg);}gst_object_unref(bus);}
  gst_element_set_state(p,GST_STATE_NULL);if(sample)gst_sample_unref(sample);
  gst_object_unref(src);gst_object_unref(out);gst_object_unref(upload);gst_object_unref(balance);gst_object_unref(p);g_free(reference);
  return pass?0:1;
}
