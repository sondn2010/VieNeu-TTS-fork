/**
 * Single-pass, longest-match pronunciation dictionary matcher. Pinned by
 * `tests/fixtures/text_contract_vectors/dictionary_matcher_vectors.json`,
 * mirrored in Python at
 * `src/vieneu_portal/text/pronunciation_dictionary_single_pass_matcher.py`.
 *
 * Operates on code points (`Array.from(text)`), not UTF-16 units — the
 * Python mirror uses `list(text)` for the same reason. Comparisons use
 * `.toLowerCase()` (not a locale-aware fold): a fold could change a
 * candidate's length (e.g. German "ß" under some foldings), and match
 * correctness here never depends on comparing lengths after folding, only
 * on direct string equality of the lower-cased forms.
 */
import { CompiledRuleSet, Rule, RuleLayer } from "./pronunciation-rule-types";

const WORD_CHAR_RE = /^[\p{L}\p{N}]$/u;

function isWordChar(ch: string): boolean {
  if (ch === "_") return true;
  return WORD_CHAR_RE.test(ch);
}

/** Index of `literal`'s first code point at or after `start`, or null. */
function findLiteral(cps: readonly string[], start: number, literal: string): number | null {
  const lit = Array.from(literal);
  const n = cps.length;
  const m = lit.length;
  for (let i = start; i <= n - m; i++) {
    let matched = true;
    for (let j = 0; j < m; j++) {
      if (cps[i + j] !== lit[j]) {
        matched = false;
        break;
      }
    }
    if (matched) return i;
  }
  return null;
}

function startsWithLiteral(cps: readonly string[], i: number, literal: string): boolean {
  const lit = Array.from(literal);
  if (i + lit.length > cps.length) return false;
  for (let j = 0; j < lit.length; j++) {
    if (cps[i + j] !== lit[j]) return false;
  }
  return true;
}

/**
 * Maps a protected span's start index to its (exclusive) end index.
 * `[...]`, `<en>...</en>` and `<|...|>` are never rewritten — an emotion tag
 * like `[cười]` must survive a rule matching the bare word `cười`, and a
 * target already wrapped in `<en>...</en>` is never rescanned. An
 * unterminated opener (no closing delimiter anywhere in the rest of the
 * text) is not protected — it is ordinary text.
 */
export function findProtectedSpans(cps: readonly string[]): Map<number, number> {
  const spans = new Map<number, number>();
  const n = cps.length;
  let i = 0;
  while (i < n) {
    if (cps[i] === "[") {
      let j = i + 1;
      while (j < n && cps[j] !== "]") j++;
      if (j < n) {
        spans.set(i, j + 1);
        i = j + 1;
        continue;
      }
    } else if (startsWithLiteral(cps, i, "<en>")) {
      const end = findLiteral(cps, i + 4, "</en>");
      if (end !== null) {
        spans.set(i, end + 5);
        i = end + 5;
        continue;
      }
    } else if (startsWithLiteral(cps, i, "<|")) {
      const end = findLiteral(cps, i + 2, "|>");
      if (end !== null) {
        spans.set(i, end + 2);
        i = end + 2;
        continue;
      }
    }
    i++;
  }
  return spans;
}

function matchAt(cps: readonly string[], i: number, n: number, compiled: CompiledRuleSet): [Rule, string] | null {
  const candidates = compiled.index.get(cps[i]!.toLowerCase()) ?? [];
  for (const r of candidates) {
    const sourceCps = Array.from(r.source);
    const length = sourceCps.length;
    if (i + length > n) continue;
    const candidate = cps.slice(i, i + length).join("");
    if (r.caseSensitive) {
      if (candidate !== r.source) continue;
    } else if (candidate.toLowerCase() !== r.source.toLowerCase()) {
      continue;
    }
    if (r.wholeWord) {
      const leftOk = i === 0 || !isWordChar(cps[i - 1]!);
      const rightOk = i + length >= n || !isWordChar(cps[i + length]!);
      if (!(leftOk && rightOk)) continue;
    }
    return [r, candidate];
  }
  return null;
}

function renderMatch(rule: Rule, matchedText: string): string {
  if (rule.layer === RuleLayer.ENGLISH_FALLBACK) {
    return `<en>${matchedText}</en>`;
  }
  return rule.target;
}

export function applyPronunciationRules(text: string, compiled: CompiledRuleSet): string {
  const cps = Array.from(text.normalize("NFC"));
  const n = cps.length;
  const spans = findProtectedSpans(cps);

  const out: string[] = [];
  let i = 0;
  while (i < n) {
    const spanEnd = spans.get(i);
    if (spanEnd !== undefined) {
      out.push(cps.slice(i, spanEnd).join(""));
      i = spanEnd;
      continue;
    }
    const matched = matchAt(cps, i, n, compiled);
    if (matched !== null) {
      const [rule, matchedText] = matched;
      out.push(renderMatch(rule, matchedText));
      i += Array.from(matchedText).length;
      continue;
    }
    out.push(cps[i]!);
    i++;
  }
  return out.join("");
}
