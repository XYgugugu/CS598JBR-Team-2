Translate the C project **bigint** into safe, idiomatic Rust.

## Locations

- Original C project (read-only): `/Users/jasonzhao/Desktop/Coding Agent/CS598JBR-Team-2/MP4/subjects/project_1`
- Rust project to complete (your working directory): `/Users/jasonzhao/Desktop/Coding Agent/CS598JBR-Team-2/MP4/translations/project_1`

## C source files

- `src/bigint.h`
- `tests/test1.c`
- `tests/test2.c`
- `tests/test3.c`

## Rust files in the project

Interface files (implement every `unimplemented!()` body, keep the signatures):

- `src/lib.rs`
- `src/interfaces/bigint.rs`

Test files (read and run them, never modify them):

- `src/bin/test1.rs`
- `src/bin/test2.rs`
- `src/bin/test3.rs`

## What to do

1. Inspect the C code and the Rust interface and tests to understand the required behavior.
2. Make the project build (move the interface files into `src/` if needed).
3. Implement every function, then compile, test, and run Clippy with the toolchain
   `nightly-2025-05-13`, repairing until everything is clean.
4. Finish with a short summary of the final status.
