The external checker re-ran the checks on your code (round {round} of {max_rounds}).
Some checks are not clean yet. Here are the results:

## Summary

- Build: {build_status}
- Tests: {tests_passed} passed out of {tests_total}
- Clippy warnings: {clippy_summary}
- Unsafe metrics: {unsafe_summary}
- Protected files (tests, Cargo.toml): {protected_status}

## Details

{feedback}

## What to do

Read the feedback above, find the cause of each problem in your Rust code, and repair it. Keep the
same rules as before: do not modify the tests or `Cargo.toml`, keep the required interface, no
`unsafe`, and match the behavior of the C code. Re-run build, tests, and Clippy yourself after your
changes, and finish with a short summary of the final status.
