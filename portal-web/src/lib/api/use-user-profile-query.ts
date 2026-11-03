"use client";

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "./api-client-with-csrf";

export interface UserClientConfig {
  tokens_per_char_milli: number;
  tts_max_chars: number;
  tts_sync_char_cap: number;
  terms_version: string;
}

export interface UserProfile {
  id: string;
  email: string;
  username: string;
  avatar_initials: string;
  plan_tier: string;
  token_balance: number;
  token_quota_total: number;
  daily_char_limit: number;
  daily_char_remaining: number;
  plan_expires_at: string | null;
  has_accepted_tts_terms: boolean;
  terms_version: string | null;
  onboarding_completed_steps: number;
  onboarding_hidden: boolean;
  ui_theme: "dark" | "light";
  ui_language: "vi" | "en";
  role: "USER" | "ADMIN" | "SUPERADMIN";
  client_config: UserClientConfig;
}

export const USER_PROFILE_QUERY_KEY = ["user-profile"] as const;

export function useUserProfileQuery(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: USER_PROFILE_QUERY_KEY,
    queryFn: () => apiFetch<UserProfile>("/api/v1/user/profile"),
    retry: false,
    enabled: options.enabled ?? true,
  });
}
