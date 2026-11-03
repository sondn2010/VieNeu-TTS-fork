"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import { useDeleteUserMutation } from "./admin-api-hooks";

export interface DeleteUserConfirmDialogProps {
  userId: string;
  email: string;
  onClose: () => void;
}

export function DeleteUserConfirmDialog({ userId, email, onClose }: DeleteUserConfirmDialogProps) {
  const router = useRouter();
  const { language, messages } = useI18n();
  const t = getAdminMessages(language);
  const [confirmEmail, setConfirmEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const mutation = useDeleteUserMutation(userId);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (confirmEmail.trim().toLowerCase() !== email.toLowerCase()) {
      setError(t.deleteUserDialog.errorMismatch);
      return;
    }
    try {
      await mutation.mutateAsync(confirmEmail);
      router.push("/admin/users/");
    } catch {
      setError(t.guard.genericError);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t.deleteUserDialog.title}
      style={{ position: "fixed", inset: 0, background: "rgba(5,5,10,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div style={{ width: 380, background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 12, padding: 20 }}>
        <h2 style={{ fontSize: 16, margin: "0 0 8px", color: "var(--color-text-primary)" }}>{t.deleteUserDialog.title}</h2>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "0 0 12px" }}>{t.deleteUserDialog.body}</p>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
            {t.deleteUserDialog.confirmEmailLabel}
            <input
              type="text"
              value={confirmEmail}
              onChange={(e) => setConfirmEmail(e.target.value)}
              placeholder={email}
              style={{ width: "100%", padding: 8, marginTop: 4 }}
            />
          </label>
          {error && <p style={{ color: "var(--color-danger-text)", fontSize: 12, margin: 0 }}>{error}</p>}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <button type="button" onClick={onClose} disabled={mutation.isPending}>
              {messages.common.cancel}
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              style={{ background: "var(--color-danger-badge)", color: "#fff", border: "none", borderRadius: 6, padding: "6px 12px" }}
            >
              {t.deleteUserDialog.submitButton}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
