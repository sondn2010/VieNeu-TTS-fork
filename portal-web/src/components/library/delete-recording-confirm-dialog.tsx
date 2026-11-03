"use client";

import { useI18n } from "../../lib/i18n/i18n-provider";

export interface DeleteRecordingConfirmDialogProps {
  onConfirm: () => void;
  onCancel: () => void;
}

export function DeleteRecordingConfirmDialog({ onConfirm, onCancel }: DeleteRecordingConfirmDialogProps) {
  const { messages } = useI18n();
  const t = messages.library;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t.deleteConfirmTitle}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(5,5,10,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div style={{ width: 360, background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 12, padding: 20 }}>
        <h2 style={{ fontSize: 16, margin: "0 0 8px", color: "var(--color-text-primary)" }}>{t.deleteConfirmTitle}</h2>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "0 0 16px" }}>{t.deleteConfirmBody}</p>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button type="button" onClick={onCancel}>
            {messages.common.cancel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            style={{ background: "var(--color-danger-badge)", color: "#fff", border: "none", borderRadius: 6, padding: "6px 12px" }}
          >
            {t.deleteConfirmButton}
          </button>
        </div>
      </div>
    </div>
  );
}
