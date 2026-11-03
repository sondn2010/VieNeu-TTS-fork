"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { useAdminUserQuery } from "../../../../../components/admin/admin-api-hooks";
import { PlanEditForm } from "../../../../../components/admin/plan-edit-form";
import { TokenAdjustForm } from "../../../../../components/admin/token-adjust-form";
import { UserApiKeysTable } from "../../../../../components/admin/user-api-keys-table";
import { UserProfileAdminCard } from "../../../../../components/admin/user-profile-admin-card";
import { UserRecordingsAdminTable } from "../../../../../components/admin/user-recordings-admin-table";
import { useI18n } from "../../../../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../../../../lib/i18n/messages-admin-en";

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 10, padding: 16 }}>
      <h2 style={{ fontSize: 15, margin: "0 0 12px", color: "var(--color-text-primary)" }}>{title}</h2>
      {children}
    </div>
  );
}

function UserDetailInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const userId = searchParams.get("id");
  const { language, messages } = useI18n();
  const t = getAdminMessages(language);
  const { data, isLoading } = useAdminUserQuery(userId);

  if (!userId) {
    return <p style={{ padding: 24, color: "var(--color-danger-text)" }}>{t.guard.genericError}</p>;
  }
  if (isLoading || !data) {
    return <p style={{ padding: 24, color: "var(--color-text-secondary)" }}>{messages.common.loading}</p>;
  }

  const user = data.user;

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
      <button
        type="button"
        onClick={() => router.push("/admin/users/")}
        style={{ alignSelf: "flex-start", background: "none", border: "none", color: "var(--color-text-secondary)", cursor: "pointer" }}
      >
        {t.userDetail.backToList}
      </button>

      <UserProfileAdminCard user={user} />

      <SectionCard title={t.userDetail.quotaTitle}>
        <TokenAdjustForm userId={user.id} />
      </SectionCard>

      <SectionCard title={t.userDetail.planTitle}>
        <PlanEditForm user={user} />
      </SectionCard>

      <SectionCard title={t.userDetail.apiKeysTitle}>
        <UserApiKeysTable userId={user.id} />
      </SectionCard>

      <SectionCard title={t.userDetail.recordingsTitle}>
        <UserRecordingsAdminTable userId={user.id} />
      </SectionCard>
    </div>
  );
}

export default function UserDetailPage() {
  return (
    <Suspense fallback={null}>
      <UserDetailInner />
    </Suspense>
  );
}
