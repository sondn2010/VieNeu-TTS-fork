"use client";

import { useState } from "react";

import { useSingleActiveAudio } from "../audio/single-active-audio-player";
import { formatRecordingTimestamp } from "../../lib/format/vietnamese-number-and-date-format";
import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import {
  useAdminUserRecordingsQuery,
  useDeleteAdminRecordingMutation,
  type AdminRecordingRow,
} from "./admin-api-hooks";

function RecordingRow({ userId, row }: { userId: string; row: AdminRecordingRow }) {
  const { isPlaying, toggle } = useSingleActiveAudio(row.audio_url);
  const deleteRecording = useDeleteAdminRecordingMutation(userId);

  return (
    <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
      <td style={{ padding: "6px 4px" }}>
        <button type="button" onClick={toggle} disabled={!row.audio_url} style={{ fontSize: 12 }}>
          {isPlaying ? "⏸" : "▶"}
        </button>
      </td>
      <td style={{ padding: "6px 4px", maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {row.original_text}
      </td>
      <td style={{ padding: "6px 4px" }}>{row.status}{row.error_code ? ` (${row.error_code})` : ""}</td>
      <td style={{ padding: "6px 4px" }}>{row.duration_seconds.toFixed(1)}s</td>
      <td style={{ padding: "6px 4px" }}>{formatRecordingTimestamp(row.created_at)}</td>
      <td style={{ padding: "6px 4px" }}>
        <button type="button" onClick={() => deleteRecording.mutate(row.id)} disabled={deleteRecording.isPending} style={{ fontSize: 12 }}>
          🗑
        </button>
      </td>
    </tr>
  );
}

export interface UserRecordingsAdminTableProps {
  userId: string;
}

export function UserRecordingsAdminTable({ userId }: UserRecordingsAdminTableProps) {
  const { language, messages } = useI18n();
  const t = getAdminMessages(language);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const query = useAdminUserRecordingsQuery(userId, { search, status });
  const items = query.data?.items ?? [];

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={messages.library.searchPlaceholder}
          style={{ flex: 1, padding: 6, fontSize: 12 }}
        />
        <select value={status} onChange={(e) => setStatus(e.target.value)} style={{ fontSize: 12 }}>
          <option value="">{t.users.statusFilterAll}</option>
          <option value="SUCCESS">SUCCESS</option>
          <option value="PENDING">PENDING</option>
          <option value="FAILED">FAILED</option>
        </select>
      </div>
      {query.isLoading ? (
        <p style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>{messages.common.loading}</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <tbody>
            {items.map((row) => (
              <RecordingRow key={row.id} userId={userId} row={row} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
