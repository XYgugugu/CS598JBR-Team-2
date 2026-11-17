use rand::seq::SliceRandom;
use rand::thread_rng;

use crate::cards::{Card, RANK_CHARS, RANKS_PER_DECK, Rank, SUIT_CHARS, SUITS_PER_DECK, Suit};

pub const CARDS_PER_DECK: usize = 52;

/// Build a full deck ordered by rank (Deuce to Ace), then suit (club, diamond, heart, spade).
pub fn new_deck() -> Vec<Card> {
    let mut deck = Vec::with_capacity(RANKS_PER_DECK * SUITS_PER_DECK);
    for rank in RANK_CHARS.chars().map(Rank::from_char) {
        deck.extend(
            SUIT_CHARS
                .chars()
                .map(Suit::from_char)
                .map(|suit| Card::new(rank, suit)),
        );
    }
    deck
}

/// Shuffle the deck in place.
pub fn deck_shuffle(deck: &mut Vec<Card>) {
    deck.shuffle(&mut thread_rng());
}
