"use client";

import { useState } from "react";

import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import { useUpdateVoiceMutation, type AdminVoiceRow } from "./admin-api-hooks";
import { VoiceMediaUploadControls } from "./voice-media-upload-controls";

const GENDERS = ["NAM", "NU"] as const;
const REGIONS = ["MIEN_BAC", "MIEN_TRUNG", "MIEN_NAM"] as const;

export interface VoiceEditDrawerProps {
  voice: AdminVoiceRow;
  onClose: () => void;
}

export function VoiceEditDrawer({ voice, onClose }: VoiceEditDrawerProps) {
  const { language } = useI18n();
  const t = getAdminMessages(language);
  const [name, setName] = useState(voice.name);
  const [gender, setGender] = useState(voice.gender);
  const [region, setRegion] = useState(voice.region);
  const [tags, setTags] = useState(voice.tags.join(", "));
  const [languageLabel, setLanguageLabel] = useState(voice.language_label);
  const [sortOrder, setSortOrder] = useState(String(voice.sort_order));
  const [isActive, setIsActive] = useState(voice.is_active);
  const [error, setError] = useState<string | null>(null);
  const update = useUpdateVoiceMutation(voice.id);

  async function handleSave() {
    setError(null);
    try {
      await update.mutateAsync({
        name,
        gender,
        region,
        tags: tags.split(",").map((s) => s.trim()).filter(Boolean),
        language_label: languageLabel,
        sort_order: Number(sortOrder) || 0,
        is_active: isActive,
      });
    } catch {
      setError(t.guard.genericError);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t.voiceEditDrawer.title}
      style={{ position: "fixed", inset: 0, background: "rgba(5,5,10,0.6)", display: "flex", justifyContent: "flex-end", zIndex: 50 }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          width: 380,
          height: "100%",
          background: "var(--color-surface)",
          borderLeft: "1px solid var(--color-border)",
          padding: 20,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <h2 style={{ fontSize: 16, margin: 0, color: "var(--color-text-primary)" }}>{t.voiceEditDrawer.title}</h2>
        <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
          {t.voiceEditDrawer.nameLabel}
          <input value={name} onChange={(e) => setName(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
        </label>
        <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
          {t.voiceEditDrawer.genderLabel}
          <select value={gender} onChange={(e) => setGender(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }}>
            {GENDERS.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </label>
        <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
          {t.voiceEditDrawer.regionLabel}
          <select value={region} onChange={(e) => setRegion(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }}>
            {REGIONS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
        <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
          {t.voiceEditDrawer.tagsLabel} <span style={{ fontSize: 10 }}>({t.voiceEditDrawer.tagsHint})</span>
          <input value={tags} onChange={(e) => setTags(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
        </label>
        <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
          {t.voiceEditDrawer.languageLabelLabel}
          <input value={languageLabel} onChange={(e) => setLanguageLabel(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
        </label>
        <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
          {t.voiceEditDrawer.sortOrderLabel}
          <input type="number" value={sortOrder} onChange={(e) => setSortOrder(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
        </label>
        <label style={{ fontSize: 12, color: "var(--color-text-secondary)", display: "flex", alignItems: "center", gap: 6 }}>
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          {t.voiceEditDrawer.activeLabel}
        </label>
        {error && <p style={{ color: "var(--color-danger-text)", fontSize: 12, margin: 0 }}>{error}</p>}
        <div style={{ display: "flex", gap: 8 }}>
          <button type="button" onClick={onClose}>
            {t.voiceEditDrawer.closeButton}
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={update.isPending}
            style={{ background: "var(--color-accent)", color: "#fff", border: "none", borderRadius: 6, padding: "6px 12px" }}
          >
            {t.voiceEditDrawer.saveButton}
          </button>
        </div>

        <hr style={{ borderColor: "var(--color-border)", width: "100%" }} />
        <VoiceMediaUploadControls voice={voice} />
      </div>
    </div>
  );
}
