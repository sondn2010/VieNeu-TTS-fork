"use client";

import { ChevronsUpDown, Pause, Play } from "lucide-react";
import { useState } from "react";

import { useSingleActiveAudio } from "../audio/single-active-audio-player";
import { useVoicesQuery, type Voice } from "../../lib/api/use-voices-query";
import { useI18n } from "../../lib/i18n/i18n-provider";

export interface VoiceSelectorPillProps {
  voiceId: string | null;
  onChange: (voice: Voice) => void;
}

function VoiceSampleButton({ voice }: { voice: Voice }) {
  const { isPlaying, toggle } = useSingleActiveAudio(voice.sample_audio_url);
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        toggle();
      }}
      disabled={!voice.sample_audio_url}
      aria-label={voice.name}
      style={{ background: "none", border: "none", cursor: "pointer", color: "var(--color-text-secondary)" }}
    >
      {isPlaying ? <Pause size={14} aria-hidden /> : <Play size={14} aria-hidden />}
    </button>
  );
}

export function VoiceSelectorPill({ voiceId, onChange }: VoiceSelectorPillProps) {
  const { messages } = useI18n();
  const { data } = useVoicesQuery();
  const [open, setOpen] = useState(false);
  const voices = data?.data ?? [];
  const selected = voices.find((v) => v.id === voiceId) ?? voices[0];

  return (
    <div style={{ position: "relative" }}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        style={{ display: "flex", alignItems: "center", gap: 8, background: "none", border: "none", cursor: "pointer", padding: "4px 8px" }}
      >
        <span
          aria-hidden
          style={{
            width: 28,
            height: 28,
            borderRadius: "50%",
            background: "var(--color-accent)",
            color: "#fff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 11,
            fontWeight: 700,
            flexShrink: 0,
          }}
        >
          {selected?.initials ?? "?"}
        </span>
        <span style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
          <span style={{ fontSize: 10, color: "var(--color-text-secondary)", textTransform: "uppercase" }}>
            {messages.studio.voiceSelectorLabel}
          </span>
          <span style={{ fontSize: 14, fontWeight: 700, color: "var(--color-text-primary)" }}>
            {selected?.name ?? messages.common.loading}
          </span>
        </span>
        <ChevronsUpDown size={14} aria-hidden color="var(--color-text-secondary)" />
      </button>
      {open && (
        <div
          role="listbox"
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            zIndex: 20,
            minWidth: 260,
            maxHeight: 320,
            overflowY: "auto",
            background: "#181822",
            border: "1px solid #262636",
            borderRadius: 10,
            padding: 6,
            marginTop: 4,
          }}
        >
          {voices.map((voice) => (
            <div
              key={voice.id}
              role="option"
              aria-selected={voice.id === selected?.id}
              onClick={() => {
                onChange(voice);
                setOpen(false);
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 8px",
                borderRadius: 6,
                cursor: "pointer",
                background: voice.id === selected?.id ? "rgba(124,92,252,0.15)" : "transparent",
              }}
            >
              <span style={{ flex: 1, fontSize: 13, color: "var(--color-text-primary)" }}>{voice.name}</span>
              <VoiceSampleButton voice={voice} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
