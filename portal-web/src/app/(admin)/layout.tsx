"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { AppSidebar } from "../../components/sidebar/app-sidebar";
import { DisabledSupportChatButton } from "../../components/support/disabled-support-chat-button";
import { ApiError } from "../../lib/api/api-error";
import { useUserProfileQuery } from "../../lib/api/use-user-profile-query";
import { useI18n } from "../../lib/i18n/i18n-provider";

const ADMIN_ROLES = new Set(["ADMIN", "SUPERADMIN"]);

/** Static export means no server components or middleware — the guard is
 * this client layout: `GET /user/profile`, redirect to `/login/` on 401,
 * redirect `USER` accounts to `/studio/`. */
export default function AdminLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { messages } = useI18n();
  const { data: profile, isError, error, isLoading } = useUserProfileQuery();

  useEffect(() => {
    if (isError && error instanceof ApiError && error.status === 401) {
      router.replace("/login/");
      return;
    }
    if (profile && !ADMIN_ROLES.has(profile.role)) {
      router.replace("/studio/");
    }
  }, [isError, error, profile, router]);

  if (isLoading || !profile || !ADMIN_ROLES.has(profile.role)) {
    return (
      <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: "var(--color-text-secondary)" }}>{messages.common.loading}</p>
      </main>
    );
  }

  return (
    <div style={{ display: "flex" }}>
      <AppSidebar profile={profile} />
      <main style={{ flex: 1, minHeight: "100vh" }}>{children}</main>
      <DisabledSupportChatButton />
    </div>
  );
}
