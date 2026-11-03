"use client";

import { useInfiniteQuery } from "@tanstack/react-query";

import { apiFetch } from "./api-client-with-csrf";
import type { GeneratedRecording } from "./use-generate-recording-mutation";

export interface RecordingsLibraryPage {
  items: GeneratedRecording[];
  total_count: number;
  overall_count: number;
  total_duration_seconds: number;
  voices_used: { id: string; name: string }[];
  page: number;
  limit: number;
}

export interface RecordingsLibraryParams {
  search?: string;
  voiceId?: string;
  limit?: number;
}

export function recordingsLibraryQueryKey(params: RecordingsLibraryParams) {
  return ["recordings-library", params.search ?? "", params.voiceId ?? "", params.limit ?? 20] as const;
}

export function useRecordingsLibraryQuery(params: RecordingsLibraryParams) {
  const limit = params.limit ?? 20;
  return useInfiniteQuery({
    queryKey: recordingsLibraryQueryKey(params),
    queryFn: ({ pageParam }) => {
      const query = new URLSearchParams({ page: String(pageParam), limit: String(limit) });
      if (params.search) query.set("search", params.search);
      if (params.voiceId) query.set("voice_id", params.voiceId);
      return apiFetch<RecordingsLibraryPage>(`/api/v1/tts/recordings?${query.toString()}`);
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      const loaded = lastPage.page * lastPage.limit;
      return loaded < lastPage.total_count ? lastPage.page + 1 : undefined;
    },
  });
}
