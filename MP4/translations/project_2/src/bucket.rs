use crate::cards::Card;

/// A small container holding up to four cards of the same rank.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Bucket {
    pub cards: [Option<Card>; 4],
    pub count: usize,
}

impl Bucket {
    /// Create an empty bucket.
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a card to the bucket; ignored if the bucket is already full.
    pub fn add(&mut self, card: Card) {
        if let Some(slot) = self.cards.get_mut(self.count) {
            *slot = Some(card);
            self.count += 1;
        }
    }
}
