
#!/usr/bin/env python3

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

METRICS = {
    "pointer_arithmetic": "Pointer arithmetic",
    "unsafe_lines": "Unsafe lines",
    "unsafe_calls": "Unsafe calls",
    "unsafe_casts": "Unsafe casts",
    "total_spans": "Total spans",
    "raw_pointer_dereferences": "Raw pointer dereferences",
    "raw_pointer_declarations": "Raw pointer declarations",
}

PATTERNS = {
    key: re.compile(
        rf"^\s*{re.escape(label)}:\s*(\d+)\s*$",
        re.MULTILINE,
    )
    for key, label in METRICS.items()
}


def aggregate(text, totals):
    """Sum every occurrence of each metric."""
    for key, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            totals[key] += int(match.group(1))


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate cargo newmetrics output"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Log files to process (default: stdin)",
    )
    parser.add_argument(
        "--out",
        default="newmetrics_summary.json",
        help="Output JSON file",
    )

    args = parser.parse_args()
    totals = defaultdict(int)

    if args.files:
        for filename in args.files:
            text = Path(filename).read_text(
                encoding="utf-8",
                errors="replace",
            )
            aggregate(text, totals)
    else:
        aggregate(sys.stdin.read(), totals)

    report = {
        key: totals[key]
        for key in METRICS
    }

    total_spans = report["total_spans"]
    report["unsafe_ratio"] = (
        report["unsafe_lines"] / total_spans
        if total_spans > 0
        else 0.0
    )

    output = Path(args.out)
    output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
