"use client";

import { useState, type FormEvent } from "react";

import { ApiError } from "../../lib/api/api-error";
import { apiFetch } from "../../lib/api/api-client-with-csrf";
import { useI18n } from "../../lib/i18n/i18n-provider";

const MIN_PASSWORD_LEN = 10;

export interface ChangePasswordDialogProps {
  onClose: () => void;
}

export function ChangePasswordDialog({ onClose }: ChangePasswordDialogProps) {
  const { messages } = useI18n();
  const t = messages.changePasswordDialog;
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (newPassword.length < MIN_PASSWORD_LEN) {
      setError(t.errorTooShort);
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(t.errorMismatch);
      return;
    }

    setSubmitting(true);
    try {
      await apiFetch("/api/v1/user/password", {
        method: "POST",
        body: { current_password: currentPassword, new_password: newPassword },
      });
      setSuccess(true);
    } catch (err) {
      if (err instanceof ApiError && err.code === "INVALID_CREDENTIALS") {
        setError(t.errorWrongCurrent);
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(t.errorTooShort);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t.title}
      style={{
        position: "fixed", inset: 0, background: "rgba(5,5,10,0.6)", display: "flex",
        alignItems: "center", justifyContent: "center", zIndex: 50,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          width: 360, background: "var(--color-surface)", border: "1px solid var(--color-border)",
          borderRadius: 12, padding: 20,
        }}
      >
        <h2 style={{ fontSize: 16, margin: "0 0 12px", color: "var(--color-text-primary)" }}>{t.title}</h2>
        {success ? (
          <div style={{ color: "var(--color-success-text)", fontSize: 13 }}>
            {t.success}
            <div style={{ marginTop: 12, textAlign: "right" }}>
              <button type="button" onClick={onClose}>
                {messages.common.close}
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
              {t.currentPasswordLabel}
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                style={{ width: "100%", padding: 8, marginTop: 4 }}
              />
            </label>
            <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
              {t.newPasswordLabel}
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={MIN_PASSWORD_LEN}
                style={{ width: "100%", padding: 8, marginTop: 4 }}
              />
            </label>
            <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
              {t.confirmPasswordLabel}
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={MIN_PASSWORD_LEN}
                style={{ width: "100%", padding: 8, marginTop: 4 }}
              />
            </label>
            {error && <p style={{ color: "var(--color-danger-text)", fontSize: 12, margin: 0 }}>{error}</p>}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 4 }}>
              <button type="button" onClick={onClose} disabled={submitting}>
                {messages.common.cancel}
              </button>
              <button
                type="submit"
                disabled={submitting}
                style={{ background: "var(--color-accent)", color: "#fff", border: "none", borderRadius: 6, padding: "6px 12px" }}
              >
                {t.submitButton}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
