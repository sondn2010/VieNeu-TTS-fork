"use client";

import { useState } from "react";

import { useAdminVoicesQuery, type AdminVoiceRow } from "../../../../components/admin/admin-api-hooks";
import { VoiceEditDrawer } from "../../../../components/admin/voice-edit-drawer";
import { useI18n } from "../../../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../../../lib/i18n/messages-admin-en";

export default function AdminVoicesPage() {
  const { language, messages } = useI18n();
  const t = getAdminMessages(language);
  const query = useAdminVoicesQuery();
  const [editing, setEditing] = useState<AdminVoiceRow | null>(null);

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <header style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--color-text-primary)", margin: 0 }}>{t.voices.title}</h1>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "4px 0 0" }}>{t.voices.subtitle}</p>
      </header>

      {query.isLoading ? (
        <p style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>{messages.common.loading}</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "var(--color-text-secondary)", borderBottom: "1px solid var(--color-border)" }}>
              <th style={{ padding: "8px 6px" }}>{t.voices.columnName}</th>
              <th style={{ padding: "8px 6px" }}>{t.voices.columnGender}</th>
              <th style={{ padding: "8px 6px" }}>{t.voices.columnRegion}</th>
              <th style={{ padding: "8px 6px" }}>{t.voices.columnActive}</th>
              <th style={{ padding: "8px 6px" }} />
            </tr>
          </thead>
          <tbody>
            {(query.data?.items ?? []).map((voice) => (
              <tr key={voice.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
                <td style={{ padding: "8px 6px", color: "var(--color-text-primary)" }}>{voice.name}</td>
                <td style={{ padding: "8px 6px" }}>{voice.gender}</td>
                <td style={{ padding: "8px 6px" }}>{voice.region}</td>
                <td style={{ padding: "8px 6px", color: voice.is_active ? "var(--color-success-text)" : "var(--color-danger-text)" }}>
                  {voice.is_active ? "✓" : "—"}
                </td>
                <td style={{ padding: "8px 6px" }}>
                  <button type="button" onClick={() => setEditing(voice)} style={{ fontSize: 12 }}>
                    {t.voices.editButton}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {editing && <VoiceEditDrawer voice={editing} onClose={() => setEditing(null)} />}
    </div>
  );
}
