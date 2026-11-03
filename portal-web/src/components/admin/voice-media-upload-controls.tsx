"use client";

import { useRef, useState, type ChangeEvent } from "react";

import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import {
  useDeleteVoiceAvatarMutation,
  useRenderVoiceSampleMutation,
  useUploadVoiceAvatarMutation,
  useUploadVoiceSampleMutation,
  type AdminVoiceRow,
} from "./admin-api-hooks";

export interface VoiceMediaUploadControlsProps {
  voice: AdminVoiceRow;
}

export function VoiceMediaUploadControls({ voice }: VoiceMediaUploadControlsProps) {
  const { language } = useI18n();
  const t = getAdminMessages(language);
  const avatarInputRef = useRef<HTMLInputElement | null>(null);
  const sampleInputRef = useRef<HTMLInputElement | null>(null);
  const [renderText, setRenderText] = useState("");
  const [error, setError] = useState<string | null>(null);

  const uploadAvatar = useUploadVoiceAvatarMutation(voice.id);
  const deleteAvatar = useDeleteVoiceAvatarMutation(voice.id);
  const uploadSample = useUploadVoiceSampleMutation(voice.id);
  const renderSample = useRenderVoiceSampleMutation(voice.id);

  async function handleAvatarChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError(null);
    try {
      await uploadAvatar.mutateAsync(file);
    } catch {
      setError(t.guard.genericError);
    }
  }

  async function handleSampleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError(null);
    try {
      await uploadSample.mutateAsync(file);
    } catch {
      setError(t.guard.genericError);
    }
  }

  async function handleRender() {
    setError(null);
    try {
      await renderSample.mutateAsync(renderText || undefined);
    } catch {
      setError(t.guard.genericError);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <h4 style={{ fontSize: 13, color: "var(--color-text-primary)", margin: "0 0 6px" }}>{t.voiceEditDrawer.avatarTitle}</h4>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {voice.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element -- presigned, short-lived URL; next/image's remote-pattern config doesn't apply.
            <img src={voice.avatar_url} alt={voice.name} style={{ width: 40, height: 40, borderRadius: "50%" }} />
          ) : (
            <span
              aria-hidden
              style={{
                width: 40,
                height: 40,
                borderRadius: "50%",
                background: "var(--color-accent)",
                color: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 13,
              }}
            >
              {voice.initials}
            </span>
          )}
          <input ref={avatarInputRef} type="file" accept="image/png,image/jpeg,image/webp" onChange={handleAvatarChange} style={{ display: "none" }} />
          <button type="button" onClick={() => avatarInputRef.current?.click()} disabled={uploadAvatar.isPending}>
            {t.voiceEditDrawer.uploadAvatarButton}
          </button>
          {voice.avatar_url && (
            <button type="button" onClick={() => deleteAvatar.mutate()} disabled={deleteAvatar.isPending}>
              {t.voiceEditDrawer.removeAvatarButton}
            </button>
          )}
        </div>
      </div>

      <div>
        <h4 style={{ fontSize: 13, color: "var(--color-text-primary)", margin: "0 0 6px" }}>{t.voiceEditDrawer.sampleTitle}</h4>
        {voice.sample_audio_url && <audio controls src={voice.sample_audio_url} style={{ width: "100%", marginBottom: 8 }} />}
        <input ref={sampleInputRef} type="file" accept="audio/mpeg,audio/wav" onChange={handleSampleChange} style={{ display: "none" }} />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button type="button" onClick={() => sampleInputRef.current?.click()} disabled={uploadSample.isPending}>
            {t.voiceEditDrawer.uploadSampleButton}
          </button>
        </div>
        <div style={{ marginTop: 8 }}>
          <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
            {t.voiceEditDrawer.renderTextLabel}
            <input
              type="text"
              value={renderText}
              onChange={(e) => setRenderText(e.target.value)}
              placeholder={t.voiceEditDrawer.renderTextPlaceholder}
              style={{ width: "100%", padding: 8, marginTop: 4 }}
            />
          </label>
          <button type="button" onClick={handleRender} disabled={renderSample.isPending} style={{ marginTop: 6 }}>
            {t.voiceEditDrawer.renderSampleButton}
          </button>
        </div>
      </div>
      {error && <p style={{ color: "var(--color-danger-text)", fontSize: 12, margin: 0 }}>{error}</p>}
    </div>
  );
}
