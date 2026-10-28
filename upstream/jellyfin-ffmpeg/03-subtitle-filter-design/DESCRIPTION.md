# VideoToolbox subtitle images and overlay design

Discuss GPU subtitle image preparation and composition before exporting the
large feature. The existing downstream patch combines a command protocol, new
filter, overlay changes and configure plumbing. Its application protocol is not
automatically a suitable public FFmpeg interface. No unsplit feature patch is
submitted by this kit.

Validation: source preparation only; the missing checks below have not run.

Before submission: Maintainer agreement on filter and overlay API; Split the
command protocol from generic filter plumbing; Mac render and lifetime tests.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
