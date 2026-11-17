Translate the C project **{project_name}** into safe, idiomatic Rust.

## Locations

- Original C project (read-only): `{subject_dir}`
- Rust project to complete (your working directory): `{translation_dir}`

## C source files

{c_files}

## Rust files in the project

Interface files (implement every `unimplemented!()` body, keep the signatures):

{interface_files}

Test files (read and run them, never modify them):

{test_files}

## What to do

1. Inspect the C code and the Rust interface and tests to understand the required behavior.
2. Make the project build (move the interface files into `src/` if needed).
3. Implement every function, then compile, test, and run Clippy with the toolchain
   `nightly-2025-05-13`, repairing until everything is clean.
4. Finish with a short summary of the final status.
