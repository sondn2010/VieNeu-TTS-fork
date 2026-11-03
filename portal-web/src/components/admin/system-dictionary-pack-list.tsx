"use client";

import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import { useDeleteDictionaryMutation, useUpdateDictionaryMutation, type AdminDictionaryPack } from "./admin-api-hooks";

function PackRow({
  pack,
  onOpen,
  onImport,
}: {
  pack: AdminDictionaryPack;
  onOpen: (id: number) => void;
  onImport: (pack: AdminDictionaryPack) => void;
}) {
  const { language } = useI18n();
  const t = getAdminMessages(language);
  const update = useUpdateDictionaryMutation(pack.id);
  const deletePack = useDeleteDictionaryMutation();

  return (
    <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
      <td style={{ padding: "8px 6px", cursor: "pointer", color: "var(--color-text-primary)" }} onClick={() => onOpen(pack.id)}>
        {pack.name}
      </td>
      <td style={{ padding: "8px 6px" }}>{pack.kind}</td>
      <td style={{ padding: "8px 6px" }}>
        <input
          type="checkbox"
          checked={pack.is_enabled}
          disabled={update.isPending}
          onChange={(e) => update.mutate({ is_enabled: e.target.checked })}
        />
      </td>
      <td style={{ padding: "8px 6px", display: "flex", gap: 6, flexWrap: "wrap" }}>
        <button type="button" onClick={() => onOpen(pack.id)} style={{ fontSize: 12 }}>
          {t.dictionaries.openButton}
        </button>
        <button type="button" onClick={() => onImport(pack)} style={{ fontSize: 12 }}>
          {t.dictionaries.importButton}
        </button>
        <a href={`/api/v1/admin/system-dictionaries/${pack.id}/export?format=json`} download={`${pack.name}.json`} style={{ fontSize: 12 }}>
          {t.dictionaries.exportJsonButton}
        </a>
        <a href={`/api/v1/admin/system-dictionaries/${pack.id}/export?format=txt`} download={`${pack.name}.txt`} style={{ fontSize: 12 }}>
          {t.dictionaries.exportTxtButton}
        </a>
        <button
          type="button"
          onClick={() => deletePack.mutate(pack.id)}
          disabled={deletePack.isPending}
          style={{ fontSize: 12, color: "var(--color-danger-text)" }}
        >
          {t.dictionaries.deleteButton}
        </button>
      </td>
    </tr>
  );
}

export interface SystemDictionaryPackListProps {
  packs: AdminDictionaryPack[];
  isLoading: boolean;
  onOpen: (id: number) => void;
  onImport: (pack: AdminDictionaryPack) => void;
}

export function SystemDictionaryPackList({ packs, isLoading, onOpen, onImport }: SystemDictionaryPackListProps) {
  const { language, messages } = useI18n();
  const t = getAdminMessages(language);

  if (isLoading) {
    return <p style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>{messages.common.loading}</p>;
  }

  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
      <thead>
        <tr style={{ textAlign: "left", color: "var(--color-text-secondary)", borderBottom: "1px solid var(--color-border)" }}>
          <th style={{ padding: "8px 6px" }}>{t.dictionaries.columnName}</th>
          <th style={{ padding: "8px 6px" }}>{t.dictionaries.columnKind}</th>
          <th style={{ padding: "8px 6px" }}>{t.dictionaries.columnEnabled}</th>
          <th style={{ padding: "8px 6px" }} />
        </tr>
      </thead>
      <tbody>
        {packs.map((pack) => (
          <PackRow key={pack.id} pack={pack} onOpen={onOpen} onImport={onImport} />
        ))}
      </tbody>
    </table>
  );
}
