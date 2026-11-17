use std::cmp::Ordering;
use std::fmt;

/// Arbitrary precision signed integer stored as decimal digits,
/// most significant digit first.
#[derive(Clone, Debug)]
pub struct BigInt {
    negative: bool,
    digits: Vec<u8>,
}

/// Number of digits below which a value is handled with native `i64` arithmetic.
const NATIVE_DIGIT_LIMIT: usize = 10;

/// Returns the digits without leading zeros (`[0]` if the value is zero).
fn trim(digits: &[u8]) -> &[u8] {
    match digits.iter().position(|&d| d != 0) {
        Some(start) => &digits[start..],
        None => &[0],
    }
}

/// Removes leading zeros from an owned digit vector, keeping at least one digit.
fn normalize(mut digits: Vec<u8>) -> Vec<u8> {
    match digits.iter().position(|&d| d != 0) {
        Some(start) => {
            digits.drain(..start);
            digits
        }
        None => vec![0],
    }
}

/// Converts an intermediate value into a single decimal digit.
fn to_digit(value: i64) -> u8 {
    u8::try_from(value.rem_euclid(10)).unwrap_or_default()
}

/// Compares two magnitudes.
fn cmp_mag(a: &[u8], b: &[u8]) -> Ordering {
    let (a, b) = (trim(a), trim(b));
    a.len().cmp(&b.len()).then_with(|| a.cmp(b))
}

/// Adds two magnitudes.
fn add_mag(a: &[u8], b: &[u8]) -> Vec<u8> {
    let len = a.len().max(b.len());
    let mut a_iter = a.iter().rev();
    let mut b_iter = b.iter().rev();
    let mut result = Vec::with_capacity(len + 1);
    let mut carry = 0i64;
    for _ in 0..len {
        let sum = carry
            + a_iter.next().map_or(0, |&d| i64::from(d))
            + b_iter.next().map_or(0, |&d| i64::from(d));
        result.push(to_digit(sum));
        carry = sum / 10;
    }
    while carry > 0 {
        result.push(to_digit(carry));
        carry /= 10;
    }
    result.reverse();
    normalize(result)
}

/// Subtracts magnitude `small` from magnitude `large` (requires `large >= small`).
fn sub_mag(large: &[u8], small: &[u8]) -> Vec<u8> {
    let mut small_iter = small.iter().rev();
    let mut result = Vec::with_capacity(large.len());
    let mut borrow = 0i64;
    for &d in large.iter().rev() {
        let mut diff = i64::from(d) + borrow - small_iter.next().map_or(0, |&s| i64::from(s));
        if diff < 0 {
            diff += 10;
            borrow = -1;
        } else {
            borrow = 0;
        }
        result.push(to_digit(diff));
    }
    result.reverse();
    normalize(result)
}

/// Multiplies two magnitudes using schoolbook multiplication.
fn mul_mag(a: &[u8], b: &[u8]) -> Vec<u8> {
    let mut acc = vec![0i64; a.len() + b.len()];
    for (i, &da) in a.iter().rev().enumerate() {
        for (j, &db) in b.iter().rev().enumerate() {
            acc[i + j] += i64::from(da) * i64::from(db);
        }
    }
    let mut result = Vec::with_capacity(acc.len() + 1);
    let mut carry = 0i64;
    for value in acc {
        let sum = value + carry;
        result.push(to_digit(sum));
        carry = sum / 10;
    }
    while carry > 0 {
        result.push(to_digit(carry));
        carry /= 10;
    }
    result.reverse();
    normalize(result)
}

/// Long division of magnitudes; returns `(quotient, remainder)`.
fn divmod_mag(numerator: &[u8], denominator: &[u8]) -> (Vec<u8>, Vec<u8>) {
    let mut quotient = Vec::with_capacity(numerator.len());
    let mut remainder: Vec<u8> = Vec::new();
    for &d in numerator {
        remainder.push(d);
        remainder = normalize(remainder);
        let mut count = 0u8;
        while cmp_mag(&remainder, denominator) != Ordering::Less {
            remainder = sub_mag(&remainder, denominator);
            count += 1;
        }
        quotient.push(count);
    }
    (normalize(quotient), normalize(remainder))
}

impl BigInt {
    pub fn zero() -> Self {
        BigInt {
            negative: false,
            digits: vec![0],
        }
    }

    pub fn is_64_bit(&self) -> bool {
        self.digits.len() < NATIVE_DIGIT_LIMIT
    }

    pub fn remove_leading_zeros(&mut self) {
        let digits = std::mem::take(&mut self.digits);
        self.digits = normalize(digits);
    }

    pub fn from_int(n: i64) -> Self {
        BigInt {
            negative: n < 0,
            digits: n
                .unsigned_abs()
                .to_string()
                .bytes()
                .map(|b| b - b'0')
                .collect(),
        }
    }

    pub fn to_int(&self) -> i64 {
        let magnitude = self
            .digits
            .iter()
            .fold(0i64, |acc, &d| acc.wrapping_mul(10).wrapping_add(i64::from(d)));
        if self.negative {
            magnitude.wrapping_neg()
        } else {
            magnitude
        }
    }

    pub fn from_str(s: &str) -> Self {
        let (negative, body) = match s.strip_prefix('-') {
            Some(rest) => (true, rest),
            None => (false, s),
        };
        let digits: Vec<u8> = body.bytes().map(|b| b.wrapping_sub(b'0')).collect();
        BigInt {
            negative,
            digits: if digits.is_empty() { vec![0] } else { digits },
        }
    }

    pub fn copy(&self) -> BigInt {
        self.clone()
    }

    pub fn print(&self) {
        print!("{self}");
    }

    pub fn is_zero(&self) -> bool {
        trim(&self.digits) == [0]
    }

    pub fn lt_zero(&self) -> bool {
        !self.is_zero() && self.negative
    }

    pub fn gt_zero(&self) -> bool {
        !self.is_zero() && !self.negative
    }

    pub fn lezero(&self) -> bool {
        self.is_zero() || self.negative
    }

    pub fn gezero(&self) -> bool {
        self.is_zero() || !self.negative
    }

    pub fn abs(&self) -> Self {
        BigInt {
            negative: false,
            digits: self.digits.clone(),
        }
    }

    pub fn add(&self, other: &Self) -> Self {
        match (self.negative, other.negative) {
            (true, false) => other.sub(&self.abs()),
            (false, true) => self.sub(&other.abs()),
            (negative, _) => BigInt {
                negative,
                digits: add_mag(&self.digits, &other.digits),
            },
        }
    }

    pub fn sub(&self, other: &Self) -> Self {
        match (self.negative, other.negative) {
            // Mirrors the original library: both negative yields -(|a| + |b|),
            // and -a - b = -(|a| + |b|).
            (true, _) => BigInt {
                negative: true,
                digits: add_mag(&self.digits, &other.digits),
            },
            (false, true) => BigInt {
                negative: false,
                digits: add_mag(&self.digits, &other.digits),
            },
            (false, false) => {
                let digits = if gt(self, other) {
                    sub_mag(trim(&self.digits), trim(&other.digits))
                } else {
                    sub_mag(trim(&other.digits), trim(&self.digits))
                };
                BigInt {
                    negative: lt(self, other),
                    digits,
                }
            }
        }
    }

    pub fn inc(&mut self) {
        *self = BigInt::add(self, &BigInt::from_int(1));
    }

    pub fn dec(&mut self) {
        *self = BigInt::sub(self, &BigInt::from_int(1));
    }

    pub fn mul(&self, other: &Self) -> Self {
        if self.is_64_bit() && other.is_64_bit() {
            return BigInt::from_int(self.to_int().wrapping_mul(other.to_int()));
        }
        BigInt {
            negative: self.negative != other.negative,
            digits: mul_mag(&self.digits, &other.digits),
        }
    }

    /// Returns `(quotient, remainder)`.
    ///
    /// # Panics
    /// Panics on division by zero (the C library aborts or never terminates).
    pub fn divmod(&self, other: &Self) -> (Self, Self) {
        assert!(!other.is_zero(), "attempt to divide by zero");
        if self.is_64_bit() && other.is_64_bit() {
            let (n, d) = (self.to_int(), other.to_int());
            return (BigInt::from_int(n / d), BigInt::from_int(n % d));
        }
        let negative = self.negative != other.negative;
        let (quotient, remainder) = divmod_mag(trim(&self.digits), trim(&other.digits));
        (
            BigInt {
                negative,
                digits: quotient,
            },
            BigInt {
                negative,
                digits: remainder,
            },
        )
    }

    pub fn div(&self, other: &Self) -> Self {
        self.divmod(other).0
    }

    pub fn r#mod(&self, other: &Self) -> Self {
        self.divmod(other).1
    }

    pub fn pow(&self, exponent: &Self) -> Self {
        if exponent.negative {
            return BigInt::zero();
        }
        let mut result = BigInt::from_int(1);
        let mut remaining = exponent.clone();
        while !remaining.is_zero() {
            result = BigInt::mul(&result, self);
            remaining.dec();
        }
        result
    }

    fn native_fast_pow(base: i64, mut exp: i64, modulo: i64) -> i64 {
        let mut result = 1i64;
        let mut base = base % modulo;
        while exp > 0 {
            if exp % 2 == 1 {
                result = result.wrapping_mul(base) % modulo;
            }
            exp >>= 1;
            base = base.wrapping_mul(base) % modulo;
        }
        result
    }

    pub fn fast_pow(&self, exponent: &Self, modulo: &Self) -> Self {
        if self.is_64_bit() && exponent.is_64_bit() && modulo.is_64_bit() {
            return BigInt::from_int(Self::native_fast_pow(
                self.to_int(),
                exponent.to_int(),
                modulo.to_int(),
            ));
        }
        if exponent.negative {
            return BigInt::zero();
        }
        if exponent.is_zero() {
            return BigInt::from_int(1);
        }

        let two = BigInt::from_int(2);
        let base = self.r#mod(modulo);
        let mut result = base.clone();
        let mut halving = exponent.clone();
        halving.dec();
        let mut power = BigInt::from_int(1);

        // Repeatedly square while the exponent can be halved.
        while halving.div(&two).gt_zero() {
            result = BigInt::mul(&result, &result).r#mod(modulo);
            halving = halving.div(&two);
            power = BigInt::add(&power, &power);
        }

        let mut rest = BigInt::sub(exponent, &power);
        if rest.is_odd() {
            result = BigInt::mul(&result, &base).r#mod(modulo);
            rest.dec();
        }

        if lt(&rest, &BigInt::from_int(5)) {
            while !rest.is_zero() {
                result = BigInt::mul(&result, &base).r#mod(modulo);
                rest.dec();
            }
            return result;
        }

        let subpart = base.fast_pow(&rest, modulo);
        BigInt::mul(&result, &subpart).r#mod(modulo)
    }

    pub fn modinv(&self, modulo: &Self) -> Self {
        let mut y = BigInt::zero();
        let mut x = BigInt::from_int(1);
        let mut a = self.clone();
        let mut m = modulo.clone();

        while !a.is_zero() {
            let q = m.div(&a);
            let t = BigInt::sub(&m, &BigInt::mul(&q, &a));
            m = std::mem::replace(&mut a, t);
            let t = BigInt::sub(&y, &BigInt::mul(&q, &x));
            y = std::mem::replace(&mut x, t);
        }
        if m.lt_zero() {
            m = BigInt::add(&m, modulo);
        }

        if m != BigInt::from_int(1) {
            return BigInt::zero();
        }
        let result = y.r#mod(modulo);
        if result.lt_zero() {
            BigInt::add(&result, modulo)
        } else {
            result
        }
    }

    pub fn sqrt(&self) -> Self {
        let one = BigInt::from_int(1);
        let two = BigInt::from_int(2);
        let mut low = BigInt::zero();
        let mut high = self.clone();
        while lt(&low, &high) {
            let mid = BigInt::add(&low, &high).div(&two);
            if lt(&BigInt::mul(&mid, &mid), self) {
                low = BigInt::add(&mid, &one);
            } else {
                high = mid;
            }
        }
        low
    }

    pub fn is_even(&self) -> bool {
        self.digits.last().is_some_and(|d| d % 2 == 0)
    }

    pub fn is_odd(&self) -> bool {
        self.digits.last().is_some_and(|d| d % 2 == 1)
    }

    pub fn is_prime(&self) -> bool {
        if self.is_even() {
            return false;
        }
        if self.digits.len() > 1 && matches!(self.digits.last(), Some(0 | 5)) {
            return false;
        }
        let digit_sum: u64 = self.digits.iter().map(|&d| u64::from(d)).sum();
        if digit_sum % 3 == 0 {
            return false;
        }

        let sqrt_n = self.sqrt();
        let mut divisor = BigInt::from_int(2);
        while le(&divisor, &sqrt_n) {
            if self.r#mod(&divisor).is_zero() {
                return false;
            }
            divisor.inc();
        }
        true
    }
}

/// Mirrors the original comparison, which decides using the sign of `a` only.
pub fn gt(a: &BigInt, b: &BigInt) -> bool {
    let (da, db) = (trim(&a.digits), trim(&b.digits));
    match da.len().cmp(&db.len()).then_with(|| da.cmp(db)) {
        Ordering::Greater => !a.negative,
        Ordering::Less => a.negative,
        Ordering::Equal => false,
    }
}

pub fn lt(a: &BigInt, b: &BigInt) -> bool {
    !ge(a, b)
}

pub fn ge(a: &BigInt, b: &BigInt) -> bool {
    gt(a, b) || a == b
}

pub fn le(a: &BigInt, b: &BigInt) -> bool {
    !gt(a, b)
}

pub fn delete(a: &mut BigInt) {
    *a = BigInt::zero();
}

impl std::ops::Neg for BigInt {
    type Output = BigInt;
    fn neg(mut self) -> BigInt {
        self.negative = !self.negative;
        self
    }
}

impl PartialEq for BigInt {
    fn eq(&self, other: &Self) -> bool {
        self.negative == other.negative && trim(&self.digits) == trim(&other.digits)
    }
}

impl Eq for BigInt {}

impl Ord for BigInt {
    fn cmp(&self, other: &Self) -> Ordering {
        if gt(self, other) {
            Ordering::Greater
        } else if self == other {
            Ordering::Equal
        } else {
            Ordering::Less
        }
    }
}

impl PartialOrd for BigInt {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl fmt::Display for BigInt {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        if self.negative {
            write!(f, "-")?;
        }
        self.digits.iter().try_for_each(|d| write!(f, "{d}"))
    }
}
