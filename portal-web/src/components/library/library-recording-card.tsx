"use client";

import { Download, Trash2 } from "lucide-react";
import { useState } from "react";

import { useSingleActiveAudio } from "../audio/single-active-audio-player";
import type { GeneratedRecording } from "../../lib/api/use-generate-recording-mutation";
import { formatRecordingTimestamp } from "../../lib/format/vietnamese-number-and-date-format";
import { useI18n } from "../../lib/i18n/i18n-provider";
import { DeleteRecordingConfirmDialog } from "./delete-recording-confirm-dialog";

export interface LibraryRecordingCardProps {
  recording: GeneratedRecording;
  voiceName: string;
  onDelete: (id: string) => void;
}

export function LibraryRecordingCard({ recording, voiceName, onDelete }: LibraryRecordingCardProps) {
  const { messages } = useI18n();
  const { isPlaying, toggle } = useSingleActiveAudio(recording.audio_url);
  const [confirming, setConfirming] = useState(false);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: 10,
        padding: "16px 20px",
        marginBottom: 12,
      }}
    >
      <button
        type="button"
        onClick={toggle}
        disabled={!recording.audio_url}
        style={{
          width: 42,
          height: 42,
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
            fontSize: 14,
            fontWeight: 600,
            color: "var(--color-text-primary)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {recording.original_text}
        </div>
        <div style={{ fontSize: 12, color: "var(--color-text-secondary)", display: "flex", gap: 16, marginTop: 4 }}>
          <span>👤 {voiceName}</span>
          <span>🕒 {recording.duration_seconds.toFixed(1)}s</span>
          <span>📅 {formatRecordingTimestamp(recording.created_at)}</span>
        </div>
      </div>
      <a
        href={recording.download_url ?? undefined}
        aria-disabled={!recording.download_url}
        aria-label={messages.studio.downloadButton}
        style={{
          color: "var(--color-text-secondary)",
          pointerEvents: recording.download_url ? "auto" : "none",
          opacity: recording.download_url ? 1 : 0.4,
        }}
      >
        <Download size={18} aria-hidden />
      </a>
      <button
        type="button"
        onClick={() => setConfirming(true)}
        aria-label={messages.library.deleteButtonLabel}
        style={{ background: "none", border: "none", color: "var(--color-danger-text)", cursor: "pointer" }}
      >
        <Trash2 size={18} aria-hidden />
      </button>
      {confirming && (
        <DeleteRecordingConfirmDialog
          onConfirm={() => {
            setConfirming(false);
            onDelete(recording.id);
          }}
          onCancel={() => setConfirming(false)}
        />
      )}
    </div>
  );
}
