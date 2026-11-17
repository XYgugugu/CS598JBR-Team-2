# NewMetrics

## Installation

Build and install the `newmetrics` tool from the project root:

```bash
cargo install --debug --locked --path . --force
```

## Usage

From the root of your translated Rust project, run:

```bash
cargo newmetrics 2>&1 | python3 aggregate.py --out summary.json
```

This runs the analysis, aggregates metrics across compilation units, and saves the results to `summary.json`.
