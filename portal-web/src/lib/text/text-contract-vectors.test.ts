/**
 * Drives the shared JSON vectors in `tests/fixtures/text_contract_vectors/`
 * against the TypeScript text-contract modules — the same vectors drive
 * the Python mirror (`tests/portal/test_text_contract_vectors.py`).
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { countChars, estimateTokens } from "./character-count-and-token-estimate";
import {
  ImportedRule,
  ImportTooLargeError,
  exportDictionaryTxt,
  mergeImportedRules,
  parseDictionaryImport,
  validateRule,
} from "./dictionary-import-export-and-merge";
import { applyPronunciationRules } from "./pronunciation-dictionary-single-pass-matcher";
import { Rule, RuleLayer, compileRules } from "./pronunciation-rule-types";

const VECTORS_DIR = join(__dirname, "..", "..", "..", "..", "tests", "fixtures", "text_contract_vectors");

function load<T>(name: string): T {
  return JSON.parse(readFileSync(join(VECTORS_DIR, name), "utf-8")) as T;
}

interface CharCountVector {
  description: string;
  text: string;
  expected_chars: number;
}

interface TokenEstimateVector {
  chars: number;
  rate_milli: number;
  expected_tokens: number;
}

interface TokenVectorsFile {
  char_count_vectors: CharCountVector[];
  token_estimate_vectors: TokenEstimateVector[];
}

interface MatcherRuleVector {
  source: string;
  target: string;
  whole_word: boolean;
  case_sensitive: boolean;
  enabled: boolean;
  layer: keyof typeof RuleLayer;
  list_order: number;
}

interface MatcherVector {
  description: string;
  text: string;
  rules: MatcherRuleVector[];
  expected: string;
}

interface ImportedRuleVector {
  source: string;
  target: string;
  whole_word: boolean;
  case_sensitive: boolean;
  enabled: boolean;
}

interface ParseVector {
  description: string;
  input: string;
  expected_rules: ImportedRuleVector[];
  expected_error_lines: number[];
}

interface MergeVector {
  description: string;
  existing: ImportedRuleVector[];
  imported: ImportedRuleVector[];
  expected_rules?: ImportedRuleVector[];
  expected_error?: string;
}

interface ImportVectorsFile {
  parse_vectors: ParseVector[];
  merge_vectors: MergeVector[];
}

const tokenVectors = load<TokenVectorsFile>("token_estimate_vectors.json");
const matcherVectors = load<{ matcher_vectors: MatcherVector[] }>("dictionary_matcher_vectors.json").matcher_vectors;
const importVectors = load<ImportVectorsFile>("dictionary_import_vectors.json");

function ruleFromVector(i: number, v: MatcherRuleVector): Rule {
  return {
    id: `r${i}`,
    source: v.source,
    target: v.target,
    wholeWord: v.whole_word,
    caseSensitive: v.case_sensitive,
    enabled: v.enabled,
    layer: RuleLayer[v.layer],
    listOrder: v.list_order,
  };
}

function importedRuleFromVector(v: ImportedRuleVector): ImportedRule {
  return {
    source: v.source,
    target: v.target,
    wholeWord: v.whole_word,
    caseSensitive: v.case_sensitive,
    enabled: v.enabled,
  };
}

describe("countChars / estimateTokens", () => {
  for (const vector of tokenVectors.char_count_vectors) {
    it(vector.description, () => {
      expect(countChars(vector.text)).toBe(vector.expected_chars);
    });
  }

  for (const vector of tokenVectors.token_estimate_vectors) {
    it(`chars=${vector.chars},rate=${vector.rate_milli}`, () => {
      expect(estimateTokens(vector.chars, vector.rate_milli)).toBe(vector.expected_tokens);
    });
  }
});

describe("applyPronunciationRules", () => {
  for (const vector of matcherVectors) {
    it(vector.description, () => {
      const rules = vector.rules.map((r, i) => ruleFromVector(i, r));
      const compiled = compileRules(rules);
      expect(applyPronunciationRules(vector.text, compiled)).toBe(vector.expected);
    });
  }

  it("performance benchmark: 2000 account + 848 seed + 10000 synthetic system rules", () => {
    const rules: Rule[] = [];
    for (let i = 0; i < 2000; i++) {
      rules.push({
        id: `a${i}`, source: `acct${String(i).padStart(4, "0")}`, target: `T${i}`, wholeWord: true,
        caseSensitive: false, enabled: true, layer: RuleLayer.ACCOUNT, listOrder: i,
      });
    }
    for (let i = 0; i < 848; i++) {
      rules.push({
        id: `s${i}`, source: `seed${String(i).padStart(4, "0")}`, target: `S${i}`, wholeWord: true,
        caseSensitive: false, enabled: true, layer: RuleLayer.SYSTEM, listOrder: i,
      });
    }
    for (let i = 0; i < 10000; i++) {
      rules.push({
        id: `y${i}`, source: `syn${String(i).padStart(5, "0")}`, target: `Y${i}`, wholeWord: true,
        caseSensitive: false, enabled: true, layer: RuleLayer.SYSTEM, listOrder: 1000 + i,
      });
    }

    const t0 = performance.now();
    const compiled = compileRules(rules);
    expect(performance.now() - t0).toBeLessThan(500);

    const words: string[] = [];
    for (let i = 0; words.join(" ").length < 20000; i++) words.push(`word${i}`);
    const text = words.join(" ").slice(0, 20000);

    const t1 = performance.now();
    applyPronunciationRules(text, compiled);
    expect(performance.now() - t1).toBeLessThan(200);
  });
});

describe("parseDictionaryImport", () => {
  for (const vector of importVectors.parse_vectors) {
    it(vector.description, () => {
      const [rules, errors] = parseDictionaryImport(vector.input);
      expect(rules).toEqual(vector.expected_rules.map(importedRuleFromVector));
      expect(errors.map((e) => e.line)).toEqual(vector.expected_error_lines);
    });
  }

  it("rejects an import over the byte cap instead of truncating", () => {
    expect(() => parseDictionaryImport("x".repeat(1_000_001))).toThrow(ImportTooLargeError);
  });

  it("rejects an import over the line cap instead of truncating", () => {
    expect(() => parseDictionaryImport("\n".repeat(5001))).toThrow(ImportTooLargeError);
  });
});

describe("mergeImportedRules", () => {
  for (const vector of importVectors.merge_vectors) {
    it(vector.description, () => {
      const existing = vector.existing.map(importedRuleFromVector);
      const imported = vector.imported.map(importedRuleFromVector);
      const result = mergeImportedRules(existing, imported);
      if (vector.expected_error !== undefined) {
        expect(result.error).toBe(vector.expected_error);
        expect(result.rules).toEqual([]);
      } else {
        expect(result.error).toBeNull();
        expect(result.rules).toEqual((vector.expected_rules ?? []).map(importedRuleFromVector));
      }
    });
  }
});

describe("validateRule / exportDictionaryTxt", () => {
  it("rejects newline, tab and '=' in source; accepts a clean rule", () => {
    expect(validateRule("a\nb", "ok")).not.toEqual([]);
    expect(validateRule("a\tb", "ok")).not.toEqual([]);
    expect(validateRule("a=b", "ok")).not.toEqual([]);
    expect(validateRule("", "ok")).not.toEqual([]);
    expect(validateRule("x".repeat(256), "ok")).not.toEqual([]);
    expect(validateRule("ok", "ok")).toEqual([]);
  });

  it("round-trips export -> import exactly, even with '=' in a target", () => {
    const rules: ImportedRule[] = [
      { source: "VieNeu", target: "Vi Nơi", wholeWord: true, caseSensitive: false, enabled: true },
      { source: "GPU", target: "Gờ Pê U = viết tắt", wholeWord: true, caseSensitive: false, enabled: true },
    ];
    const text = exportDictionaryTxt(rules);
    const [reimported, errors] = parseDictionaryImport(text);
    expect(errors).toEqual([]);
    expect(reimported).toEqual(rules);
  });
});
