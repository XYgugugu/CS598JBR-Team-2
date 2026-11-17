The external checker re-ran the checks on your code (round 1 of 5).
Some checks are not clean yet. Here are the results:

## Summary

- Build: OK
- Tests: 24 passed out of 24
- Clippy warnings: {"correctness": 0, "style": 2, "complexity": 0, "perf": 0}
- Unsafe metrics: {"pointer_arithmetic": 0, "unsafe_lines": 0, "unsafe_calls": 0, "unsafe_casts": 0, "total_spans": 36757, "raw_pointer_dereferences": 0, "raw_pointer_declarations": 0, "unsafe_ratio": 0.0}
- Protected files (tests, Cargo.toml): unchanged

## Details

### Clippy output

```
warning: implementation of inherent method `to_string(&self) -> String` for type `cards::Card`
   --> src/cards.rs:94:5
    |
94  | /     pub fn to_string(&self) -> String {
95  | |         if self.is_valid() {
96  | |             [self.rank.to_char(), self.suit.to_char()].iter().collect()
97  | |         } else {
...   |
100 | |     }
    | |_____^
    |
    = help: implement trait `Display` for type `cards::Card` instead
    = help: for further information visit https://rust-lang.github.io/rust-clippy/master/index.html#inherent_to_string
    = note: `-W clippy::inherent-to-string` implied by `-W clippy::style`
    = help: to override `-W clippy::style` add `#[allow(clippy::inherent_to_string)]`

warning: writing `&mut Vec` instead of `&mut [_]` involves a new object where a slice will do
  --> src/deck.rs:23:27
   |
23 | pub fn deck_shuffle(deck: &mut Vec<Card>) {
   |                           ^^^^^^^^^^^^^^ help: change this to: `&mut [Card]`
   |
   = help: for further information visit https://rust-lang.github.io/rust-clippy/master/index.html#ptr_arg
   = note: `-W clippy::ptr-arg` implied by `-W clippy::style`
   = help: to override `-W clippy::style` add `#[allow(clippy::ptr_arg)]`

warning: crate `Holdem_Odds` should have a snake case name
  |
  = help: convert the identifier to snake case: `holdem_odds`
  = note: `#[warn(non_snake_case)]` on by default

warning: `Holdem_Odds` (lib) generated 3 warnings
warning: `Holdem_Odds` (lib test) generated 2 warnings (2 duplicates)
warning: unused imports: `Card`, `Rank`, `Suit`, `card_compare`, and `card_swap`
 --> src/bin/test_cards.rs:1:26
  |
1 | use Holdem_Odds::cards::{Card, Rank, Suit, card_compare, card_swap};
  |                          ^^^^  ^^^^  ^^^^  ^^^^^^^^^^^^  ^^^^^^^^^
  |
  = note: `#[warn(unused_imports)]` on by default

warning: unused imports: `deck_shuffle` and `new_deck`
 --> src/bin/test_hands.rs:3:25
  |
3 | use Holdem_Odds::deck::{new_deck, deck_shuffle};
  |                         ^^^^^^^^  ^^^^^^^^^^^^
  |
  = note: `#[warn(unused_imports)]` on by default

warning: variables can be used directly in the `format!` string
  --> src/bin/test_hands.rs:37:13
   |
37 |             assert_eq!(hand_classify(&hand), HandType::StraightFlush, "{} should be a straight flush", hand_str);
   |             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   |
   = help: for further information visit https://rust-lang.github.io/rust-clippy/master/index.html#uninlined_format_args
   = note: `-W clippy::uninlined-format-args` implied by `-W clippy::style`
   = help: to override `-W clippy::style` add `#[allow(clippy::uninlined_format_args)]`
help: change this to
   |
37 -             assert_eq!(hand_classify(&hand), HandType::StraightFlush, "{} should be a straight flush", hand_str);
37 +             assert_eq!(hand_classify(&hand), HandType::StraightFlush, "{hand_str} should be a straight flush");
   |

warning: variables can be used

... [output shortened] ...

om_string(&format!("{rank}{suit}"));
   |

warning: transmute used without annotations
  --> src/bin/test_cards.rs:86:51
   |
86 |             let c1 = Card::new(unsafe { std::mem::transmute(rank1) }, Suit::Club);
   |                                                   ^^^^^^^^^ help: consider adding missing annotations: `transmute::<u8, Holdem_Odds::cards::Rank>`
   |
   = help: for further information visit https://rust-lang.github.io/rust-clippy/master/index.html#missing_transmute_annotations

warning: transmute used without annotations
  --> src/bin/test_cards.rs:87:51
   |
87 |             let c2 = Card::new(unsafe { std::mem::transmute(rank2) }, Suit::Diamond);
   |                                                   ^^^^^^^^^ help: consider adding missing annotations: `transmute::<u8, Holdem_Odds::cards::Rank>`
   |
   = help: for further information visit https://rust-lang.github.io/rust-clippy/master/index.html#missing_transmute_annotations

warning: unused import: `Holdem_Odds::bucket::Bucket`
 --> src/bin/test_bucket.rs:1:5
  |
1 | use Holdem_Odds::bucket::Bucket;
  |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |
  = note: `#[warn(unused_imports)]` on by default

warning: unused imports: `Card`, `Rank`, and `Suit`
 --> src/bin/test_bucket.rs:2:26
  |
2 | use Holdem_Odds::cards::{Card, Rank, Suit};
  |                          ^^^^  ^^^^  ^^^^

warning: unused imports: `Card`, `Rank`, `Suit`, and `card_compare`
 --> src/bin/test_deck.rs:1:26
  |
1 | use Holdem_Odds::cards::{Card, Rank, Suit, card_compare};
  |                          ^^^^  ^^^^  ^^^^  ^^^^^^^^^^^^
  |
  = note: `#[warn(unused_imports)]` on by default

warning: unused imports: `deck_shuffle` and `new_deck`
 --> src/bin/test_deck.rs:2:25
  |
2 | use Holdem_Odds::deck::{new_deck, deck_shuffle};
  |                         ^^^^^^^^  ^^^^^^^^^^^^

warning: unused import: `rand::thread_rng`
 --> src/bin/test_deck.rs:3:5
  |
3 | use rand::thread_rng;
  |     ^^^^^^^^^^^^^^^^

warning: `Holdem_Odds` (bin "test_cards") generated 1 warning (run `cargo clippy --fix --bin "test_cards"` to apply 1 suggestion)
warning: `Holdem_Odds` (bin "test_hands" test) generated 15 warnings (run `cargo clippy --fix --bin "test_hands" --tests` to apply 15 suggestions)
warning: `Holdem_Odds` (bin "test_hands") generated 4 warnings (run `cargo clippy --fix --bin "test_hands"` to apply 3 suggestions)
warning: `Holdem_Odds` (bin "test_deck" test) generated 2 warnings (run `cargo clippy --fix --bin "test_deck" --tests` to apply 2 suggestions)
warning: `Holdem_Odds` (bin "test_cards" test) generated 7 warnings (run `cargo clippy --fix --bin "test_cards" --tests` to apply 1 suggestion)
warning: `Holdem_Odds` (bin "test_bucket") generated 2 warnings (run `cargo clippy --fix --bin "test_bucket"` to apply 2 suggestions)
warning: `Holdem_Odds` (bin "test_deck") generated 3 warnings (run `cargo clippy --fix --bin "test_deck"` to apply 3 suggestions)
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.02s

```

## What to do

Read the feedback above, find the cause of each problem in your Rust code, and repair it. Keep the
same rules as before: do not modify the tests or `Cargo.toml`, keep the required interface, no
`unsafe`, and match the behavior of the C code. Re-run build, tests, and Clippy yourself after your
changes, and finish with a short summary of the final status.
