use crate::bucket;
use crate::cards::{Card, RANKS_PER_DECK, Rank, card_compare};

const HAND_LENGTH: usize = 5;

#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Copy, Clone)]
pub enum HandType {
    InvalidHand,
    HighCard,
    Pair,
    TwoPair,
    ThreeOfAKind,
    Straight,
    Wheel,
    Flush,
    FullHouse,
    FourOfAKind,
    StraightFlush,
    WheelFlush,
}

impl HandType {
    /// Strength of the hand type, as defined by the original C enum order
    /// (a wheel is weaker than any other straight, and a wheel flush is
    /// weaker than any other straight flush).
    fn strength(self) -> i32 {
        match self {
            HandType::InvalidHand => 0,
            HandType::HighCard => 1,
            HandType::Pair => 2,
            HandType::TwoPair => 3,
            HandType::ThreeOfAKind => 4,
            HandType::Wheel => 5,
            HandType::Straight => 6,
            HandType::Flush => 7,
            HandType::FullHouse => 8,
            HandType::FourOfAKind => 9,
            HandType::WheelFlush => 10,
            HandType::StraightFlush => 11,
        }
    }
}

/// Compare two sorted hands: negative if `hand1` is weaker, 0 on a tie,
/// positive if `hand1` is stronger.
pub fn hand_compare(hand1: &[Card; 5], hand2: &[Card; 5]) -> i32 {
    let diff = hand_classify(hand1).strength() - hand_classify(hand2).strength();
    if diff != 0 {
        return diff;
    }
    hand1
        .iter()
        .zip(hand2)
        .map(|(a, b)| card_compare(a, b))
        .find(|&cmp| cmp != 0)
        .unwrap_or(0)
}

/// Sort cards by the number of cards sharing their rank, then by rank,
/// from strongest to weakest.
pub fn hand_sort(hand: &mut [Card; 5]) {
    let mut buckets = [bucket::Bucket::new(); RANKS_PER_DECK];
    let mut unplaced = Vec::new();

    for card in hand.iter() {
        match (card.rank as usize).checked_sub(1) {
            Some(index) if index < RANKS_PER_DECK => buckets[index].add(*card),
            _ => unplaced.push(*card),
        }
    }

    let sorted = (1..=4)
        .rev()
        .flat_map(|count| {
            buckets
                .iter()
                .rev()
                .filter(move |b| b.count == count)
                .flat_map(|b| b.cards.iter().flatten().copied())
        })
        .chain(unplaced);

    for (slot, card) in hand.iter_mut().zip(sorted) {
        *slot = card;
    }
}

/// Classify a sorted hand, checking from the strongest type to the weakest.
pub fn hand_classify(cards: &[Card; 5]) -> HandType {
    if hand_is_straight_flush(cards) {
        HandType::StraightFlush
    } else if hand_is_wheel_flush(cards) {
        HandType::WheelFlush
    } else if hand_is_flush(cards) {
        HandType::Flush
    } else if hand_is_four_of_a_kind(cards) {
        HandType::FourOfAKind
    } else if hand_is_full_house(cards) {
        HandType::FullHouse
    } else if hand_is_straight(cards) {
        HandType::Straight
    } else if hand_is_wheel(cards) {
        HandType::Wheel
    } else if hand_is_three_of_a_kind(cards) {
        HandType::ThreeOfAKind
    } else if hand_is_two_pair(cards) {
        HandType::TwoPair
    } else if hand_is_pair(cards) {
        HandType::Pair
    } else if hand_is_high_card(cards) {
        HandType::HighCard
    } else {
        HandType::InvalidHand
    }
}

/// A valid hand contains only valid cards.
pub fn hand_is_valid(cards: &[Card; 5]) -> bool {
    cards.iter().take(HAND_LENGTH).all(Card::is_valid)
}

fn hand_is_straight_flush(cards: &[Card; 5]) -> bool {
    hand_is_straight(cards) && hand_is_flush(cards)
}

fn hand_is_wheel_flush(cards: &[Card; 5]) -> bool {
    hand_is_wheel(cards) && hand_is_flush(cards)
}

fn hand_is_four_of_a_kind(cards: &[Card; 5]) -> bool {
    cards[0].rank == cards[3].rank
}

fn hand_is_full_house(cards: &[Card; 5]) -> bool {
    cards[0].rank == cards[2].rank && cards[3].rank == cards[4].rank
}

fn hand_is_flush(cards: &[Card; 5]) -> bool {
    cards.iter().all(|c| c.suit == cards[0].suit)
}

fn hand_is_straight(cards: &[Card; 5]) -> bool {
    let first = cards[0].rank as i32;
    first == cards[1].rank as i32 + 1 && first == cards[4].rank as i32 + 4
}

fn hand_is_wheel(cards: &[Card; 5]) -> bool {
    cards[0].rank == Rank::Ace && cards[1].rank == Rank::Five
}

fn hand_is_three_of_a_kind(cards: &[Card; 5]) -> bool {
    cards[0].rank == cards[2].rank
}

fn hand_is_two_pair(cards: &[Card; 5]) -> bool {
    cards[2].rank == cards[3].rank
}

fn hand_is_pair(cards: &[Card; 5]) -> bool {
    cards[0].rank == cards[1].rank
}

fn hand_is_high_card(_cards: &[Card; 5]) -> bool {
    true
}
