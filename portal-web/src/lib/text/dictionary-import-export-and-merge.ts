/**
 * Dictionary file import, export and merge — pinned by
 * `tests/fixtures/text_contract_vectors/dictionary_import_vectors.json`,
 * mirrored in Python at
 * `src/vieneu_portal/text/dictionary_import_export_and_merge.py`.
 */

export const MAX_SOURCE_OR_TARGET_LEN = 255;
export const MAX_RULES = 2000;
export const MAX_IMPORT_BYTES = 1_000_000;
export const MAX_IMPORT_LINES = 5_000;

// Priority order, not first-occurring-character order: if '=' appears
// anywhere in the line, split there even if ',' appears earlier —
// "Hà Nội, Việt Nam = Ha Noi" splits at '=', not the comma.
const SEPARATORS = ["=", "→", "\t", ","] as const;

export class ImportTooLargeError extends Error {}

export interface ImportedRule {
  source: string;
  target: string;
  wholeWord: boolean;
  caseSensitive: boolean;
  enabled: boolean;
}

export interface ImportLineError {
  line: number;
  message: string;
}

export interface MergeResult {
  rules: readonly ImportedRule[];
  error: string | null;
}

function makeImportedRule(source: string, target: string): ImportedRule {
  return { source, target, wholeWord: true, caseSensitive: false, enabled: true };
}

function importedRulesEqual(a: ImportedRule, b: ImportedRule): boolean {
  return (
    a.source === b.source &&
    a.target === b.target &&
    a.wholeWord === b.wholeWord &&
    a.caseSensitive === b.caseSensitive &&
    a.enabled === b.enabled
  );
}

export function validateRule(source: string, target: string): string[] {
  const errors: string[] = [];
  for (const [label, value] of [
    ["source", source],
    ["target", target],
  ] as const) {
    if (value.includes("\n") || value.includes("\r") || value.includes("\t")) {
      errors.push(`${label} must not contain a newline or tab`);
    }
    const len = Array.from(value).length;
    if (len < 1 || len > MAX_SOURCE_OR_TARGET_LEN) {
      errors.push(`${label} must be 1-${MAX_SOURCE_OR_TARGET_LEN} characters`);
    }
  }
  if (source.includes("=")) {
    errors.push("source must not contain '=' (breaks the export round-trip)");
  }
  return errors;
}

function splitOnSeparator(line: string): [string, string] | null {
  for (const sep of SEPARATORS) {
    const idx = line.indexOf(sep);
    if (idx !== -1) {
      return [line.slice(0, idx).trim(), line.slice(idx + sep.length).trim()];
    }
  }
  return null;
}

export function parseDictionaryImport(text: string): [readonly ImportedRule[], readonly ImportLineError[]] {
  if (new TextEncoder().encode(text).length > MAX_IMPORT_BYTES) {
    throw new ImportTooLargeError(`import text exceeds ${MAX_IMPORT_BYTES} bytes`);
  }
  let body = text;
  if (body.startsWith("﻿")) {
    body = body.slice(1);
  }
  const lines = body.split(/\r?\n/);
  if (lines.length > MAX_IMPORT_LINES) {
    throw new ImportTooLargeError(`import text exceeds ${MAX_IMPORT_LINES} lines`);
  }

  // Duplicate sources within the file: the last line wins, including its
  // position — `order` is rebuilt to put the winning occurrence last.
  const order: string[] = [];
  const byKey = new Map<string, ImportedRule>();
  const errors: ImportLineError[] = [];

  lines.forEach((rawLine, idx) => {
    const lineNo = idx + 1;
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) return;
    const split = splitOnSeparator(line);
    if (split === null) {
      errors.push({ line: lineNo, message: "no separator ('=', '→', tab or ',') found" });
      return;
    }
    const [source, target] = split;
    const ruleErrors = validateRule(source, target);
    if (ruleErrors.length > 0) {
      errors.push({ line: lineNo, message: ruleErrors.join("; ") });
      return;
    }
    const key = source.toLowerCase(); // imported rules default to caseSensitive=false
    if (byKey.has(key)) {
      const pos = order.indexOf(key);
      if (pos !== -1) order.splice(pos, 1);
    }
    order.push(key);
    byKey.set(key, makeImportedRule(source, target));
  });

  return [order.map((key) => byKey.get(key)!), errors];
}

/** Equal ignoring case when either rule is case-insensitive, else exact equal. */
function conflicts(existing: ImportedRule, imported: ImportedRule): boolean {
  if (!existing.caseSensitive || !imported.caseSensitive) {
    return existing.source.toLowerCase() === imported.source.toLowerCase();
  }
  return existing.source === imported.source;
}

/**
 * Imported rules first (file order), then existing rules minus any that
 * conflict with an imported one. Over `MAX_RULES` after merging is a hard
 * error — never silently truncated.
 */
export function mergeImportedRules(
  existing: readonly ImportedRule[],
  imported: readonly ImportedRule[],
): MergeResult {
  const kept = existing.filter((e) => !imported.some((i) => conflicts(e, i)));
  const merged = [...imported, ...kept];
  if (merged.length > MAX_RULES) {
    return { rules: [], error: "DICTIONARY_LIMIT_EXCEEDED" };
  }
  return { rules: merged, error: null };
}

/**
 * `source = target` per line; re-importing this text round-trips exactly,
 * since `validateRule` already forbids '=' in `source`.
 */
export function exportDictionaryTxt(rules: readonly ImportedRule[]): string {
  const lines = ["# exported", ...rules.map((r) => `${r.source} = ${r.target}`)];
  return lines.join("\n") + "\n";
}

export { importedRulesEqual };
