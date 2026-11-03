"use client";

import { Volume2, Zap } from "lucide-react";

import { useI18n } from "../../lib/i18n/i18n-provider";

export interface StudioActionButtonsProps {
  onPlayNow: () => void;
  onStopStream: () => void;
  onGenerate: () => void;
  isStreaming: boolean;
  isGenerating: boolean;
  /** Empty text, over-budget, or no voice selected yet. */
  disabled: boolean;
}

export function StudioActionButtons({
  onPlayNow,
  onStopStream,
  onGenerate,
  isStreaming,
  isGenerating,
  disabled,
}: StudioActionButtonsProps) {
  const { messages } = useI18n();
  const t = messages.studio;

  // Both buttons stay disabled while a stream, a sync generate, or a
  // polled async job is in flight, except the Play button also doubles as
  // Stop once a stream is already running.
  const playDisabled = isStreaming ? false : disabled || isGenerating;
  const generateDisabled = disabled || isGenerating || isStreaming;

  return (
    <div style={{ display: "flex", gap: 10 }}>
      <button
        type="button"
        onClick={isStreaming ? onStopStream : onPlayNow}
        disabled={playDisabled}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          background: "#1a1a26",
          border: "1px solid #2e2e42",
          borderRadius: 8,
          padding: "8px 14px",
          color: "var(--color-text-primary)",
          cursor: playDisabled ? "not-allowed" : "pointer",
          opacity: playDisabled ? 0.5 : 1,
        }}
      >
        <Zap size={16} aria-hidden />
        {isStreaming ? t.stopButton : t.playNowButton}
      </button>
      <button
        type="button"
        onClick={onGenerate}
        disabled={generateDisabled}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          background: "var(--color-accent)",
          border: "none",
          borderRadius: 8,
          padding: "8px 16px",
          color: "#fff",
          fontWeight: 700,
          cursor: generateDisabled ? "not-allowed" : "pointer",
          opacity: generateDisabled ? 0.5 : 1,
        }}
      >
        <Volume2 size={16} aria-hidden />
        {t.generateButton}
      </button>
    </div>
  );
}
