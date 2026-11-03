"use client";

import { useQueryClient } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiFetch } from "../../lib/api/api-client-with-csrf";
import { USER_PROFILE_QUERY_KEY, type UserProfile } from "../../lib/api/use-user-profile-query";
import { useI18n } from "../../lib/i18n/i18n-provider";
import { ChangePasswordDialog } from "../account/change-password-dialog";

export interface UserProfileCardProps {
  profile: UserProfile;
}

export function UserProfileCard({ profile }: UserProfileCardProps) {
  const { messages } = useI18n();
  const queryClient = useQueryClient();
  const router = useRouter();
  const [dialogOpen, setDialogOpen] = useState(false);

  async function handleLogout() {
    try {
      await apiFetch("/api/v1/auth/logout", { method: "POST" });
    } finally {
      queryClient.removeQueries({ queryKey: USER_PROFILE_QUERY_KEY });
      router.push("/login/");
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: "10px 12px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div
          aria-hidden
          style={{
            width: 32, height: 32, borderRadius: "50%", background: "var(--color-accent)",
            color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, fontWeight: 700, flexShrink: 0,
          }}
        >
          {profile.avatar_initials}
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div
            style={{
              fontSize: 13, color: "var(--color-text-primary)", overflow: "hidden",
              textOverflow: "ellipsis", whiteSpace: "nowrap",
            }}
          >
            {profile.email}
          </div>
          <div style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>
            {messages.profile.planLabel}: {profile.plan_tier}
          </div>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          aria-label={messages.sidebar.logout}
          title={messages.sidebar.logout}
          style={{ background: "none", border: "none", cursor: "pointer", color: "var(--color-text-secondary)" }}
        >
          <LogOut size={16} aria-hidden />
        </button>
      </div>
      <button
        type="button"
        onClick={() => setDialogOpen(true)}
        style={{
          background: "none", border: "1px solid var(--color-border)", borderRadius: 6, padding: "6px 10px",
          color: "var(--color-text-secondary)", fontSize: 12, cursor: "pointer", textAlign: "left",
        }}
      >
        {messages.profile.changePassword}
      </button>
      {dialogOpen && <ChangePasswordDialog onClose={() => setDialogOpen(false)} />}
    </div>
  );
}
