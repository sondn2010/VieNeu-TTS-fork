"use client";

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "./api-client-with-csrf";

export interface Voice {
  id: string;
  name: string;
  initials: string;
  avatar_url: string | null;
  gender: string;
  region: string;
  language_code: string;
  language_label: string;
  model_version: string;
  tags: string[];
  supported_styles: string[];
  sample_audio_url: string | null;
  is_active: boolean;
}

export const VOICES_QUERY_KEY = ["voices"] as const;

export function useVoicesQuery() {
  return useQuery({
    queryKey: VOICES_QUERY_KEY,
    queryFn: () => apiFetch<{ data: Voice[] }>("/api/v1/voices"),
    staleTime: 5 * 60 * 1000,
  });
}
