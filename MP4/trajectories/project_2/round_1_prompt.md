Translate the C project **Holdem-Odds** into safe, idiomatic Rust.

## Locations

- Original C project (read-only): `/Users/jasonzhao/Desktop/Coding Agent/CS598JBR-Team-2/MP4/subjects/project_2`
- Rust project to complete (your working directory): `/Users/jasonzhao/Desktop/Coding Agent/CS598JBR-Team-2/MP4/translations/project_2`

## C source files

- `src/bucket.c`
- `src/bucket.h`
- `src/cards.c`
- `src/cards.h`
- `src/deck.c`
- `src/deck.h`
- `src/hands.c`
- `src/hands.h`
- `src/holdemodds.c`
- `src/holdemodds.h`
- `src/tests/CuTest.c`
- `src/tests/CuTest.h`
- `src/tests/all_tests.c`
- `src/tests/test_bucket.c`
- `src/tests/test_cards.c`
- `src/tests/test_deck.c`
- `src/tests/test_hands.c`

## Rust files in the project

Interface files (implement every `unimplemented!()` body, keep the signatures):

- `src/lib.rs`
- `src/interfaces/bucket.rs`
- `src/interfaces/cards.rs`
- `src/interfaces/deck.rs`
- `src/interfaces/hands.rs`
- `src/interfaces/holdemodds.rs`

Test files (read and run them, never modify them):

- `src/bin/test_bucket.rs`
- `src/bin/test_cards.rs`
- `src/bin/test_deck.rs`
- `src/bin/test_hands.rs`

## What to do

1. Inspect the C code and the Rust interface and tests to understand the required behavior.
2. Make the project build (move the interface files into `src/` if needed).
3. Implement every function, then compile, test, and run Clippy with the toolchain
   `nightly-2025-05-13`, repairing until everything is clean.
4. Finish with a short summary of the final status.
