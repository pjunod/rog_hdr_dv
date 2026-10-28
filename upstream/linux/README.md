# Linux — luminance follow-ups and scoped report drafts

**Status:** follow-up source qualified on 2026-10-28; email-thread and human
attestations remain with the submitter. [Manifest](manifest.json) is exact;
[evidence](evidence.json) distinguishes new and recovered test results.

| Unit | Inventory | Deliverable | State |
|---|---|---|---|
| 01 | LNX-1 | Reply draft for Cristian La Spina's existing series | No resubmission and no fabricated Tested-by |
| 02 | LNX-2 | Two validation/KUnit follow-up patches | Builds; 4/4 current KUnit; thread/DCO/mail setup outstanding |
| 03 | LNX-3 | VRR/PSR failure report draft | Current-source diagnosis; fresh hardware/log reproduction outstanding |

```bash
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
receipts are retained under `~/work/upstream-prep/linux-mail/` by default,
not in a disposable compiler cache. You may instead
import the prepared series into your b4 workflow. `--source PATH` reads an
existing source cache without changing it; the emitted tree must still match
the recorded qualification.

The current kernel's [coding-assistant guidance](https://github.com/torvalds/linux/blob/65ba8f34ec886ec72b2c07ddc8cf3d815c32869d/Documentation/process/coding-assistants.rst)
no longer mandates an Assisted-by trailer. Tool involvement remains disclosed
in the follow-up changelogs. No kernel was installed or activated here.
