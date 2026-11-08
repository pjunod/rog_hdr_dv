/* Exercise the public libavfilter graph using an already-PQ synthetic input. */
#include <stdint.h>
#include <stdio.h>
#include <libavfilter/avfilter.h>
#include <libavfilter/buffersink.h>
#include <libavfilter/buffersrc.h>
#include <libavutil/hdr_dynamic_metadata.h>
#include <libavutil/imgutils.h>
#include <libavutil/hwcontext.h>
#include <libavutil/mastering_display_metadata.h>

int main(void)
{
    AVFilterGraph *graph = avfilter_graph_alloc();
    AVFrame *input = av_frame_alloc(), *output = av_frame_alloc();
    AVFilterContext *source = NULL, *filter = NULL, *sink = NULL;
    int result = 1;
    if (!graph || !input || !output)
        goto done;
    input->format = AV_PIX_FMT_YUV420P10LE;
    input->width = input->height = 32;
    input->pts = 0;
    input->duration = 1;
    input->color_trc = AVCOL_TRC_SMPTE2084;
    input->colorspace = AVCOL_SPC_BT2020_NCL;
    input->color_primaries = AVCOL_PRI_BT2020;
    input->color_range = AVCOL_RANGE_MPEG;
    if (av_frame_get_buffer(input, 32) < 0)
        goto done;
    ptrdiff_t linesizes[4] = {input->linesize[0], input->linesize[1], input->linesize[2], 0};
    if (av_image_fill_black(input->data, linesizes, input->format, input->color_range, 32, 32) < 0)
        goto done;
    AVDynamicHDRPlus *hdr = av_dynamic_hdr_plus_create_side_data(input);
    if (!hdr)
        goto done;
    hdr->num_windows = 1;
    if (!av_frame_new_side_data(input, AV_FRAME_DATA_DOVI_RPU_BUFFER, 1))
        goto done;
    filter = avfilter_graph_alloc_filter(graph, avfilter_get_by_name("libplacebo"), "map");
    if (!filter || av_hwdevice_ctx_create(&filter->hw_device_ctx, AV_HWDEVICE_TYPE_VULKAN,
                                           "0", NULL, 0) < 0)
        goto done;
    if (avfilter_graph_create_filter(&source, avfilter_get_by_name("buffer"), "source",
            "video_size=32x32:pix_fmt=yuv420p10le:time_base=1/24:frame_rate=24/1:pixel_aspect=1/1:colorspace=bt2020nc:range=tv",
            NULL, graph) < 0 ||
        avfilter_init_str(filter,
            "apply_dolbyvision=0:target_peak=600:target_black=0.001:target_gamut=p3:format=yuv420p10le") < 0 ||
        avfilter_graph_create_filter(&sink, avfilter_get_by_name("buffersink"), "sink",
            NULL, NULL, graph) < 0 ||
        avfilter_link(source, 0, filter, 0) < 0 || avfilter_link(filter, 0, sink, 0) < 0 ||
        avfilter_graph_config(graph, NULL) < 0 ||
        av_buffersrc_write_frame(source, input) < 0 || av_buffersrc_close(source, 1, 0) < 0)
        goto done;
    int ret = av_buffersink_get_frame(sink, output);
    if (ret < 0) {
        fprintf(stderr, "reading mapped frame: %s\n", av_err2str(ret));
        goto done;
    }
    fprintf(stderr, "output transfer=%d primaries=%d side-data=%d\n",
            output->color_trc, output->color_primaries, output->nb_side_data);
    const AVFrameSideData *md = av_frame_get_side_data(output, AV_FRAME_DATA_MASTERING_DISPLAY_METADATA);
    if (!md || md->size < sizeof(AVMasteringDisplayMetadata))
        goto done;
    const AVMasteringDisplayMetadata *mastering = (const void *) md->data;
    fprintf(stderr, "mastering peak=%d/%d HDR10+=%d Dolby RPU=%d\n",
            mastering->max_luminance.num, mastering->max_luminance.den,
            !!av_frame_get_side_data(output, AV_FRAME_DATA_DYNAMIC_HDR_PLUS),
            !!av_frame_get_side_data(output, AV_FRAME_DATA_DOVI_RPU_BUFFER));
    result = !(mastering->has_luminance && mastering->has_primaries &&
               av_cmp_q(mastering->max_luminance, (AVRational){600, 1}) == 0 &&
               output->color_trc == AVCOL_TRC_SMPTE2084 &&
               output->color_primaries == AVCOL_PRI_BT2020 &&
               !av_frame_get_side_data(output, AV_FRAME_DATA_DYNAMIC_HDR_PLUS) &&
               !av_frame_get_side_data(output, AV_FRAME_DATA_DOVI_RPU_BUFFER));
done:
    fprintf(stderr, "explicit target metadata result=%d\n", result);
    av_frame_free(&output);
    av_frame_free(&input);
    avfilter_graph_free(&graph);
    return result;
}
