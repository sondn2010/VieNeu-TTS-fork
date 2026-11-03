"use client";

import { useState } from "react";

import { useUserProfileQuery } from "../../lib/api/use-user-profile-query";
import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import { mapAdminGuardError } from "./admin-guard-error-mapping";
import { useSetUserRoleMutation, useUpdateUserMutation, type AdminUserRow } from "./admin-api-hooks";
import { DeleteUserConfirmDialog } from "./delete-user-confirm-dialog";
import { ResetPasswordDialog } from "./reset-password-dialog";
import { RoleSelectWithGuards } from "./role-select-with-guards";

export interface UserProfileAdminCardProps {
  user: AdminUserRow;
}

export function UserProfileAdminCard({ user }: UserProfileAdminCardProps) {
  const { language } = useI18n();
  const t = getAdminMessages(language);
  const { data: actorProfile } = useUserProfileQuery();
  const [email, setEmail] = useState(user.email);
  const [username, setUsername] = useState(user.username);
  const [error, setError] = useState<string | null>(null);
  const [resetOpen, setResetOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const updateUser = useUpdateUserMutation(user.id);
  const setRole = useSetUserRoleMutation(user.id);
  const isSelf = actorProfile?.id === user.id;

  async function handleSaveProfile() {
    setError(null);
    try {
      await updateUser.mutateAsync({ email, username });
    } catch (err) {
      setError(mapAdminGuardError(err, t));
    }
  }

  async function handleToggleActive() {
    setError(null);
    try {
      await updateUser.mutateAsync({ is_active: !user.is_active });
    } catch (err) {
      setError(mapAdminGuardError(err, t));
    }
  }

  async function handleRoleChange(role: string) {
    setError(null);
    try {
      await setRole.mutateAsync(role);
    } catch (err) {
      setError(mapAdminGuardError(err, t));
    }
  }

  return (
    <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 10, padding: 16 }}>
      <h2 style={{ fontSize: 15, margin: "0 0 12px", color: "var(--color-text-primary)" }}>{t.userDetail.profileTitle}</h2>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
          {t.userDetail.emailLabel}
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
        </label>
        <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
          {t.userDetail.usernameLabel}
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
        </label>
        <RoleSelectWithGuards target={user} onChange={handleRoleChange} disabled={setRole.isPending} />
        {error && <p style={{ color: "var(--color-danger-text)", fontSize: 12, margin: 0 }}>{error}</p>}
        <div style={{ display: "flex", gap: 8, marginTop: 4, flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={handleSaveProfile}
            disabled={updateUser.isPending}
            style={{ background: "var(--color-accent)", color: "#fff", border: "none", borderRadius: 6, padding: "6px 12px" }}
          >
            {t.userDetail.saveButton}
          </button>
          <button type="button" onClick={handleToggleActive} disabled={updateUser.isPending || isSelf}>
            {user.is_active ? t.userDetail.disableButton : t.userDetail.enableButton}
          </button>
          <button type="button" onClick={() => setResetOpen(true)}>
            {t.userDetail.resetPasswordButton}
          </button>
          <button type="button" onClick={() => setDeleteOpen(true)} disabled={isSelf} style={{ color: "var(--color-danger-text)" }}>
            {t.userDetail.deleteButton}
          </button>
        </div>
      </div>
      {resetOpen && <ResetPasswordDialog userId={user.id} onClose={() => setResetOpen(false)} />}
      {deleteOpen && <DeleteUserConfirmDialog userId={user.id} email={user.email} onClose={() => setDeleteOpen(false)} />}
    </div>
  );
}
