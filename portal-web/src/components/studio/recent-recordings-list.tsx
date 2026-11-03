"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, History, Music, RefreshCw } from "lucide-react";

import { useSingleActiveAudio } from "../audio/single-active-audio-player";
import { apiFetch } from "../../lib/api/api-client-with-csrf";
import type { GeneratedRecording } from "../../lib/api/use-generate-recording-mutation";
import type { RecordingsLibraryPage } from "../../lib/api/use-recordings-library-query";
import { formatRecordingTimestamp } from "../../lib/format/vietnamese-number-and-date-format";
import { useI18n } from "../../lib/i18n/i18n-provider";

export const RECENT_RECORDINGS_QUERY_KEY = ["recordings-library", "recent"] as const;
const RECENT_RECORDINGS_LIMIT = 5;

interface RecordingCardProps {
  recording: GeneratedRecording;
  voiceName: string;
  onDeleted: () => void;
}

function RecordingCard({ recording, voiceName, onDeleted }: RecordingCardProps) {
  const { messages } = useI18n();
  const { isPlaying, toggle } = useSingleActiveAudio(recording.audio_url);
  const isFailed = recording.status === "FAILED";

  async function deleteFailed() {
    try {
      await apiFetch(`/api/v1/tts/recordings/${recording.id}`, { method: "DELETE" });
      onDeleted();
    } catch {
      // Best-effort: leave the row for the next manual refresh/retry.
    }
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: 10,
        padding: "10px 14px",
        marginBottom: 8,
      }}
    >
      <button
        type="button"
        onClick={toggle}
        disabled={!recording.audio_url}
        style={{
          width: 36,
          height: 36,
          borderRadius: "50%",
          background: "#1e1e2a",
          border: "none",
          color: "#fff",
          flexShrink: 0,
          cursor: recording.audio_url ? "pointer" : "not-allowed",
        }}
      >
        {isPlaying ? "⏸" : "▶"}
      </button>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 13,
            color: isFailed ? "var(--color-danger-text)" : "var(--color-text-primary)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {isFailed ? messages.studio.retryHint : recording.original_text}
        </div>
        <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
          {voiceName}{" "}
          <span
            style={{
              background: "rgba(124,92,252,0.15)",
              color: "var(--color-accent)",
              borderRadius: 4,
              padding: "0 4px",
              fontSize: 11,
            }}
          >
            {recording.model_version}
          </span>{" "}
          · {recording.duration_seconds.toFixed(1)}s · {formatRecordingTimestamp(recording.created_at)}
        </div>
      </div>
      {isFailed ? (
        <button
          type="button"
          onClick={deleteFailed}
          style={{ background: "none", border: "none", color: "var(--color-text-secondary)", cursor: "pointer", fontSize: 12 }}
        >
          {messages.studio.deleteButton}
        </button>
      ) : (
        <>
          <a
            href={recording.download_url ?? undefined}
            aria-disabled={!recording.download_url}
            aria-label={messages.studio.downloadButton}
            style={{
              color: recording.download_url ? "var(--color-text-secondary)" : "var(--color-text-muted)",
              pointerEvents: recording.download_url ? "auto" : "none",
            }}
          >
            <Download size={16} aria-hidden />
          </a>
          <button
            type="button"
            disabled
            title={messages.common.comingSoon}
            style={{
              background: "var(--color-accent)",
              opacity: 0.4,
              border: "none",
              borderRadius: 6,
              width: 28,
              height: 28,
              color: "#fff",
              cursor: "not-allowed",
            }}
          >
            <Music size={14} aria-hidden />
          </button>
        </>
      )}
    </div>
  );
}

export interface RecentRecordingsListProps {
  voiceNameById: Record<string, string>;
}

export function RecentRecordingsList({ voiceNameById }: RecentRecordingsListProps) {
  const { messages } = useI18n();
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: RECENT_RECORDINGS_QUERY_KEY,
    queryFn: () => apiFetch<RecordingsLibraryPage>(`/api/v1/tts/recordings?limit=${RECENT_RECORDINGS_LIMIT}`),
  });
  const items = data?.items ?? [];

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: RECENT_RECORDINGS_QUERY_KEY });
  }

  return (
    <section style={{ marginTop: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 12,
            fontWeight: 700,
            color: "#9ca3af",
            textTransform: "uppercase",
          }}
        >
          <History size={14} aria-hidden />
          {messages.studio.recentRecordingsTitle}
          <span style={{ background: "#1e1e2a", borderRadius: 999, padding: "1px 8px" }}>{items.length}</span>
        </div>
        <button
          type="button"
          onClick={refresh}
          aria-label={messages.studio.refreshButton}
          style={{ background: "none", border: "none", color: "var(--color-text-secondary)", cursor: "pointer" }}
        >
          <RefreshCw size={14} aria-hidden />
        </button>
      </div>
      {isLoading ? (
        <p style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>{messages.common.loading}</p>
      ) : (
        items.map((item) => (
          <RecordingCard key={item.id} recording={item} voiceName={voiceNameById[item.voice_id] ?? ""} onDeleted={refresh} />
        ))
      )}
    </section>
  );
}
