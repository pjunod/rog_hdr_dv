# SEI RBSP boundary reproduction

This standalone regression compiles the actual FFmpeg `find_sei_end()`
function from two Git revisions. The candidate also supplies its actual
`read_sei_byte()`. Only logging, the unused codec context and constants are
stubbed. Production function bodies are not rewritten or reimplemented.

On the recorded base, 13 of 21 expectations fail. The candidate passes all 21
under AddressSanitizer and UndefinedBehaviorSanitizer. The actual changed
`libavcodec/videotoolboxenc.o` also compiles on arm64 with macOS SDK 27.0 and
the H.264 VideoToolbox encoder enabled. See [receipt.json](receipt.json) for
source/function hashes, exact cases, build commands and log hashes.

## Run

Use an owned FFmpeg Git checkout containing the candidate. The unsigned unit
preview prepares such a checkout; use the path it prints. This runner reads
Git objects without switching branches or modifying the supplied source.
It requires Git and a C compiler with AddressSanitizer/UndefinedBehaviorSanitizer.

```bash
python3 upstream/ffmpeg/01-videotoolbox-caption-sei/reproduction/run.py \
  --source /path/to/owned/FFmpeg --candidate HEAD \
  --baseline 16efe6927d850d23766aee15820abedcb1219121 \
  --output work/ffmpeg-sei-proof-1
```

The output directory must be new. It retains generated C, binaries and
`results.json`; nothing is deleted or overwritten. Exit zero requires both
named escaped-UUID failures on the baseline and every expectation passing on
the candidate. A missing compiler, build failure or unexpected candidate result
fails the command.

## What the fixtures establish

The fixture builder constructs RBSP SEI messages and independently inserts
emulation-prevention bytes to produce the encoded NAL. A literal escaped UUID
NAL additionally checks the builder. User-data-unregistered payloads contain
the required 16-byte UUID, sometimes followed by arbitrary user bytes. The
unknown extended payload type checks only structural SEI parsing.

A successful lookup must point to the existing `0x80` trailing byte; the return
value includes that byte. Expected offsets come from the constructed encoded
NAL length, not from another implementation of the production walker.

| Fixture | Expected trailing offset | Baseline | Candidate |
|---|---|---|---|
| Escaped UUID, 21 encoded bytes | 20 | Invalid-data error | 20 |
| Zero UUID, 27 encoded bytes | 26 | 19: inside existing payload | 26 |
| 255-byte payload, 261 encoded bytes | 260 | 4: inside existing payload | 260 |

Other cases cover each escaped byte `00` through `03`, payload-size extension
bytes, two SEI messages, missing trailing data, invalid/truncated escapes,
truncated headers, empty input and non-SEI input. The baseline header-only case
also triggers UBSan pointer-offset overflow. The corrected parser rejects it.

## Jellyfin's smaller alternative

Jellyfin commit
[`7ef12861`](https://github.com/jellyfin/jellyfin-ffmpeg/commit/7ef12861e5f832e3cd86dfd8d4d8d77e2fcde442)
removes `find_sei_end()` and the append-to-existing-SEI branch. Existing SEI NAL
units are copied, then the existing insertion path emits a separate caption
SEI before a later post-SEI NAL. That avoids this walker entirely with less code.
The candidate instead retains merging, correctly counts RBSP payload bytes and
preserves existing encoded data. Maintainers should choose whether retaining
merging is required; this reproduction is evidence for the defect, not an
argument that the larger repair is preferable.

## Limits

No VideoToolbox encode, A/53 caption insertion, FATE integration, full FFmpeg
link or hardware decoder ran. The standalone fixture does not execute the
changed destination-capacity arithmetic in `copy_replace_length_codes()`;
that code is covered only by the actual translation-unit compile. Structurally
valid SEI NALs are not a full decodable H.264 access-unit qualification. The
Jellyfin alternative was inspected, not encoder-tested here. Native configure
and compile logs are retained outside Git, with hashes in the receipt. The
retained configure summary redacts its absolute owned source path. No
installation or upstream submission occurred.
