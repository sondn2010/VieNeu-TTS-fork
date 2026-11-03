"use client";

import { useState, type FormEvent } from "react";

import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import { useAdminResetPasswordMutation } from "./admin-api-hooks";

const MIN_PASSWORD_LEN = 10;

export interface ResetPasswordDialogProps {
  userId: string;
  onClose: () => void;
}

export function ResetPasswordDialog({ userId, onClose }: ResetPasswordDialogProps) {
  const { language, messages } = useI18n();
  const t = getAdminMessages(language);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const mutation = useAdminResetPasswordMutation(userId);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (newPassword.length < MIN_PASSWORD_LEN) {
      setError(t.resetPasswordDialog.errorTooShort);
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(t.resetPasswordDialog.errorMismatch);
      return;
    }
    try {
      await mutation.mutateAsync(newPassword);
      setSuccess(true);
    } catch {
      setError(t.guard.genericError);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t.resetPasswordDialog.title}
      style={{ position: "fixed", inset: 0, background: "rgba(5,5,10,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div style={{ width: 360, background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 12, padding: 20 }}>
        <h2 style={{ fontSize: 16, margin: "0 0 12px", color: "var(--color-text-primary)" }}>{t.resetPasswordDialog.title}</h2>
        {success ? (
          <div style={{ color: "var(--color-success-text)", fontSize: 13 }}>
            {t.resetPasswordDialog.success}
            <div style={{ marginTop: 12, textAlign: "right" }}>
              <button type="button" onClick={onClose}>
                {messages.common.close}
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
              {t.resetPasswordDialog.newPasswordLabel}
              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
            </label>
            <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
              {t.resetPasswordDialog.confirmPasswordLabel}
              <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
            </label>
            {error && <p style={{ color: "var(--color-danger-text)", fontSize: 12, margin: 0 }}>{error}</p>}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 4 }}>
              <button type="button" onClick={onClose} disabled={mutation.isPending}>
                {messages.common.cancel}
              </button>
              <button
                type="submit"
                disabled={mutation.isPending}
                style={{ background: "var(--color-accent)", color: "#fff", border: "none", borderRadius: 6, padding: "6px 12px" }}
              >
                {t.resetPasswordDialog.submitButton}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
