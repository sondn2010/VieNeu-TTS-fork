"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAdminDictionariesQuery, type AdminDictionaryPack } from "../../../../components/admin/admin-api-hooks";
import { CreateDictionaryDialog } from "../../../../components/admin/create-dictionary-dialog";
import { SystemDictionaryImportExportControls } from "../../../../components/admin/system-dictionary-import-export-controls";
import { SystemDictionaryPackList } from "../../../../components/admin/system-dictionary-pack-list";
import { useI18n } from "../../../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../../../lib/i18n/messages-admin-en";

export default function AdminDictionariesPage() {
  const router = useRouter();
  const { language } = useI18n();
  const t = getAdminMessages(language);
  const query = useAdminDictionariesQuery();
  const [createOpen, setCreateOpen] = useState(false);
  const [importingPack, setImportingPack] = useState<AdminDictionaryPack | null>(null);

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: "0 auto" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--color-text-primary)", margin: 0 }}>{t.dictionaries.title}</h1>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "4px 0 0" }}>{t.dictionaries.subtitle}</p>
        </div>
        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          style={{ background: "var(--color-accent)", color: "#fff", fontWeight: 700, border: "none", borderRadius: 8, padding: "8px 16px", cursor: "pointer" }}
        >
          {t.dictionaries.createButton}
        </button>
      </header>

      <SystemDictionaryPackList
        packs={query.data?.items ?? []}
        isLoading={query.isLoading}
        onOpen={(id) => router.push(`/admin/dictionaries/detail/?id=${id}`)}
        onImport={setImportingPack}
      />

      {createOpen && <CreateDictionaryDialog onClose={() => setCreateOpen(false)} />}
      {importingPack && <SystemDictionaryImportExportControls pack={importingPack} onClose={() => setImportingPack(null)} />}
    </div>
  );
}
