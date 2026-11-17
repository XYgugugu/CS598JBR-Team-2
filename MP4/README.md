# MP4: Agentic C-to-Rust Translation

## Environment

| Item | Value |
|---|---|
| OS | macOS 26.6.2 (Darwin 25.6.0), Apple Silicon (arm64) |
| Agent framework | Claude Code CLI 2.1.326 |
| Model(s) and provider | `claude-opus-5-5` (Claude Opus 5.5) via Anthropic, through Claude Code; single agent, single model |
| Inference settings | Effort `high`; max $10 per agent round (`--max-budget-usd`); max 5 rounds. Claude Code does not expose temperature. All settings in `configs/pipeline.json` |
| Rust toolchain | `nightly-2025-05-13` (rustc 1.89.0-nightly 8405332bd 2025-05-12, cargo 1.89.0-nightly) |
| Rust components | `clippy` 0.1.88, `rustfmt`, `rustc-dev`, `llvm-tools-preview` |
| rustup | 1.29.3 |
| Python | 3.14.7 |
| Unsafe-metrics tool | `newmetrics` 0.1.0 |
| API / usage limits | TODO |

### Tools available to the agent

- File read / search / edit tools (built into Claude Code): may read the C project and the Rust
  project, may edit only `src/` of the Rust project (never `src/bin/` tests or `Cargo.toml`)
- Shell commands, allow-listed: `cargo`, `ls`, `mv`, `mkdir`, `rmdir`, `cat`, `head`, `tail`,
  `grep`, `wc`, `sort`, `uniq`, `diff`, `echo`. No network, `git`, or `rm`
  (see `configs/claude_settings.json`)
- `cargo +nightly-2025-05-13 build`
- `cargo +nightly-2025-05-13 check`
- `cargo +nightly-2025-05-13 test --no-fail-fast`
- `cargo +nightly-2025-05-13 clippy --all-targets --all-features -- -W clippy::correctness -W clippy::style -W clippy::complexity -W clippy::perf`
- `cargo +nightly-2025-05-13 newmetrics`

## Setup

All commands below are run from the repository root unless noted.

### 1. Rust toolchain

```bash
# Install rustup (skip if already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain none
. "$HOME/.cargo/env"

# Pinned toolchain used for both translation and grading
rustup toolchain install nightly-2025-05-13 --profile minimal \
    -c clippy -c rustfmt -c rustc-dev -c llvm-tools-preview

cargo +nightly-2025-05-13 --version
cargo +nightly-2025-05-13 clippy --version
```

### 2. Unsafe-metrics tool

```bash
cd MP4/newmetrics
cargo install --debug --locked --path . --force
cd ../..
```

Usage example, from the root of a translated Rust project (run `cargo clean` first so every compilation unit is analyzed):

```bash
cargo clean
cargo +nightly-2025-05-13 newmetrics 2>&1 | python3 <path-to>/MP4/newmetrics/aggregate.py --out summary.json
```

### 3. Agent framework

```bash
# Install Claude Code (native installer)
curl -fsSL https://claude.ai/install.sh | bash
claude --version
```

Authenticate either by running `claude` once and logging in, or by exporting `ANTHROPIC_API_KEY` in your shell.

### 4. Python dependencies

The pipeline itself needs no third-party packages. The structure validator needs:

```bash
pip install GitPython colorama
python3 MP4/validate.py https://github.com/XYgugugu/CS598JBR-Team-2.git main
```

### 5. Benchmark data

The C projects in `subjects/` and the Rust interfaces/tests come from the CRUST-Bench dataset archive (`datasets/CRUST_bench.zip`):

| Project | C source (`CBench/`) | Rust interface + tests (`RBench/`) |
|---|---|---|
| project_1 | `bigint` | `bigint` (8 tests) |
| project_2 | `Holdem-Odds` | `Holdem_Odds` (24 tests) |

The templates are committed unmodified (commit `0d8779c`). As shipped they do not compile, because
`lib.rs` declares modules whose files are in `src/interfaces/`. The agent is instructed to apply
CRUST-Bench's own formatting step (`src/check_benchmarks/check_build.py`): move each file from
`src/interfaces/` up into `src/`. File contents, tests, and public signatures are not modified.

## Run

```bash
MP4/src/run.sh 1     # project_1 (bigint)
MP4/src/run.sh 2     # project_2 (Holdem-Odds)
```

To start a project again from the untouched CRUST-Bench template:

```bash
git checkout 0d8779c -- MP4/translations/project_1
```

## Pipeline

Files:

| File | Purpose |
|---|---|
| `src/run_pipeline.py` | The controller: runs the agent, runs the checks, decides whether to stop or send feedback |
| `src/run.sh` | One-command entry point |
| `configs/pipeline.json` | Model, effort, budget, toolchain, stopping condition, project paths |
| `configs/claude_settings.json` | Agent permissions (what it may read, edit, and run) |
| `configs/prompts/system.md` | Standing instructions: rules for correctness, safety, idiomatic Rust, workflow |
| `configs/prompts/initial.md` | First message for a project (filled with the project's file lists) |
| `configs/prompts/repair.md` | Repair message template (filled with the checker's feedback) |

Loop:

1. **Baseline (round 0):** run all checks on the untouched template.
2. **Inspect + generate (agent):** Claude Code (`claude -p`, working directory
   `translations/project_N/`, read access to `subjects/project_N/`) reads the C code, the Rust
   interface, and the tests, then writes the Rust implementation. Inside its session it runs
   `cargo build` / `test` / `clippy` itself and repairs based on the output.
3. **Observe (pipeline):** after the agent stops, the pipeline independently
   - restores any changed test file or `Cargo.toml` (and reports it to the agent),
   - runs `cargo build`, `cargo test --no-fail-fast`, the Clippy command (plus one run per category
     to count correctness / style / complexity / perf), and `cargo newmetrics`.
4. **Repair:** if a check is not clean, the pipeline sends the failing results (build errors,
   failing tests, Clippy output, unsafe metrics) to the **same** agent session (`--resume`) and
   goes back to step 2.

**Stopping condition** (first one that applies):

- all checks pass: build OK, all tests pass, 0 Clippy warnings in the agent's own code, all four
  primary unsafe metrics are 0, tests and `Cargo.toml` unchanged;
- 5 agent rounds reached;
- no progress: build status, tests passed, Clippy count, and unsafe total are identical to the
  previous round.

Clippy warnings inside the provided test files (`src/bin/`) cannot be fixed without editing the
tests, so the stopping condition counts only warnings in the agent's own code. Both counts are
recorded in `summary.json`.

## Outputs

Per project, in `trajectories/project_N/`:

| File | Content |
|---|---|
| `execution.log` | Timeline of the run: agent tool calls, check results, stop reason |
| `round_K_prompt.md` | The message sent to the agent in round K |
| `round_K_agent.jsonl` | Full raw agent trajectory (every message, tool call, and tool result) |
| `round_K_transcript.md` | The same trajectory as readable Markdown |
| `round_K_checks.txt` | Raw build / test / Clippy / newmetrics output from the pipeline's checks |
| `round_K_unsafe_metrics.json` | Aggregated unsafe metrics |
| `summary.json` | Per-round numbers, cost, and final status |

The final Rust code is in `translations/project_N/`.

## Outputs

## Evaluation
