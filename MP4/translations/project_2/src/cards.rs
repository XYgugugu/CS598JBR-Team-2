pub const RANKS_PER_DECK: usize = 13;
pub const SUITS_PER_DECK: usize = 4;
pub const RANK_CHARS: &str = "23456789TJQKA";
pub const SUIT_CHARS: &str = "cdhs";

/// Valid ranks, in the same order as `RANK_CHARS`.
const RANKS: [Rank; RANKS_PER_DECK] = [
    Rank::Deuce,
    Rank::Trey,
    Rank::Four,
    Rank::Five,
    Rank::Six,
    Rank::Seven,
    Rank::Eight,
    Rank::Nine,
    Rank::Ten,
    Rank::Jack,
    Rank::Queen,
    Rank::King,
    Rank::Ace,
];

/// Valid suits, in the same order as `SUIT_CHARS`.
const SUITS: [Suit; SUITS_PER_DECK] = [Suit::Club, Suit::Diamond, Suit::Heart, Suit::Spade];

/// Character used to display an invalid rank or suit.
const INVALID_CHAR: char = '-';

#[derive(Debug, PartialEq, Eq, Copy, Clone)]
pub enum Suit {
    InvalidSuit,
    Club,
    Diamond,
    Heart,
    Spade,
}

#[derive(Debug, PartialEq, Eq, Copy, Clone, PartialOrd, Ord)]
pub enum Rank {
    InvalidRank,
    Deuce,
    Trey,
    Four,
    Five,
    Six,
    Seven,
    Eight,
    Nine,
    Ten,
    Jack,
    Queen,
    King,
    Ace,
}

#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub struct Card {
    pub rank: Rank,
    pub suit: Suit,
}

const INVALID_CARD: Card = Card {
    rank: Rank::InvalidRank,
    suit: Suit::InvalidSuit,
};

impl Card {
    /// Create a new card; returns an invalid card if either part is invalid.
    pub fn new(rank: Rank, suit: Suit) -> Self {
        let card = Card { rank, suit };
        if card.is_valid() { card } else { INVALID_CARD }
    }

    /// Create a card from a 2-character string such as `"As"`.
    pub fn from_string(s: &str) -> Card {
        let mut chars = s.chars();
        match (chars.next(), chars.next(), chars.next()) {
            (Some(rank), Some(suit), None) => Card::from_chars(rank, suit),
            _ => INVALID_CARD,
        }
    }

    /// Create a card from a rank character and a suit character.
    pub fn from_chars(rank: char, suit: char) -> Card {
        Card::new(Rank::from_char(rank), Suit::from_char(suit))
    }

    /// Whether both the rank and the suit are valid.
    pub fn is_valid(&self) -> bool {
        self.rank != Rank::InvalidRank && self.suit != Suit::InvalidSuit
    }

    /// 2-character representation of the card, `"--"` if invalid.
    pub fn to_string(&self) -> String {
        if self.is_valid() {
            [self.rank.to_char(), self.suit.to_char()].iter().collect()
        } else {
            [INVALID_CHAR, INVALID_CHAR].iter().collect()
        }
    }
}

pub fn card_swap(card1: &mut Card, card2: &mut Card) {
    std::mem::swap(card1, card2);
}

impl Rank {
    pub fn from_char(c: char) -> Rank {
        index_of(c, RANK_CHARS).map_or(Rank::InvalidRank, |i| RANKS[i])
    }

    pub fn to_char(&self) -> char {
        RANKS
            .iter()
            .zip(RANK_CHARS.chars())
            .find_map(|(rank, c)| (rank == self).then_some(c))
            .unwrap_or(INVALID_CHAR)
    }
}

impl Suit {
    pub fn from_char(c: char) -> Suit {
        index_of(c, SUIT_CHARS).map_or(Suit::InvalidSuit, |i| SUITS[i])
    }

    pub fn to_char(&self) -> char {
        SUITS
            .iter()
            .zip(SUIT_CHARS.chars())
            .find_map(|(suit, c)| (suit == self).then_some(c))
            .unwrap_or(INVALID_CHAR)
    }
}

/// Return the 0-based position of `c` in `chars`, or `None` if absent.
pub fn index_of(c: char, chars: &str) -> Option<usize> {
    chars.chars().position(|x| x == c)
}

pub fn char_to_rank(c: char) -> Rank {
    Rank::from_char(c)
}

pub fn char_to_suit(c: char) -> Suit {
    Suit::from_char(c)
}

pub fn new_card_from_chars(rank: char, suit: char) -> Card {
    Card::from_chars(rank, suit)
}

/// Compare cards by rank: negative if `card1` is lower, 0 if equal, positive if higher.
pub fn card_compare(card1: &Card, card2: &Card) -> i32 {
    card1.rank as i32 - card2.rank as i32
}

/// Whether two cards have the same rank and suit.
pub fn card_equal(card1: &Card, card2: &Card) -> bool {
    card1 == card2
}
