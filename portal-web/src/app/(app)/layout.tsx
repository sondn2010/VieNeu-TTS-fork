"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { ApiError } from "../../lib/api/api-error";
import { useUserProfileQuery } from "../../lib/api/use-user-profile-query";
import { useI18n } from "../../lib/i18n/i18n-provider";
import { AppSidebar } from "../../components/sidebar/app-sidebar";
import { DisabledSupportChatButton } from "../../components/support/disabled-support-chat-button";
import { TermsConsentModal } from "../../components/terms/terms-consent-modal";

/**
 * Static export means no server components that fetch at request time and
 * no Next Middleware — the auth guard is this client layout, calling
 * `GET /user/profile` and redirecting to `/login/` on 401.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { messages } = useI18n();
  const { data: profile, isError, error, isLoading } = useUserProfileQuery();

  useEffect(() => {
    if (isError && error instanceof ApiError && error.status === 401) {
      router.replace("/login/");
    }
  }, [isError, error, router]);

  if (isLoading || !profile) {
    return (
      <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: "var(--color-text-secondary)" }}>{messages.common.loading}</p>
      </main>
    );
  }

  const termsAccepted = profile.has_accepted_tts_terms && profile.terms_version === profile.client_config.terms_version;

  return (
    <div style={{ display: "flex" }}>
      <AppSidebar profile={profile} />
      <main style={{ flex: 1, minHeight: "100vh" }}>{children}</main>
      <DisabledSupportChatButton />
      {!termsAccepted && (
        <TermsConsentModal termsVersion={profile.client_config.terms_version} onAccepted={() => {}} />
      )}
    </div>
  );
}
