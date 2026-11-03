"use client";

import { useState } from "react";

import { ApiError } from "../../lib/api/api-error";
import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import { applyPronunciationRules } from "../../lib/text/pronunciation-dictionary-single-pass-matcher";
import { RuleLayer, compileRules, type Rule } from "../../lib/text/pronunciation-rule-types";
import { useAdminDictionaryRulesQuery, useReplaceDictionaryRulesMutation, type AdminDictionaryRule } from "./admin-api-hooks";

interface EditableRule {
  key: string;
  source_term: string;
  phonetic_replacement: string;
  rule_kind: "REPLACE" | "ENGLISH_FALLBACK";
  match_whole_word: boolean;
  case_sensitive: boolean;
  is_enabled: boolean;
  note: string;
}

let nextTempId = 1;

function fromServerRule(rule: AdminDictionaryRule): EditableRule {
  return {
    key: rule.id,
    source_term: rule.source_term,
    phonetic_replacement: rule.phonetic_replacement,
    rule_kind: rule.rule_kind,
    match_whole_word: rule.match_whole_word,
    case_sensitive: rule.case_sensitive,
    is_enabled: rule.is_enabled,
    note: rule.note,
  };
}

function newRow(): EditableRule {
  return {
    key: `new-${nextTempId++}`,
    source_term: "",
    phonetic_replacement: "",
    rule_kind: "REPLACE",
    match_whole_word: true,
    case_sensitive: false,
    is_enabled: true,
    note: "",
  };
}

export interface SystemDictionaryRulesEditorProps {
  dictionaryId: number;
}

export function SystemDictionaryRulesEditor({ dictionaryId }: SystemDictionaryRulesEditorProps) {
  const { language, messages } = useI18n();
  const t = getAdminMessages(language);
  const query = useAdminDictionaryRulesQuery(dictionaryId);
  const replaceMutation = useReplaceDictionaryRulesMutation(dictionaryId);

  const [rows, setRows] = useState<EditableRule[]>([]);
  // Render-phase sync (the project's established pattern for adopting a
  // server value into local editable state without an effect — see
  // `theme-provider.tsx`): a plain state variable remembers the last etag
  // seen, so a fresh load (or a save that returns a new etag) replaces the
  // local rows exactly once.
  const [lastSyncedEtag, setLastSyncedEtag] = useState<string | undefined>(undefined);
  if (query.data && query.data.etag !== lastSyncedEtag) {
    setLastSyncedEtag(query.data.etag);
    setRows(query.data.items.map(fromServerRule));
  }

  const [error, setError] = useState<string | null>(null);
  const [previewText, setPreviewText] = useState("");

  function updateRow(key: string, patch: Partial<EditableRule>) {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  }

  function removeRow(key: string) {
    setRows((prev) => prev.filter((r) => r.key !== key));
  }

  async function handleSave() {
    if (!query.data) return;
    setError(null);
    try {
      await replaceMutation.mutateAsync({
        etag: query.data.etag,
        rules: rows
          .filter((r) => r.source_term.trim())
          .map((r) => ({
            term: r.source_term,
            replacement: r.phonetic_replacement,
            mode: r.rule_kind === "ENGLISH_FALLBACK" ? "en" : ("phonetic" as const),
            case_sensitive: r.case_sensitive,
            note: r.note,
          })),
      });
    } catch (err) {
      if (err instanceof ApiError && err.code === "ETAG_MISMATCH") {
        setError(t.dictionaryDetail.etagConflict);
      } else {
        setError(t.guard.genericError);
      }
    }
  }

  const previewRules: Rule[] = rows
    .filter((r) => r.is_enabled && r.source_term.trim())
    .map((r, index) => ({
      id: r.key,
      source: r.source_term,
      target: r.phonetic_replacement,
      wholeWord: r.match_whole_word,
      caseSensitive: r.case_sensitive,
      enabled: true,
      layer: r.rule_kind === "ENGLISH_FALLBACK" ? RuleLayer.ENGLISH_FALLBACK : RuleLayer.SYSTEM,
      listOrder: index,
    }));
  const previewOutput = previewText ? applyPronunciationRules(previewText, compileRules(previewRules)) : "";

  if (query.isLoading) {
    return <p style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>{messages.common.loading}</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr style={{ textAlign: "left", color: "var(--color-text-secondary)" }}>
            <th>{t.dictionaryDetail.columnSource}</th>
            <th>{t.dictionaryDetail.columnReplacement}</th>
            <th>{t.dictionaryDetail.columnMode}</th>
            <th>{t.dictionaryDetail.columnWholeWord}</th>
            <th>{t.dictionaryDetail.columnCaseSensitive}</th>
            <th>{t.dictionaryDetail.columnEnabled}</th>
            <th>{t.dictionaryDetail.columnNote}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              <td>
                <input value={row.source_term} onChange={(e) => updateRow(row.key, { source_term: e.target.value })} style={{ width: 120 }} />
              </td>
              <td>
                <input
                  value={row.phonetic_replacement}
                  onChange={(e) => updateRow(row.key, { phonetic_replacement: e.target.value })}
                  disabled={row.rule_kind === "ENGLISH_FALLBACK"}
                  style={{ width: 140 }}
                />
              </td>
              <td>
                <select value={row.rule_kind} onChange={(e) => updateRow(row.key, { rule_kind: e.target.value as EditableRule["rule_kind"] })}>
                  <option value="REPLACE">{t.dictionaryDetail.modePhonetic}</option>
                  <option value="ENGLISH_FALLBACK">{t.dictionaryDetail.modeEnglishFallback}</option>
                </select>
              </td>
              <td>
                <input type="checkbox" checked={row.match_whole_word} onChange={(e) => updateRow(row.key, { match_whole_word: e.target.checked })} />
              </td>
              <td>
                <input type="checkbox" checked={row.case_sensitive} onChange={(e) => updateRow(row.key, { case_sensitive: e.target.checked })} />
              </td>
              <td>
                <input type="checkbox" checked={row.is_enabled} onChange={(e) => updateRow(row.key, { is_enabled: e.target.checked })} />
              </td>
              <td>
                <input value={row.note} onChange={(e) => updateRow(row.key, { note: e.target.value })} style={{ width: 100 }} />
              </td>
              <td>
                <button type="button" onClick={() => removeRow(row.key)} style={{ fontSize: 11 }}>
                  {t.dictionaryDetail.removeRowButton}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ display: "flex", gap: 10 }}>
        <button type="button" onClick={() => setRows((prev) => [...prev, newRow()])}>
          {t.dictionaryDetail.addRuleButton}
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={replaceMutation.isPending}
          style={{ background: "var(--color-accent)", color: "#fff", border: "none", borderRadius: 6, padding: "6px 12px" }}
        >
          {t.dictionaryDetail.saveButton}
        </button>
      </div>
      {error && <p style={{ color: "var(--color-danger-text)", fontSize: 12, margin: 0 }}>{error}</p>}

      <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: 12 }}>
        <h3 style={{ fontSize: 13, color: "var(--color-text-primary)", margin: "0 0 6px" }}>{t.dictionaryDetail.previewTitle}</h3>
        <textarea
          value={previewText}
          onChange={(e) => setPreviewText(e.target.value)}
          placeholder={t.dictionaryDetail.previewPlaceholder}
          style={{ width: "100%", minHeight: 60, padding: 8 }}
        />
        {previewText && <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginTop: 6 }}>{previewOutput}</p>}
      </div>
    </div>
  );
}
