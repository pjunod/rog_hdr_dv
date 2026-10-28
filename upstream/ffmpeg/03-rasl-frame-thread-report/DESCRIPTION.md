# HEVC skipped-picture continuation already fixed upstream

Do not submit the old suppressed-RASL patch or the provisional current-base
port. Upstream commit `e5eb7581ddc511a46892b5501b26fb831161b5da` explicitly
fixes remaining slices of a skipped picture being parsed against stale context
after a seek, including PPS-change and dependent-slice errors.

The current decoder drops continuation slices before header parsing when
`skipping_frame` is set, copies that state to fresh frame-thread workers, and
clears it during flush. This addresses the exact reason for the old patch. The
earlier inventory noticed that restructuring but incorrectly left the item as
likely still open. Source inspection resolves it as already upstream; it is not
a new physical or full FATE qualification claim.

A provisional port compiled during preparation but is excluded from this kit
because no additional current-upstream defect was established. The official
RAP_A_docomo CRA sample was inspected; it has only first-slice NAL units and
does not exercise the old multi-slice regression, so no reproduction pass is
claimed from it.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
