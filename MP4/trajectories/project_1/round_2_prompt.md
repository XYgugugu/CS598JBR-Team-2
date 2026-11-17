The external checker re-ran the checks on your code (round 1 of 5).
Some checks are not clean yet. Here are the results:

## Summary

- Build: OK
- Tests: 8 passed out of 8
- Clippy warnings: {"correctness": 0, "style": 1, "complexity": 0, "perf": 0}
- Unsafe metrics: {"pointer_arithmetic": 0, "unsafe_lines": 0, "unsafe_calls": 0, "unsafe_casts": 0, "total_spans": 18524, "raw_pointer_dereferences": 0, "raw_pointer_declarations": 0, "unsafe_ratio": 0.0}
- Protected files (tests, Cargo.toml): unchanged

## Details

### Clippy output

```
warning: file `/Users/jasonzhao/Desktop/Coding Agent/CS598JBR-Team-2/MP4/translations/project_1/src/bin/test3.rs` found to be present in multiple build targets:
  * `bin` target `test3`
  * `integration-test` target `test3`
warning: file `/Users/jasonzhao/Desktop/Coding Agent/CS598JBR-Team-2/MP4/translations/project_1/src/bin/test1.rs` found to be present in multiple build targets:
  * `bin` target `test1`
  * `integration-test` target `test1`
warning: file `/Users/jasonzhao/Desktop/Coding Agent/CS598JBR-Team-2/MP4/translations/project_1/src/bin/test2.rs` found to be present in multiple build targets:
  * `bin` target `test2`
  * `integration-test` target `test2`
warning: method `from_str` can be confused for the standard trait method `std::str::FromStr::from_str`
   --> src/bigint.rs:167:5
    |
167 | /     pub fn from_str(s: &str) -> Self {
168 | |         let (negative, body) = match s.strip_prefix('-') {
169 | |             Some(rest) => (true, rest),
170 | |             None => (false, s),
...   |
177 | |     }
    | |_____^
    |
    = help: consider implementing the trait `std::str::FromStr` or choosing a less ambiguous method name
    = help: for further information visit https://rust-lang.github.io/rust-clippy/master/index.html#should_implement_trait
    = note: `-W clippy::should-implement-trait` implied by `-W clippy::style`
    = help: to override `-W clippy::style` add `#[allow(clippy::should_implement_trait)]`

warning: `bigint` (lib) generated 1 warning
warning: this boolean expression can be simplified
  --> src/bin/test2.rs:16:13
   |
16 |     assert!(!(x < y));
   |             ^^^^^^^^ help: try: `(x >= y)`
   |
   = help: for further information visit https://rust-lang.github.io/rust-clippy/master/index.html#nonminimal_bool
   = note: `-W clippy::nonminimal-bool` implied by `-W clippy::complexity`
   = help: to override `-W clippy::complexity` add `#[allow(clippy::nonminimal_bool)]`

warning: this boolean expression can be simplified
  --> src/bin/test2.rs:17:13
   |
17 |     assert!(!(x > y));
   |             ^^^^^^^^ help: try: `(x <= y)`
   |
   = help: for further information visit https://rust-lang.github.io/rust-clippy/master/index.html#nonminimal_bool

warning: this boolean expression can be simplified
  --> src/bin/test2.rs:23:13
   |
23 |     assert!(!(x >= y));
   |             ^^^^^^^^^ help: try: `(x < y)`
   |
   = help: for further information visit https://rust-lang.github.io/rust-clippy/master/index.html#nonminimal_bool

warning: this boolean expression can be simplified
  --> src/bin/test2.rs:25:13
   |
25 |     assert!(!(x > y));
   |             ^^^^^^^^ help: try: `(x <= y)`
   |
   = help: for further information visit https://rust-lang.github.io/rust-clippy/master/index.html#nonminimal_bool

warning: unused variable: `b`
 --> src/bin/test3.rs:6:9
  |
6 |     let b = BigInt::from_int(1234567890);
  |         ^ help: if this is intentional, prefix it with an underscore: `_b`
  |
  = note: `#[warn(unused_variables)]` on by default

warning: `bigint` (bin "test2" test) generated 4 warnings (run `cargo clippy --fix --bin "test2" --tests` to apply 4 suggestions)
warning: `bigint` (bin "test3" test) generated 1 warning
warning: unused import: `bigint::bigint::BigInt`
 --> src/bin/test2.rs:1:5
  |
1 | use bigint::bigint::BigInt;
  |     ^^^^^^^^^^^^^^^^^^^^^^
  |
  = note: `#[warn(unused_imports)]` on by default

warning: variables can be used directly in the `format!` string
  --> src/bin/test1.rs:20:5
   |
20 |     println!("{}! = {}", n, result);
   |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   |
   = help: for further information visit https://rust-lang.github.io/rust-clippy/master/index.html#uninlined_format_args
   = note: `-W clippy::uninlined-format-args` implied by `-W clippy::style`
   = help: to override `-W clippy::style` add `#[allow(clippy::uninlined_format_args)]`
help: change this to
   |
20 -     println!("{}! = {}", n, result);
20 +     println!("{n}! = {result}");
   |

warning: unused import: `bigint::bigint::BigInt`
 --> src/bin/test3.rs:1:5
  |
1 | use bigint::bigint::BigInt;
  |     ^^^^^^^^^^^^^^^^^^^^^^
  |
  = note: `#[warn(unused_imports)]` on by default

warning: function `factorial` is never used
 --> src/bin/test1.rs:3:4
  |
3 | fn factorial(n: BigInt) -> BigInt {
  |    ^^^^^^^^^
  |
  = note: `#[warn(dead_code)]` on by default

warning: `bigint` (test "test2") generated 4 warnings (4 duplicates)
warning: `bigint` (bin "test2") generated 1 warning (run `cargo clippy --fix --bin "test2"` to apply 1 suggestion)
warning: `bigint` (test "test1") generated 1 warning (run `cargo clippy --fix --test "test1"` to apply 1 suggestion)
warning: `bigint` (test "test3") generated 1 warning (1 duplicate)
warning: `bigint` (bin "test3") generated 1 warning (run `cargo clippy --fix --bin "test3"` to apply 1 suggestion)
warning: `bigint` (bin "test1") generated 1 warning
warning: `bigint` (bin "test1" test) generated 1 warning (1 duplicate)
warning: `bigint` (lib test) generated 1 warning (1 duplicate)
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.02s

```

## What to do

Read the feedback above, find the cause of each problem in your Rust code, and repair it. Keep the
same rules as before: do not modify the tests or `Cargo.toml`, keep the required interface, no
`unsafe`, and match the behavior of the C code. Re-run build, tests, and Clippy yourself after your
changes, and finish with a short summary of the final status.
