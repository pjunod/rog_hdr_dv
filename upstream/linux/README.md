# Linux — luminance follow-ups and scoped report drafts

**Updated:** 2026-11-09 · Follow-up source remains qualified at its exact
2026-10-28 base; email-thread and human attestations remain with the submitter.
[Manifest](manifest.json) preserves that source pin; [evidence](evidence.json)
distinguishes the October checks from recovered test results. The later
[Ubuntu kernel rebase](../../docs/KERNEL_REBASE.md) has separate source, build
and target evidence.

| Unit | Inventory | Deliverable | State |
|---|---|---|---|
| 01 | LNX-1 | Reply draft for Cristian La Spina's existing series | No resubmission and no fabricated Tested-by |
| 02 | LNX-2 | Two validation/KUnit follow-up patches | Builds; 4/4 KUnit at the October 28 upstream base; thread/DCO/mail setup outstanding |
| 03 | LNX-3 | Report draft with a real downstream VRR/PSR fix | Bounded November 2 hardware pass retained; current upstream extraction, qualification and owner mail preparation outstanding |

```bash
export UPSTREAM_WORK_ROOT=/Volumes/Untitled/agent/workspaces/upstream-linux-mail
./upstream/linux/submit.sh all --dry-run  # Apply and emit cover + our two unsigned follow-ups.
./upstream/linux/submit.sh --lookup-thread  # Read the original public cover Message-ID.
./upstream/linux/submit.sh 02 --prepare --thread MESSAGE-ID  # Human: add your DCO and prepare mail.
```

The [prerequisites](prerequisites/) retain Cristian's authorship and original
DCO. They are not our submission. Only the two patches in
[02-luminance-validation](02-luminance-validation/) are outgoing candidates.
No Paul Signed-off-by or Tested-by is stored. Verify the latest revision of
[series 171513](https://patchwork.freedesktop.org/series/171513/), prepare the
reply with b4, and add personal attestations only after review. The explicit human `--prepare` invocation adds your DCO only to our two
follow-ups and emits a cover letter, two patches, a hash receipt and
`SEND_COMMAND.sh`. Review these files, refresh recipients with
`scripts/get_maintainer.pl`, then run that command with your configured
`git send-email` SMTP route. Preparation never sends email. Mail files and
receipts must stay in an owned durable external-drive slot. Set
`UPSTREAM_WORK_ROOT` before running the helper as above; its legacy home-directory
default is not appropriate for the current storage policy. You may instead
import the prepared series into your b4 workflow. `--source PATH` reads an
existing source cache without changing it; the emitted tree must still match
the recorded qualification.

The qualified source's [coding-assistant guidance](https://github.com/torvalds/linux/blob/65ba8f34ec886ec72b2c07ddc8cf3d815c32869d/Documentation/process/coding-assistants.rst)
no longer mandates an Assisted-by trailer. Tool involvement remains disclosed
in the follow-up changelogs. Recheck contribution guidance on the final upstream
base before sending. This submission refresh performs no build, installation
or activation.


## LNX-3 — downstream fix and remaining upstream preparation

The [fifth downstream patch](../../patches/linux/0005-drm-i915-psr-keep-Wa_14015401596-s-set-context-laten.patch)
is a real fix, not an unimplemented hypothesis. The
[rebase receipt](../../evidence/kernel-7.3-rebase.json) records its reviewed
PSR timing-check ordering, warnings-enabled i915/xe object builds and complete
Ubuntu packages. Its parser KUnit results cover the DisplayID follow-ups;
they are not a dedicated VRR regression.

The [bounded November 2 observation](../../docs/I915_VRR_FASTSET.md) retained an
owner-attended fullscreen/windowed stock-mpv fixture: live `VRR_ENABLED`
changed 0→1→0, with zero page-flip errors and normal visible output. This is
not optical, long-duration, suspend/resume, other-GPU/mode or external-monitor
qualification. The package/boot receipt and the later visible observation
retain their separate dates and scopes.

Unit 03 stays held: extract and qualify the correction against the selected
current upstream source, update the report with scoped sanitized evidence,
resolve recipients and latest relevant threads, and have the owner review and
add DCO before using the configured mail route. The existing helper prepares
only unit 02's two outgoing patches; it does not export or send the VRR patch.
