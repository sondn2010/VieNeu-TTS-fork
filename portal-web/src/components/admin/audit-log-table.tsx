"use client";

import { useState } from "react";

import { formatRecordingTimestamp } from "../../lib/format/vietnamese-number-and-date-format";
import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import type { AdminAuditLogRow } from "./admin-api-hooks";

function JsonDetails({ label, value }: { label: string; value: Record<string, unknown> | null }) {
  if (!value) return null;
  return (
    <div>
      <strong style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>{label}</strong>
      {/* Rendered as plain text via JSON.stringify, never injected as HTML. */}
      <pre style={{ fontSize: 11, margin: "2px 0 0", whiteSpace: "pre-wrap", color: "var(--color-text-secondary)" }}>
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

function AuditRow({ row }: { row: AdminAuditLogRow }) {
  const { language } = useI18n();
  const t = getAdminMessages(language);
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr style={{ borderBottom: expanded ? "none" : "1px solid var(--color-border)" }}>
        <td style={{ padding: "6px 4px" }}>{formatRecordingTimestamp(row.created_at)}</td>
        <td style={{ padding: "6px 4px" }}>{row.actor_label}</td>
        <td style={{ padding: "6px 4px", fontFamily: "var(--font-mono)" }}>{row.action}</td>
        <td style={{ padding: "6px 4px" }}>
          {row.target_type}:{row.target_label ?? row.target_id}
        </td>
        <td style={{ padding: "6px 4px" }}>
          <button type="button" onClick={() => setExpanded((e) => !e)} style={{ fontSize: 11 }}>
            {t.auditLog.expandDetails}
          </button>
        </td>
      </tr>
      {expanded && (
        <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
          <td colSpan={5} style={{ padding: "6px 4px 12px", background: "var(--color-bg-secondary)" }}>
            <div style={{ display: "flex", gap: 20 }}>
              <JsonDetails label={t.auditLog.beforeLabel} value={row.before} />
              <JsonDetails label={t.auditLog.afterLabel} value={row.after} />
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export interface AuditLogTableProps {
  rows: AdminAuditLogRow[];
  isLoading: boolean;
}

export function AuditLogTable({ rows, isLoading }: AuditLogTableProps) {
  const { language, messages } = useI18n();
  const t = getAdminMessages(language);

  if (isLoading) {
    return <p style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>{messages.common.loading}</p>;
  }

  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
      <thead>
        <tr style={{ textAlign: "left", color: "var(--color-text-secondary)", borderBottom: "1px solid var(--color-border)" }}>
          <th style={{ padding: "8px 6px" }}>{t.auditLog.columnTime}</th>
          <th style={{ padding: "8px 6px" }}>{t.auditLog.columnActor}</th>
          <th style={{ padding: "8px 6px" }}>{t.auditLog.columnAction}</th>
          <th style={{ padding: "8px 6px" }}>{t.auditLog.columnTarget}</th>
          <th style={{ padding: "8px 6px" }} />
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <AuditRow key={row.id} row={row} />
        ))}
      </tbody>
    </table>
  );
}
