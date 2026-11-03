"use client";

/**
 * `POST /tts/generate`, with transparent polling for the `202 ASYNC` path.
 * Sync success already carries the fresh `quota` numbers, merged straight
 * into the cached profile; the async path has no such field on its
 * terminal poll response, so the profile query is invalidated instead once
 * the job finishes.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import { apiFetch } from "./api-client-with-csrf";
import { ApiError } from "./api-error";
import { USER_PROFILE_QUERY_KEY, type UserProfile } from "./use-user-profile-query";

export interface GeneratedRecording {
  id: string;
  voice_id: string;
  model_version: string;
  original_text: string;
  speed: number;
  char_count: number;
  tokens_consumed: number;
  duration_seconds: number;
  status: "PENDING" | "SUCCESS" | "FAILED";
  source_module: string;
  created_at: string;
  audio_url: string | null;
  download_url: string | null;
  error_code?: string;
  estimated_seconds?: number;
}

interface GenerateResponse {
  recording: GeneratedRecording;
  quota?: { token_balance: number; token_quota_total: number; daily_char_remaining: number };
}

const POLL_INTERVAL_MS = 2000;
const POLL_EXTRA_SEC = 60;
const DEFAULT_ESTIMATE_SEC = 30;

export interface GenerateParams {
  voice_id: string;
  text: string;
  speed: number;
}

export function useGenerateRecordingMutation() {
  const queryClient = useQueryClient();
  const [isGenerating, setIsGenerating] = useState(false);

  const generate = useCallback(
    async (params: GenerateParams): Promise<GeneratedRecording> => {
      setIsGenerating(true);
      try {
        const resp = await apiFetch<GenerateResponse>("/api/v1/tts/generate", { method: "POST", body: params });
        if (resp.quota) {
          const quota = resp.quota;
          queryClient.setQueryData<UserProfile | undefined>(USER_PROFILE_QUERY_KEY, (prev) =>
            prev ? { ...prev, ...quota } : prev,
          );
        }
        if (resp.recording.status !== "PENDING") {
          return resp.recording;
        }

        const deadlineMs =
          Date.now() + (resp.recording.estimated_seconds ?? DEFAULT_ESTIMATE_SEC) * 2 * 1000 + POLL_EXTRA_SEC * 1000;
        let latest = resp.recording;
        while (Date.now() < deadlineMs) {
          await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
          const poll = await apiFetch<{ recording: GeneratedRecording }>(`/api/v1/tts/recordings/${latest.id}`);
          latest = poll.recording;
          if (latest.status !== "PENDING") {
            await queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
            return latest;
          }
        }
        throw new ApiError(504, "POLL_TIMEOUT", "generation is taking too long; check Recent recordings later");
      } finally {
        setIsGenerating(false);
      }
    },
    [queryClient],
  );

  return { generate, isGenerating };
}
