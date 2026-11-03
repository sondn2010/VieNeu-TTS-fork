"use client";

import { useI18n } from "../../lib/i18n/i18n-provider";
import type { Messages } from "../../lib/i18n/messages-vi";

export interface EmotionTagButtonsProps {
  onInsert: (tag: string) => void;
}

const TAGS: readonly { tag: string; labelKey: keyof Messages["studio"] }[] = [
  { tag: "[cười] ", labelKey: "emotionCry" },
  { tag: "[thở dài] ", labelKey: "emotionSigh" },
  { tag: "[hắng giọng] ", labelKey: "emotionClearThroat" },
];

export function EmotionTagButtons({ onInsert }: EmotionTagButtonsProps) {
  const { messages } = useI18n();
  const t = messages.studio;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>{t.emotionLabel}</span>
      {TAGS.map(({ tag, labelKey }) => (
        <button
          key={tag}
          type="button"
          onClick={() => onInsert(tag)}
          style={{
            background: "#1e1e2a",
            border: "1px solid #2e2e42",
            borderRadius: 999,
            padding: "4px 10px",
            fontSize: 12,
            color: "var(--color-text-primary)",
            cursor: "pointer",
          }}
        >
          {t[labelKey]}
        </button>
      ))}
    </div>
  );
}
