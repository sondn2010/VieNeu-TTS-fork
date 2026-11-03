"use client";

import { formatRecordingTimestamp, formatTokenBalance } from "../../lib/format/vietnamese-number-and-date-format";
import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import type { AdminUserRow } from "./admin-api-hooks";

export interface AdminUsersTableProps {
  rows: AdminUserRow[];
  isLoading: boolean;
  onOpen: (id: string) => void;
}

export function AdminUsersTable({ rows, isLoading, onOpen }: AdminUsersTableProps) {
  const { language, messages } = useI18n();
  const t = getAdminMessages(language);

  if (isLoading) {
    return <p style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>{messages.common.loading}</p>;
  }

  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
      <thead>
        <tr style={{ textAlign: "left", color: "var(--color-text-secondary)", borderBottom: "1px solid var(--color-border)" }}>
          <th style={{ padding: "8px 6px" }}>{t.users.columnEmail}</th>
          <th style={{ padding: "8px 6px" }}>{t.users.columnUsername}</th>
          <th style={{ padding: "8px 6px" }}>{t.users.columnRole}</th>
          <th style={{ padding: "8px 6px" }}>{t.users.columnStatus}</th>
          <th style={{ padding: "8px 6px" }}>{t.users.columnBalance}</th>
          <th style={{ padding: "8px 6px" }}>{t.users.columnExpiry}</th>
          <th style={{ padding: "8px 6px" }}>{t.users.columnLastLogin}</th>
          <th style={{ padding: "8px 6px" }}>{t.users.columnRecordings}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={row.id}
            onClick={() => onOpen(row.id)}
            style={{ cursor: "pointer", borderBottom: "1px solid var(--color-border)" }}
          >
            <td style={{ padding: "8px 6px", color: "var(--color-text-primary)" }}>{row.email}</td>
            <td style={{ padding: "8px 6px", color: "var(--color-text-secondary)" }}>{row.username}</td>
            <td style={{ padding: "8px 6px" }}>
              <span
                style={{
                  background: "rgba(124,92,252,0.15)",
                  color: "var(--color-accent)",
                  borderRadius: 4,
                  padding: "2px 6px",
                  fontSize: 11,
                }}
              >
                {row.role}
              </span>
            </td>
            <td style={{ padding: "8px 6px", color: row.is_active ? "var(--color-success-text)" : "var(--color-danger-text)" }}>
              {row.is_active ? t.users.statusActive : t.users.statusInactive}
            </td>
            <td style={{ padding: "8px 6px", fontFamily: "var(--font-mono)" }}>
              {formatTokenBalance(row.token_balance, row.token_quota_total)}
            </td>
            <td style={{ padding: "8px 6px" }}>
              {row.plan_expires_at ? formatRecordingTimestamp(row.plan_expires_at) : t.users.noExpiry}
            </td>
            <td style={{ padding: "8px 6px" }}>
              {row.last_login_at ? formatRecordingTimestamp(row.last_login_at) : t.users.neverLoggedIn}
            </td>
            <td style={{ padding: "8px 6px" }}>{row.recording_count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
