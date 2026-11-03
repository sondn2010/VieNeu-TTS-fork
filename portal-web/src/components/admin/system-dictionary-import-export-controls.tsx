"use client";

import { useState, type FormEvent } from "react";

import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import { useImportDictionaryMutation, type AdminDictionaryPack } from "./admin-api-hooks";

export interface SystemDictionaryImportExportControlsProps {
  pack: AdminDictionaryPack;
  onClose: () => void;
}

/** The import side of "import/export" — export is a plain `<a download>`
 * per pack in `system-dictionary-pack-list.tsx` (a GET needs no CSRF and
 * carries the session cookie automatically, so a link is all it takes). */
export function SystemDictionaryImportExportControls({ pack, onClose }: SystemDictionaryImportExportControlsProps) {
  const { language, messages } = useI18n();
  const t = getAdminMessages(language);
  const [format, setFormat] = useState<"json" | "txt">("json");
  const [mode, setMode] = useState<"merge" | "replace">("merge");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resultSummary, setResultSummary] = useState<string | null>(null);
  const mutation = useImportDictionaryMutation(pack.id);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!file) {
      setError(t.guard.genericError);
      return;
    }
    try {
      const result = await mutation.mutateAsync({ file, format, mode });
      setResultSummary(
        `${result.rejected.length} ${t.importDictionaryDialog.rejectedSummary}, ${result.line_errors.length} ${t.importDictionaryDialog.lineErrorsSummary}`,
      );
    } catch {
      setError(t.guard.genericError);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t.importDictionaryDialog.title}
      style={{ position: "fixed", inset: 0, background: "rgba(5,5,10,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div style={{ width: 380, background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 12, padding: 20 }}>
        <h2 style={{ fontSize: 16, margin: "0 0 12px", color: "var(--color-text-primary)" }}>
          {t.importDictionaryDialog.title} — {pack.name}
        </h2>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
            {t.importDictionaryDialog.formatLabel}
            <select value={format} onChange={(e) => setFormat(e.target.value as "json" | "txt")} style={{ width: "100%", padding: 8, marginTop: 4 }}>
              <option value="json">JSON</option>
              <option value="txt">TXT</option>
            </select>
          </label>
          <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
            {t.importDictionaryDialog.modeLabel}
            <select value={mode} onChange={(e) => setMode(e.target.value as "merge" | "replace")} style={{ width: "100%", padding: 8, marginTop: 4 }}>
              <option value="merge">{t.importDictionaryDialog.modeMerge}</option>
              <option value="replace">{t.importDictionaryDialog.modeReplace}</option>
            </select>
          </label>
          <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
            {t.importDictionaryDialog.fileLabel}
            <input type="file" accept=".json,.txt,.csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} style={{ width: "100%", marginTop: 4 }} />
          </label>
          {error && <p style={{ color: "var(--color-danger-text)", fontSize: 12, margin: 0 }}>{error}</p>}
          {resultSummary && <p style={{ color: "var(--color-success-text)", fontSize: 12, margin: 0 }}>{resultSummary}</p>}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <button type="button" onClick={onClose}>
              {messages.common.close}
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              style={{ background: "var(--color-accent)", color: "#fff", border: "none", borderRadius: 6, padding: "6px 12px" }}
            >
              {t.importDictionaryDialog.submitButton}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
