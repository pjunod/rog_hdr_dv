# Validation for existing AArch64 FP16 target-feature work

Do not open another pull request for the four helper annotations. The current
canonical repository is sarah-quinones/gemm; sarah-ek/gemm redirects there.

Existing work at the same base 86102c5b712737978371ac9ef7a11982f686d7bc:

- #47, kpernyer's open Draft, adds fp16 to all four helpers. Head:
  e4a7df8fa20fb155b3fb28563c1dc6b6a81b45ee.
- #39 is an earlier open four-line target-feature proposal.
- #43 is a broader open proposal including an instruction substitution.
- #45 is closed and unmerged.

The independent local four-helper candidate was built with Rust 1.97.1 for
generic aarch64-unknown-linux-gnu at opt-level zero: the original base fails
with eight fullfp16 assembler errors and the candidate builds. The exact #47
head e4a7df8fa20fb155b3fb28563c1dc6b6a81b45ee was then independently archived
and built with the same pinned generic AArch64 command, and passed.

Prepared validation reply — review before posting to the selected existing PR:

The generic AArch64 opt-level-zero failure is reproducible on the unchanged main
base with Rust 1.97.1. The exact PR #47 head
e4a7df8fa20fb155b3fb28563c1dc6b6a81b45ee builds with
CARGO_PROFILE_DEV_OPT_LEVEL=0 cargo build --target aarch64-unknown-linux-gnu -p
gemm-f16. The annotation does not raise the global CPU baseline. This is a build
check, not an arithmetic/runtime benchmark or a full-workspace test result.

No reply or Tested-by has been posted or attributed to Paul. The submission
script refuses this overlap hold so it cannot create a duplicate PR.

Prepared with GPT-6 through OpenAI Codex, and with Anthropic Claude Opus 5.5 and
Fable 5.1 through Claude Code. Human review and submission are pending.
