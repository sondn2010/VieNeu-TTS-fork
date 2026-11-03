/**
 * Rule and compiled-rule-set types for the pronunciation dictionary matcher
 * (`pronunciation-dictionary-single-pass-matcher.ts`). Pinned by
 * `tests/fixtures/text_contract_vectors/dictionary_matcher_vectors.json`,
 * mirrored in Python at `src/vieneu_portal/text/pronunciation_rule_types.py`.
 */

/** Precedence rank at equal match length: account beats system beats the
 * English fallback list. */
export enum RuleLayer {
  ACCOUNT = 0,
  SYSTEM = 1,
  ENGLISH_FALLBACK = 2,
}

export interface Rule {
  id: string;
  source: string;
  target: string;
  wholeWord: boolean;
  caseSensitive: boolean;
  enabled: boolean;
  layer: RuleLayer;
  /** Stable tiebreak at equal length and layer: the account table's row
   * order, or (system pack order, then entry order within the pack). */
  listOrder: number;
}

export interface CompiledRuleSet {
  /** sorted: source length (code points) desc, layer asc, listOrder asc */
  rules: readonly Rule[];
  /** Indexed by `rule.source`'s first code point, lower-cased (not
   * case-folded — see the matcher module for why), each bucket keeping the
   * same overall order as `rules`. */
  index: ReadonlyMap<string, readonly Rule[]>;
  /** Enabled rules' source terms, for the math/chem normalizer. */
  sourceTerms: ReadonlySet<string>;
}

export function compileRules(rules: readonly Rule[]): CompiledRuleSet {
  const normalized: Rule[] = [];
  for (const r of rules) {
    if (!r.enabled) continue;
    const source = r.source.normalize("NFC").trim();
    if (!source) continue;
    normalized.push(source === r.source ? r : { ...r, source });
  }

  const ordered = [...normalized].sort((a, b) => {
    const lengthDiff = Array.from(b.source).length - Array.from(a.source).length;
    if (lengthDiff !== 0) return lengthDiff;
    if (a.layer !== b.layer) return a.layer - b.layer;
    return a.listOrder - b.listOrder;
  });

  const index = new Map<string, Rule[]>();
  for (const r of ordered) {
    const key = Array.from(r.source)[0]!.toLowerCase();
    const bucket = index.get(key);
    if (bucket) {
      bucket.push(r);
    } else {
      index.set(key, [r]);
    }
  }

  return {
    rules: ordered,
    index,
    sourceTerms: new Set(normalized.map((r) => r.source)),
  };
}
