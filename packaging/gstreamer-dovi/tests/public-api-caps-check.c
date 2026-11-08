#include <gst/gst.h>
#include <gst/video/video.h>
#include <gstdovipicture.h>
#include <stdio.h>
#include <string.h>
struct run { GstElement *pipe; GHashTable *pts; GBytes *seed; GChecksum *sum; GstVideoConverter *convert; GstVideoInfo target; guint phase,in,out,seen[3],errors; gboolean change; };
static GstCaps *changed_caps(struct run *r,GstCaps *caps) {
 GstCaps *copy=gst_caps_copy(caps); GBytes *bytes=r->seed;
 if(r->phase==1)bytes=NULL;
 if(r->phase==2){gsize n;const guint8 *p=g_bytes_get_data(bytes,&n);guint8 b[24];memcpy(b,p,n);b[2]&=254;b[3]=(b[3]&7)|(4<<3);bytes=g_bytes_new(b,n);}
 gst_dovi_caps_apply_stream_config(copy,bytes);if(r->phase==2)g_bytes_unref(bytes);return copy;
}
static GstPadProbeReturn before(GstPad *pad,GstPadProbeInfo *i,gpointer opaque) {
 struct run *r=opaque;
 if(GST_PAD_PROBE_INFO_TYPE(i)&GST_PAD_PROBE_TYPE_EVENT_DOWNSTREAM){
  GstEvent *event=GST_PAD_PROBE_INFO_EVENT(i);
  if(GST_EVENT_TYPE(event)==GST_EVENT_CAPS){GstCaps *caps;gst_event_parse_caps(event,&caps);
   if(!r->seed){AVDOVIDecoderConfigurationRecord record;if(!gst_dovi_caps_get_stream_config(caps,&record,&r->seed)||record.dv_profile!=5||record.dv_level!=3)r->errors++;}
   if(r->seed){GstCaps *copy=changed_caps(r,caps);GstEvent *next=gst_event_new_caps(copy);gst_caps_unref(copy);gst_event_unref(event);GST_PAD_PROBE_INFO_DATA(i)=next;}}
  return GST_PAD_PROBE_OK;}
 GstBuffer *buffer=GST_PAD_PROBE_INFO_BUFFER(i);guint64 time=GST_BUFFER_PTS(buffer);if(!GST_CLOCK_TIME_IS_VALID(time))return GST_PAD_PROBE_OK;
 if(r->change&&(r->in==16||r->in==40)){r->phase=r->in==16?1:2;GstCaps *caps=gst_pad_get_current_caps(pad);GstCaps *copy=changed_caps(r,caps);gst_caps_unref(caps);if(!gst_pad_push_event(pad,gst_event_new_caps(copy)))r->errors++;gst_caps_unref(copy);}
 guint64 *key=g_new(guint64,1);*key=time;if(g_hash_table_contains(r->pts,key))r->errors++;g_hash_table_insert(r->pts,key,GUINT_TO_POINTER(r->phase+1));r->in++;return GST_PAD_PROBE_OK;
}
static void received(GstElement *sink,GstBuffer *buffer,GstPad *pad,gpointer opaque){
 struct run *r=opaque;(void)sink;guint64 time=GST_BUFFER_PTS(buffer);guint token=GPOINTER_TO_UINT(g_hash_table_lookup(r->pts,&time));if(!token){r->errors++;return;}guint phase=token-1;
 GstCaps *caps=gst_pad_get_current_caps(pad);AVDOVIDecoderConfigurationRecord raw;GBytes *bytes=NULL;gboolean raw_known=gst_dovi_caps_get_stream_config(caps,&raw,&bytes);
 GstDoviPictureMeta *meta=gst_buffer_get_dovi_picture_meta(buffer);
 if(meta){const AVDOVIDecoderConfigurationRecord *record=gst_dovi_picture_get_stream_config(meta->picture);
  if(phase==1){if(record||raw_known||bytes)r->errors++;else r->seen[1]++;}
  else if(record){guint level=phase==2?4:3;if(record->dv_profile!=5||record->dv_level!=level||!raw_known||raw.dv_level!=level||raw.dv_profile!=5)r->errors++;else r->seen[phase]++;}}
 GstVideoInfo input;GstVideoFrame src,dst;gst_video_info_init(&input);
 if(!gst_video_info_from_caps(&input,caps)){r->errors++;goto done;}
 if(!r->convert){gst_video_info_set_format(&r->target,GST_VIDEO_FORMAT_I420_10LE,input.width,input.height);r->target.fps_n=input.fps_n;r->target.fps_d=input.fps_d;r->target.par_n=input.par_n;r->target.par_d=input.par_d;r->target.interlace_mode=input.interlace_mode;r->target.colorimetry=input.colorimetry;r->target.chroma_site=input.chroma_site;r->convert=gst_video_converter_new(&input,&r->target,NULL);}
 if(!r->convert||!gst_video_frame_map(&src,&input,buffer,GST_MAP_READ)){r->errors++;goto done;}
 GstBuffer *packed=gst_buffer_new_allocate(NULL,r->target.size,NULL);
 if(!gst_video_frame_map(&dst,&r->target,packed,GST_MAP_WRITE)){r->errors++;gst_video_frame_unmap(&src);gst_buffer_unref(packed);goto done;}
 gst_video_converter_frame(r->convert,&src,&dst);
 for(guint c=0;c<3;c++){guint w=c?(r->target.width+1)/2:r->target.width,h=c?(r->target.height+1)/2:r->target.height;guint8 *data=GST_VIDEO_FRAME_PLANE_DATA(&dst,c);gint stride=GST_VIDEO_FRAME_PLANE_STRIDE(&dst,c);for(guint y=0;y<h;y++)g_checksum_update(r->sum,data+y*stride,w*2);}
 gst_video_frame_unmap(&src);gst_video_frame_unmap(&dst);gst_buffer_unref(packed);
 done:g_clear_pointer(&bytes,g_bytes_unref);gst_caps_unref(caps);r->out++;
}
int main(int argc,char **argv){if(argc!=4)return 2;gst_init(&argc,&argv);struct run r={0};r.change=!strcmp(argv[3],"change");r.pts=g_hash_table_new_full(g_int64_hash,g_int64_equal,g_free,NULL);r.sum=g_checksum_new(G_CHECKSUM_SHA256);
 gchar *file=g_strescape(argv[2],NULL);gchar *text=g_strdup_printf("filesrc location=\"%s\" ! qtdemux ! h265parse ! video/x-h265,stream-format=byte-stream,alignment=au ! identity name=inject eos-after=96 ! %s name=decode ! fakesink name=out signal-handoffs=true sync=false",file,argv[1]);GError *error=NULL;r.pipe=gst_parse_launch(text,&error);g_free(file);g_free(text);if(error||!r.pipe)return 2;
 GstElement *inject=gst_bin_get_by_name(GST_BIN(r.pipe),"inject"),*decode=gst_bin_get_by_name(GST_BIN(r.pipe),"decode"),*sink=gst_bin_get_by_name(GST_BIN(r.pipe),"out");if(g_object_class_find_property(G_OBJECT_GET_CLASS(decode),"max-threads"))g_object_set(decode,"max-threads",1,NULL);
 GstPad *pad=gst_element_get_static_pad(inject,"src");gst_pad_add_probe(pad,GST_PAD_PROBE_TYPE_BUFFER|GST_PAD_PROBE_TYPE_EVENT_DOWNSTREAM,before,&r,NULL);gst_object_unref(pad);g_signal_connect(sink,"handoff",G_CALLBACK(received),&r);gst_object_unref(inject);gst_object_unref(decode);gst_object_unref(sink);
 GstBus *bus=gst_element_get_bus(r.pipe);gst_element_set_state(r.pipe,GST_STATE_PLAYING);GstMessage *message=gst_bus_timed_pop_filtered(bus,40*GST_SECOND,GST_MESSAGE_ERROR|GST_MESSAGE_EOS);
 if(!message||GST_MESSAGE_TYPE(message)!=GST_MESSAGE_EOS)r.errors++;
 if(message&&GST_MESSAGE_TYPE(message)==GST_MESSAGE_ERROR){gchar *detail;gst_message_parse_error(message,&error,&detail);g_printerr("pipeline: %s %s\n",error->message,detail?detail:"");g_clear_error(&error);g_free(detail);}
 if(message)gst_message_unref(message);
 gst_element_set_state(r.pipe,GST_STATE_NULL);if(r.in!=r.out||r.out<85||!r.seen[0]||(r.change&&(r.seen[1]<5||r.seen[2]<5)))r.errors++;
 printf("{\"state\":\"%s\",\"decoder\":\"%s\",\"change\":%s,\"inputs\":%u,\"outputs\":%u,\"initial_known\":%u,\"removed_unknown\":%u,\"replacement_known\":%u,\"errors\":%u,\"pixels_sha256\":\"%s\"}\n",r.errors?"FAIL":"PASS",argv[1],r.change?"true":"false",r.in,r.out,r.seen[0],r.seen[1],r.seen[2],r.errors,g_checksum_get_string(r.sum));
 gst_object_unref(bus);gst_object_unref(r.pipe);if(r.convert)gst_video_converter_free(r.convert);g_clear_pointer(&r.seed,g_bytes_unref);g_hash_table_unref(r.pts);g_checksum_free(r.sum);return r.errors?1:0;}
