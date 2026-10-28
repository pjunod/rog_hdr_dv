# avfilter/bwdif_videotoolbox: bind parameters at buffer index zero

Bind the parameter buffer at the Metal shader's declared buffer index zero.
Texture and buffer index spaces are separate. The proposal is a quilt patch
appended after the existing 101-patch queue.

Validation: quilt queue apply; native Mac filter build; synthetic 128x64 10fps
NV12 Metal bwdif send_field/tff/all versus same-source CPU bwdif — baseline and
fixed compile and emit 20 frames; baseline 10 unique hashes, fixed 20; CPU mean
absolute byte error drops from 1.9980 to 0.1384 (not bit-exact).

These are scoped source and synthetic checks. They do not claim a complete x265
package build, general image-quality acceptance, or calibration.

Reproduction after building the patched Jellyfin queue:

```bash
./ffmpeg -init_hw_device videotoolbox=vt -filter_hw_device vt \
  -f lavfi -i testsrc2=size=128x64:rate=10:duration=1 \
  -vf 'format=nv12,hwupload,bwdif_videotoolbox=mode=send_field:parity=tff:deint=all,hwdownload,format=nv12' \
  -f framemd5 -
```

The original binding emits 20 field frames with 10 distinct hashes; the correct
binding emits 20 distinct hashes. Against the same source's CPU bwdif output,
mean absolute byte error falls from 1.9980 to 0.1384. This output is not bit-
exact with CPU bwdif and is not a general image-quality qualification.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
