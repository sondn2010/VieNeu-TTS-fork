"use client";

import { useState, type FormEvent } from "react";

import { ApiError } from "../../lib/api/api-error";
import { useUserProfileQuery } from "../../lib/api/use-user-profile-query";
import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import { useCreateUserMutation } from "./admin-api-hooks";

const MIN_PASSWORD_LEN = 10;

export interface CreateUserDialogProps {
  onClose: () => void;
}

export function CreateUserDialog({ onClose }: CreateUserDialogProps) {
  const { language, messages } = useI18n();
  const t = getAdminMessages(language);
  const { data: profile } = useUserProfileQuery();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("USER");
  const [error, setError] = useState<string | null>(null);
  const mutation = useCreateUserMutation();

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await mutation.mutateAsync({ email, username: username || undefined, password, role });
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.code === "EMAIL_TAKEN") setError(t.guard.emailTaken);
      else if (err instanceof ApiError) setError(err.message);
      else setError(t.guard.genericError);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t.createUserDialog.title}
      style={{ position: "fixed", inset: 0, background: "rgba(5,5,10,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div style={{ width: 380, background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 12, padding: 20 }}>
        <h2 style={{ fontSize: 16, margin: "0 0 12px", color: "var(--color-text-primary)" }}>{t.createUserDialog.title}</h2>
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
            {t.createUserDialog.emailLabel}
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required style={{ width: "100%", padding: 8, marginTop: 4 }} />
          </label>
          <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
            {t.createUserDialog.usernameLabel}
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
          </label>
          <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
            {t.createUserDialog.passwordLabel}
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={MIN_PASSWORD_LEN}
              style={{ width: "100%", padding: 8, marginTop: 4 }}
            />
          </label>
          {profile?.role === "SUPERADMIN" && (
            <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
              {t.createUserDialog.roleLabel}
              <select value={role} onChange={(e) => setRole(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }}>
                <option value="USER">USER</option>
                <option value="ADMIN">ADMIN</option>
                <option value="SUPERADMIN">SUPERADMIN</option>
              </select>
            </label>
          )}
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
              {t.createUserDialog.submitButton}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
