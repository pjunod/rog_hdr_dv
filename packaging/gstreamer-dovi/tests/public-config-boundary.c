/* SPDX-License-Identifier: MIT */
#include <libavcodec/dovi_parser.h>
#include <assert.h>
#include <stdio.h>
int main(void) {
  AVDoviRpuParser *parser=av_dovi_rpu_parser_alloc(NULL);
  AVDOVIDecoderConfigurationRecord config={0};
  assert(parser);
  config.dv_version_major=1;config.dv_profile=8;config.dv_level=6;
  config.rpu_present_flag=1;config.bl_present_flag=1;
  config.dv_md_compression=AV_DOVI_COMPRESSION_EXTENDED;
  assert(av_dovi_rpu_parser_configure(parser,&config,sizeof(config))==0);
  config.dv_md_compression=AV_DOVI_COMPRESSION_RESERVED;
  assert(av_dovi_rpu_parser_configure(parser,&config,sizeof(config))<0);
  config.dv_md_compression=AV_DOVI_COMPRESSION_EXTENDED;
  assert(av_dovi_rpu_parser_configure(parser,&config,sizeof(config))==0);
  av_dovi_rpu_parser_free(&parser);assert(!parser);
  puts("{\"state\":\"PASS\",\"reserved2_rejected\":true,\"extended3_accepted\":true,\"configure_recovers_after_rejection\":true}");
  return 0;
}
