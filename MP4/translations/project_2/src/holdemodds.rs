use std::env;
use std::process;

use rand::seq::SliceRandom;
use rand::thread_rng;

use crate::cards::Card;
use crate::deck::new_deck;
use crate::hands::{hand_compare, hand_sort};

pub const HOLDEMODDS_VERSION: &str = "0.0.0";

const ITERATIONS: usize = 2_000_000;
const BOARD_CARDS: usize = 3;

fn usage(program_name: &str) {
    eprintln!("Usage: {program_name} <c1> <c2> <c3> <c4>");
    process::exit(1);
}

/// Entry point of the odds simulator: estimates win/tie/loss frequencies of
/// the hand `c1 c2` against `c3 c4` over random 3-card boards.
pub fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 5 {
        usage(args.first().map_or("holdemodds", String::as_str));
        return;
    }

    let cards: Vec<Card> = args[1..].iter().map(|s| Card::from_string(s)).collect();
    let mut deck: Vec<Card> = new_deck()
        .into_iter()
        .filter(|c| !cards.contains(c))
        .collect();

    let mut rng = thread_rng();
    let (mut wins, mut ties, mut losses) = (0usize, 0usize, 0usize);

    for _ in 0..ITERATIONS {
        let (board, _) = deck.partial_shuffle(&mut rng, BOARD_CARDS);
        let mut hand1 = [cards[0], cards[1], board[0], board[1], board[2]];
        let mut hand2 = [cards[2], cards[3], board[0], board[1], board[2]];

        hand_sort(&mut hand1);
        hand_sort(&mut hand2);

        match hand_compare(&hand1, &hand2).signum() {
            1 => wins += 1,
            0 => ties += 1,
            _ => losses += 1,
        }
    }

    let total = ITERATIONS as f64;
    println!(
        "WIN: {:.2}\tTIE: {:.2}\tLOSS: {:.2}",
        wins as f64 / total,
        ties as f64 / total,
        losses as f64 / total
    );
}
