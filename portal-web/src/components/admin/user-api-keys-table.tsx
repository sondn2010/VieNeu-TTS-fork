"use client";

import { formatRecordingTimestamp } from "../../lib/format/vietnamese-number-and-date-format";
import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import { useAdminApiKeysQuery, useRevokeApiKeyMutation } from "./admin-api-hooks";

export interface UserApiKeysTableProps {
  userId: string;
}

export function UserApiKeysTable({ userId }: UserApiKeysTableProps) {
  const { language, messages } = useI18n();
  const t = getAdminMessages(language);
  const { data, isLoading } = useAdminApiKeysQuery(userId);
  const revoke = useRevokeApiKeyMutation(userId);
  const items = data?.items ?? [];

  if (isLoading) return <p style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>{messages.common.loading}</p>;
  if (items.length === 0) return <p style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>{t.userDetail.apiKeysEmpty}</p>;

  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
      <thead>
        <tr style={{ textAlign: "left", color: "var(--color-text-secondary)", borderBottom: "1px solid var(--color-border)" }}>
          <th style={{ padding: "6px 4px" }}>{t.userDetail.apiKeysColumnName}</th>
          <th style={{ padding: "6px 4px" }}>{t.userDetail.apiKeysColumnPrefix}</th>
          <th style={{ padding: "6px 4px" }}>{t.userDetail.apiKeysColumnEnv}</th>
          <th style={{ padding: "6px 4px" }}>{t.userDetail.apiKeysColumnLastUsed}</th>
          <th style={{ padding: "6px 4px" }}>{t.userDetail.apiKeysColumnRevoked}</th>
          <th style={{ padding: "6px 4px" }} />
        </tr>
      </thead>
      <tbody>
        {items.map((key) => (
          <tr key={key.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
            <td style={{ padding: "6px 4px", color: "var(--color-text-primary)" }}>{key.name}</td>
            <td style={{ padding: "6px 4px", fontFamily: "var(--font-mono)" }}>{key.key_prefix}</td>
            <td style={{ padding: "6px 4px" }}>{key.environment}</td>
            <td style={{ padding: "6px 4px" }}>{key.last_used_at ? formatRecordingTimestamp(key.last_used_at) : "-"}</td>
            <td style={{ padding: "6px 4px" }}>{key.revoked_at ? formatRecordingTimestamp(key.revoked_at) : "-"}</td>
            <td style={{ padding: "6px 4px" }}>
              {!key.revoked_at && (
                <button type="button" onClick={() => revoke.mutate(key.id)} disabled={revoke.isPending} style={{ fontSize: 12 }}>
                  {t.userDetail.revokeButton}
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
