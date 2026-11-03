/**
 * Character count and token estimate — pinned by
 * `tests/fixtures/text_contract_vectors/token_estimate_vectors.json`,
 * mirrored in Python at `src/vieneu_portal/text/character_count_and_token_estimate.py`.
 *
 * Both sides count code points of the NFC-normalized text, not UTF-16 units
 * (`.length`) or raw code points of a possibly-NFD string. `Array.from`
 * iterates a string by code point (surrogate pairs count as one), unlike
 * `.length`, which would count an astral character (e.g. an emoji) as two.
 */

export function countChars(text: string): number {
  return Array.from(text.normalize("NFC")).length;
}

/** Integer-only on both sides: `ceil(chars * rateMilli / 1000)`. */
export function estimateTokens(chars: number, rateMilli: number): number {
  return Math.floor((chars * rateMilli + 999) / 1000);
}
