"use client";

import { useState, type FormEvent } from "react";

import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import { useCreateDictionaryMutation } from "./admin-api-hooks";

const KINDS = ["english", "term", "name"] as const;

export interface CreateDictionaryDialogProps {
  onClose: () => void;
}

export function CreateDictionaryDialog({ onClose }: CreateDictionaryDialogProps) {
  const { language, messages } = useI18n();
  const t = getAdminMessages(language);
  const [name, setName] = useState("");
  const [kind, setKind] = useState<string>(KINDS[1]);
  const [error, setError] = useState<string | null>(null);
  const mutation = useCreateDictionaryMutation();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await mutation.mutateAsync({ name, kind });
      onClose();
    } catch {
      setError(t.guard.genericError);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t.createDictionaryDialog.title}
      style={{ position: "fixed", inset: 0, background: "rgba(5,5,10,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div style={{ width: 340, background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 12, padding: 20 }}>
        <h2 style={{ fontSize: 16, margin: "0 0 12px", color: "var(--color-text-primary)" }}>{t.createDictionaryDialog.title}</h2>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
            {t.createDictionaryDialog.nameLabel}
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
          </label>
          <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
            {t.createDictionaryDialog.kindLabel}
            <select value={kind} onChange={(e) => setKind(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }}>
              {KINDS.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          </label>
          {error && <p style={{ color: "var(--color-danger-text)", fontSize: 12, margin: 0 }}>{error}</p>}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <button type="button" onClick={onClose} disabled={mutation.isPending}>
              {messages.common.cancel}
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              style={{ background: "var(--color-accent)", color: "#fff", border: "none", borderRadius: 6, padding: "6px 12px" }}
            >
              {t.createDictionaryDialog.submitButton}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
