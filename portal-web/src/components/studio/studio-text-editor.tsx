"use client";

import { useState, type DragEvent, type RefObject } from "react";

import { importTextFromFile } from "../../lib/studio/text-file-import";
import { SAMPLE_TEXTS } from "../../lib/studio/studio-sample-texts";
import { useI18n } from "../../lib/i18n/i18n-provider";

export interface StudioTextEditorProps {
  value: string;
  onChange: (next: string) => void;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
}

export function StudioTextEditor({ value, onChange, textareaRef }: StudioTextEditorProps) {
  const { messages } = useI18n();
  const t = messages.studio;
  const [dragOver, setDragOver] = useState(false);

  function insertSample() {
    const sample = SAMPLE_TEXTS[Math.floor(Math.random() * SAMPLE_TEXTS.length)];
    if (sample) onChange(sample);
  }

  async function handleDrop(event: DragEvent<HTMLTextAreaElement>) {
    event.preventDefault();
    setDragOver(false);
    const file = event.dataTransfer.files[0];
    if (!file) return;
    try {
      const text = await importTextFromFile(file);
      onChange(text);
    } catch {
      // Best-effort: a rejected drop leaves the editor unchanged.
    }
  }

  return (
    <div style={{ position: "relative" }}>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t.editorPlaceholder}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        style={{
          width: "100%",
          minHeight: 360,
          background: "#0e0e14",
          border: `1px ${dragOver ? "dashed" : "solid"} ${dragOver ? "var(--color-accent)" : "#262636"}`,
          borderRadius: 10,
          color: "#f3f4f6",
          fontSize: 15,
          lineHeight: 1.6,
          padding: "16px 16px 48px",
          resize: "vertical",
        }}
      />
      <div style={{ position: "absolute", bottom: 12, left: 16, display: "flex", alignItems: "center", gap: 10 }}>
        <button
          type="button"
          onClick={insertSample}
          style={{
            background: "rgba(124,92,252,0.1)",
            border: "1px solid var(--color-accent)",
            color: "#c4b5fd",
            borderRadius: 999,
            padding: "6px 12px",
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          {t.insertSampleButton}
        </button>
        <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{t.dragDropHint}</span>
      </div>
    </div>
  );
}
