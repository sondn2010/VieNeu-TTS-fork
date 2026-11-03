"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { SystemDictionaryRulesEditor } from "../../../../../components/admin/system-dictionary-rules-editor";
import { useI18n } from "../../../../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../../../../lib/i18n/messages-admin-en";

function DictionaryDetailInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const idParam = searchParams.get("id");
  const { language } = useI18n();
  const t = getAdminMessages(language);

  if (!idParam) {
    return <p style={{ padding: 24, color: "var(--color-danger-text)" }}>{t.guard.genericError}</p>;
  }

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: "0 auto" }}>
      <button
        type="button"
        onClick={() => router.push("/admin/dictionaries/")}
        style={{ marginBottom: 16, background: "none", border: "none", color: "var(--color-text-secondary)", cursor: "pointer" }}
      >
        {t.dictionaryDetail.backToList}
      </button>
      <SystemDictionaryRulesEditor dictionaryId={Number(idParam)} />
    </div>
  );
}

export default function DictionaryDetailPage() {
  return (
    <Suspense fallback={null}>
      <DictionaryDetailInner />
    </Suspense>
  );
}
