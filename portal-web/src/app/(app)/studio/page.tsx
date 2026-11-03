"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense, useRef, useState, type ChangeEvent } from "react";

import { EmotionTagButtons } from "../../../components/studio/emotion-tag-buttons";
import { MathChemFeatureBanner } from "../../../components/studio/math-chem-feature-banner";
import { OnboardingProgressBar } from "../../../components/studio/onboarding-progress-bar";
import { RECENT_RECORDINGS_QUERY_KEY, RecentRecordingsList } from "../../../components/studio/recent-recordings-list";
import { SpeedSelector } from "../../../components/studio/speed-selector";
import { StudioActionButtons } from "../../../components/studio/studio-action-buttons";
import { StudioCounterPill } from "../../../components/studio/studio-counter-pill";
import { StudioTextEditor } from "../../../components/studio/studio-text-editor";
import { VoiceSelectorPill } from "../../../components/studio/voice-selector-pill";
import { apiFetch, getCsrfToken } from "../../../lib/api/api-client-with-csrf";
import { ApiError } from "../../../lib/api/api-error";
import { useGenerateRecordingMutation } from "../../../lib/api/use-generate-recording-mutation";
import { USER_PROFILE_QUERY_KEY, useUserProfileQuery } from "../../../lib/api/use-user-profile-query";
import { useVoicesQuery } from "../../../lib/api/use-voices-query";
import { useI18n } from "../../../lib/i18n/i18n-provider";
import type { Messages } from "../../../lib/i18n/messages-vi";
import { playPcmStream, type PcmStreamPlayerHandle } from "../../../lib/studio/pcm-stream-player";
import { importTextFromFile } from "../../../lib/studio/text-file-import";
import { countChars, estimateTokens } from "../../../lib/text/character-count-and-token-estimate";
import { insertTextAtCaret } from "../../../lib/text/insert-text-at-caret";

function mapGenerateError(err: unknown, messages: Messages): string {
  if (!(err instanceof ApiError)) return messages.studio.errorGeneric;
  switch (err.code) {
    case "CONTENT_POLICY_VIOLATION": {
      const category = typeof err.extra.category === "string" ? ` (${err.extra.category})` : "";
      return `${messages.studio.errorContentPolicy}${category}`;
    }
    case "TEXT_TOO_LONG_AFTER_PROCESSING":
    case "TEXT_TOO_LONG":
      return messages.studio.errorTextTooLong;
    case "SYNTHESIS_IN_PROGRESS":
      return messages.studio.errorSynthesisInProgress;
    case "PLAN_EXPIRED":
    case "INSUFFICIENT_TOKENS":
    case "DAILY_CHAR_LIMIT_REACHED":
      return messages.studio.errorQuota;
    case "TERMS_NOT_ACCEPTED":
      return messages.studio.errorTermsNotAccepted;
    case "ENGINE_UNAVAILABLE":
    case "MODERATION_UNAVAILABLE":
      return messages.studio.errorServiceUnavailable;
    default:
      return err.message || messages.studio.errorGeneric;
  }
}

function StudioPageInner() {
  const { messages } = useI18n();
  const t = messages.studio;
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();

  const { data: profile } = useUserProfileQuery();
  const { data: voicesData } = useVoicesQuery();
  const voices = voicesData?.data ?? [];
  const voiceNameById = Object.fromEntries(voices.map((v) => [v.id, v.name]));

  const [voiceId, setVoiceId] = useState<string | null>(searchParams.get("voice"));
  const effectiveVoiceId = voiceId ?? voices[0]?.id ?? null;

  const [speed, setSpeed] = useState(1);
  const [text, setText] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const streamHandleRef = useRef<PcmStreamPlayerHandle | null>(null);

  const { generate, isGenerating } = useGenerateRecordingMutation();

  const charCount = countChars(text);
  const tokensPerCharMilli = profile?.client_config.tokens_per_char_milli ?? 0;
  const tokens = estimateTokens(charCount, tokensPerCharMilli);
  const remaining = profile?.daily_char_remaining ?? 0;
  const overBudget = charCount > 0 && (charCount > remaining || tokens > (profile?.token_balance ?? 0));
  const actionsDisabled = charCount === 0 || overBudget || !effectiveVoiceId;

  function insertTag(tag: string) {
    const el = textareaRef.current;
    const focused = typeof document !== "undefined" && document.activeElement === el;
    const start = focused && el ? el.selectionStart ?? text.length : text.length;
    const end = focused && el ? el.selectionEnd ?? text.length : text.length;
    const result = insertTextAtCaret(text, tag, start, end);
    setText(result.text);
    requestAnimationFrame(() => {
      el?.focus();
      el?.setSelectionRange(result.caretPosition, result.caretPosition);
    });
  }

  async function handleFileSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      setText(await importTextFromFile(file));
    } catch {
      setErrorMessage(t.errorGeneric);
    }
  }

  async function hideOnboarding() {
    try {
      await apiFetch("/api/v1/user/profile", { method: "PATCH", body: { onboarding_hidden: true } });
      queryClient.setQueryData(USER_PROFILE_QUERY_KEY, (prev: unknown) =>
        prev && typeof prev === "object" ? { ...prev, onboarding_hidden: true } : prev,
      );
    } catch {
      // Best-effort: the bar simply stays visible for this session.
    }
  }

  function stopStream() {
    streamHandleRef.current?.stop();
    streamHandleRef.current = null;
    setIsStreaming(false);
  }

  async function startStream() {
    if (!effectiveVoiceId) return;
    setErrorMessage(null);
    try {
      const csrfToken = await getCsrfToken();
      const resp = await fetch("/api/v1/tts/stream", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
        body: JSON.stringify({ voice_id: effectiveVoiceId, text }),
      });
      if (!resp.ok) {
        const body = (await resp.json().catch(() => null)) as { error?: { code?: string; message?: string } } | null;
        throw new ApiError(resp.status, body?.error?.code ?? "ERROR", body?.error?.message ?? "stream failed");
      }
      const handle = await playPcmStream(resp);
      streamHandleRef.current = handle;
      setIsStreaming(true);
      void handle.finished.finally(() => {
        if (streamHandleRef.current === handle) {
          streamHandleRef.current = null;
          setIsStreaming(false);
        }
      });
    } catch (err) {
      setErrorMessage(mapGenerateError(err, messages));
    }
  }

  async function handleGenerate() {
    if (!effectiveVoiceId) return;
    setErrorMessage(null);
    try {
      await generate({ voice_id: effectiveVoiceId, text, speed });
      void queryClient.invalidateQueries({ queryKey: RECENT_RECORDINGS_QUERY_KEY });
    } catch (err) {
      setErrorMessage(mapGenerateError(err, messages));
      if (err instanceof ApiError && err.code === "TERMS_NOT_ACCEPTED") {
        void queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
      }
    }
  }

  if (!profile) {
    return (
      <div style={{ padding: 24 }}>
        <p style={{ color: "var(--color-text-secondary)" }}>{messages.common.loading}</p>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 980, margin: "0 auto" }}>
      {!profile.onboarding_hidden && (
        <OnboardingProgressBar completedSteps={profile.onboarding_completed_steps} onHide={hideOnboarding} />
      )}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          flexWrap: "wrap",
          background: "#13131c",
          border: "1px solid #262636",
          borderRadius: 10,
          padding: "8px 14px",
          marginBottom: 12,
        }}
      >
        <VoiceSelectorPill voiceId={effectiveVoiceId} onChange={(v) => setVoiceId(v.id)} />
        <SpeedSelector value={speed} onChange={setSpeed} />
        <EmotionTagButtons onInsert={insertTag} />
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
          <button
            type="button"
            disabled
            title={messages.common.comingSoon}
            style={{
              color: "var(--color-text-muted)",
              background: "none",
              border: "1px solid var(--color-border)",
              borderRadius: 6,
              padding: "4px 10px",
              cursor: "not-allowed",
              fontSize: 13,
            }}
          >
            ♪ {t.bgMusicLabel}
          </button>
          <label style={{ cursor: "pointer", color: "var(--color-text-secondary)", fontSize: 13 }}>
            {t.uploadFileButton}
            <input type="file" accept=".txt,.docx,.srt" onChange={handleFileSelected} style={{ display: "none" }} />
          </label>
          <span aria-disabled style={{ color: "var(--color-text-muted)", fontSize: 13, cursor: "not-allowed" }}>
            {t.dictionaryLink}
          </span>
          <button
            type="button"
            title={t.helpTooltip}
            aria-label={t.helpTooltip}
            style={{ background: "none", border: "none", color: "var(--color-text-secondary)", cursor: "pointer" }}
          >
            ?
          </button>
        </div>
      </div>

      <MathChemFeatureBanner />

      <StudioTextEditor value={text} onChange={setText} textareaRef={textareaRef} />

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 12 }}>
        <StudioCounterPill charCount={charCount} tokens={tokens} remainingChars={remaining} overBudget={overBudget} />
        <StudioActionButtons
          onPlayNow={startStream}
          onStopStream={stopStream}
          onGenerate={handleGenerate}
          isStreaming={isStreaming}
          isGenerating={isGenerating}
          disabled={actionsDisabled}
        />
      </div>

      {errorMessage && <p style={{ color: "var(--color-danger-text)", fontSize: 13, marginTop: 8 }}>{errorMessage}</p>}

      <RecentRecordingsList voiceNameById={voiceNameById} />
    </div>
  );
}

export default function StudioPage() {
  return (
    <Suspense fallback={null}>
      <StudioPageInner />
    </Suspense>
  );
}
