"use client";

/** React Query hooks over every `/api/v1/admin/*` endpoint (phase 13), one
 * file per the phase 14 plan so every admin page/component shares the same
 * query keys and invalidation rules. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "../../lib/api/api-client-with-csrf";

export interface AdminUserRow {
  id: string;
  email: string;
  username: string;
  role: "USER" | "ADMIN" | "SUPERADMIN";
  is_active: boolean;
  plan_tier: string;
  token_balance: number;
  token_quota_total: number;
  daily_char_limit: number;
  daily_char_remaining: number;
  plan_expires_at: string | null;
  created_at: string;
  last_login_at: string | null;
  recording_count: number;
}

export interface AdminUsersPage {
  items: AdminUserRow[];
  total_count: number;
  page: number;
  limit: number;
}

export interface AdminUsersParams {
  search?: string;
  role?: string;
  status?: string;
  page?: number;
}

export function useAdminUsersQuery(params: AdminUsersParams) {
  return useQuery({
    queryKey: ["admin-users", params],
    queryFn: () => {
      const query = new URLSearchParams();
      if (params.search) query.set("search", params.search);
      if (params.role) query.set("role", params.role);
      if (params.status) query.set("status", params.status);
      query.set("page", String(params.page ?? 1));
      return apiFetch<AdminUsersPage>(`/api/v1/admin/users?${query.toString()}`);
    },
  });
}

export function useAdminUserQuery(userId: string | null) {
  return useQuery({
    queryKey: ["admin-user", userId],
    queryFn: () => apiFetch<{ user: AdminUserRow }>(`/api/v1/admin/users/${userId}`),
    enabled: !!userId,
  });
}

export interface CreateUserInput {
  email: string;
  username?: string;
  password: string;
  role?: string;
}

export function useCreateUserMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateUserInput) =>
      apiFetch<{ user: AdminUserRow }>("/api/v1/admin/users", { method: "POST", body: input }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}

export interface UpdateUserInput {
  email?: string;
  username?: string;
  is_active?: boolean;
}

export function useUpdateUserMutation(userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateUserInput) =>
      apiFetch<{ user: AdminUserRow }>(`/api/v1/admin/users/${userId}`, { method: "PATCH", body: input }),
    onSuccess: (data) => {
      queryClient.setQueryData(["admin-user", userId], data);
      void queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
}

export function useSetUserRoleMutation(userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (role: string) =>
      apiFetch<{ user: AdminUserRow }>(`/api/v1/admin/users/${userId}/role`, { method: "PUT", body: { role } }),
    onSuccess: (data) => {
      queryClient.setQueryData(["admin-user", userId], data);
      void queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
}

export function useAdminResetPasswordMutation(userId: string) {
  return useMutation({
    mutationFn: (newPassword: string) =>
      apiFetch(`/api/v1/admin/users/${userId}/password`, { method: "POST", body: { new_password: newPassword } }),
  });
}

export function useDeleteUserMutation(userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (confirmEmail: string) =>
      apiFetch(`/api/v1/admin/users/${userId}`, { method: "DELETE", body: { confirm_email: confirmEmail } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}

export function useAdjustTokensMutation(userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { delta: number; reason: string }) =>
      apiFetch<{ token_balance: number }>(`/api/v1/admin/users/${userId}/tokens`, { method: "POST", body: input }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin-user", userId] });
      void queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
}

export interface UpdatePlanInput {
  plan_tier?: string;
  token_quota_total?: number;
  daily_char_limit?: number;
  plan_expires_at?: string | null;
  reset_daily_remaining?: boolean;
}

export function useUpdatePlanMutation(userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdatePlanInput) =>
      apiFetch<{ user: AdminUserRow }>(`/api/v1/admin/users/${userId}/plan`, { method: "PATCH", body: input }),
    onSuccess: (data) => {
      queryClient.setQueryData(["admin-user", userId], data);
      void queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
}

export interface AdminApiKey {
  id: string;
  name: string;
  environment: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}

export function useAdminApiKeysQuery(userId: string | null) {
  return useQuery({
    queryKey: ["admin-api-keys", userId],
    queryFn: () => apiFetch<{ items: AdminApiKey[] }>(`/api/v1/admin/users/${userId}/api-keys`),
    enabled: !!userId,
  });
}

export function useRevokeApiKeyMutation(userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) => apiFetch(`/api/v1/admin/users/${userId}/api-keys/${keyId}/revoke`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-api-keys", userId] }),
  });
}

export interface AdminRecordingRow {
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
}

export interface AdminRecordingsParams {
  search?: string;
  voiceId?: string;
  status?: string;
  page?: number;
}

export function useAdminUserRecordingsQuery(userId: string | null, params: AdminRecordingsParams) {
  return useQuery({
    queryKey: ["admin-user-recordings", userId, params],
    queryFn: () => {
      const query = new URLSearchParams();
      if (params.search) query.set("search", params.search);
      if (params.voiceId) query.set("voice_id", params.voiceId);
      if (params.status) query.set("status", params.status);
      query.set("page", String(params.page ?? 1));
      return apiFetch<{ items: AdminRecordingRow[]; total_count: number; page: number }>(
        `/api/v1/admin/users/${userId}/recordings?${query.toString()}`,
      );
    },
    enabled: !!userId,
  });
}

export function useDeleteAdminRecordingMutation(userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (recordingId: string) => apiFetch(`/api/v1/admin/recordings/${recordingId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-user-recordings", userId] }),
  });
}

export interface AdminDictionaryPack {
  id: number;
  name: string;
  kind: string;
  is_enabled: boolean;
  description: string;
  sort_order: number;
  updated_at: string;
  etag: string;
}

export function useAdminDictionariesQuery() {
  return useQuery({
    queryKey: ["admin-dictionaries"],
    queryFn: () => apiFetch<{ items: AdminDictionaryPack[] }>("/api/v1/admin/system-dictionaries"),
  });
}

export interface CreateDictionaryInput {
  name: string;
  kind: string;
}

export function useCreateDictionaryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateDictionaryInput) =>
      apiFetch<{ dictionary: AdminDictionaryPack; rejected: unknown[] }>("/api/v1/admin/system-dictionaries", {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-dictionaries"] }),
  });
}

export interface UpdateDictionaryInput {
  name?: string;
  kind?: string;
  is_enabled?: boolean;
  description?: string;
  sort_order?: number;
}

export function useUpdateDictionaryMutation(dictionaryId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateDictionaryInput) =>
      apiFetch<{ dictionary: AdminDictionaryPack }>(`/api/v1/admin/system-dictionaries/${dictionaryId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-dictionaries"] }),
  });
}

export function useDeleteDictionaryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (dictionaryId: number) =>
      apiFetch(`/api/v1/admin/system-dictionaries/${dictionaryId}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-dictionaries"] }),
  });
}

export interface AdminDictionaryRule {
  id: string;
  source_term: string;
  phonetic_replacement: string;
  match_whole_word: boolean;
  case_sensitive: boolean;
  is_enabled: boolean;
  sort_order: number;
  note: string;
  rule_kind: "REPLACE" | "ENGLISH_FALLBACK";
}

export function useAdminDictionaryRulesQuery(dictionaryId: number | null) {
  return useQuery({
    queryKey: ["admin-dictionary-rules", dictionaryId],
    queryFn: () =>
      apiFetch<{ items: AdminDictionaryRule[]; total_count: number; etag: string }>(
        `/api/v1/admin/system-dictionaries/${dictionaryId}/rules?limit=200`,
      ),
    enabled: dictionaryId !== null,
  });
}

export interface RuleInput {
  term: string;
  replacement: string;
  mode: "phonetic" | "en";
  case_sensitive: boolean;
  note: string;
}

export function useReplaceDictionaryRulesMutation(dictionaryId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ rules, etag }: { rules: RuleInput[]; etag: string }) =>
      apiFetch<{ dictionary: AdminDictionaryPack; rejected: unknown[] }>(
        `/api/v1/admin/system-dictionaries/${dictionaryId}/rules`,
        { method: "PUT", body: { rules }, headers: { "If-Match": etag } },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin-dictionary-rules", dictionaryId] });
      void queryClient.invalidateQueries({ queryKey: ["admin-dictionaries"] });
    },
  });
}

export interface ImportDictionaryInput {
  file: File;
  format: "json" | "txt";
  mode: "merge" | "replace";
}

export function useImportDictionaryMutation(dictionaryId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, format, mode }: ImportDictionaryInput) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiFetch<{
        dictionary: AdminDictionaryPack;
        rejected: unknown[];
        line_errors: { line: number; message: string }[];
      }>(`/api/v1/admin/system-dictionaries/${dictionaryId}/import?format=${format}&mode=${mode}`, {
        method: "POST",
        rawBody: formData,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin-dictionary-rules", dictionaryId] });
      void queryClient.invalidateQueries({ queryKey: ["admin-dictionaries"] });
    },
  });
}

export interface AdminVoiceRow {
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
  sort_order: number;
}

export function useAdminVoicesQuery() {
  return useQuery({
    queryKey: ["admin-voices"],
    queryFn: () => apiFetch<{ items: AdminVoiceRow[] }>("/api/v1/admin/voices"),
  });
}

export interface UpdateVoiceInput {
  name?: string;
  gender?: string;
  region?: string;
  tags?: string[];
  language_label?: string;
  is_active?: boolean;
  sort_order?: number;
}

export function useUpdateVoiceMutation(voiceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateVoiceInput) =>
      apiFetch<{ voice: AdminVoiceRow }>(`/api/v1/admin/voices/${voiceId}`, { method: "PATCH", body: input }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-voices"] }),
  });
}

export function useUploadVoiceAvatarMutation(voiceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiFetch<{ voice: AdminVoiceRow }>(`/api/v1/admin/voices/${voiceId}/avatar`, {
        method: "PUT",
        rawBody: formData,
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-voices"] }),
  });
}

export function useDeleteVoiceAvatarMutation(voiceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<{ voice: AdminVoiceRow }>(`/api/v1/admin/voices/${voiceId}/avatar`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-voices"] }),
  });
}

export function useUploadVoiceSampleMutation(voiceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiFetch<{ voice: AdminVoiceRow }>(`/api/v1/admin/voices/${voiceId}/sample`, {
        method: "PUT",
        rawBody: formData,
      });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-voices"] }),
  });
}

export function useRenderVoiceSampleMutation(voiceId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (text: string | undefined) =>
      apiFetch<{ voice: AdminVoiceRow }>(`/api/v1/admin/voices/${voiceId}/sample/render`, {
        method: "POST",
        body: { text: text || undefined },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-voices"] }),
  });
}

export interface AdminAuditLogRow {
  id: number;
  actor_user_id: string | null;
  actor_label: string;
  action: string;
  target_type: string;
  target_id: string;
  target_label: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditLogParams {
  actor?: string;
  action?: string;
  targetType?: string;
  targetId?: string;
  from?: string;
  to?: string;
  page?: number;
}

export function useAdminAuditLogQuery(params: AuditLogParams) {
  return useQuery({
    queryKey: ["admin-audit-log", params],
    queryFn: () => {
      const query = new URLSearchParams();
      if (params.actor) query.set("actor", params.actor);
      if (params.action) query.set("action", params.action);
      if (params.targetType) query.set("target_type", params.targetType);
      if (params.targetId) query.set("target_id", params.targetId);
      if (params.from) query.set("from", params.from);
      if (params.to) query.set("to", params.to);
      query.set("page", String(params.page ?? 1));
      return apiFetch<{ items: AdminAuditLogRow[]; total_count: number; page: number; limit: number }>(
        `/api/v1/admin/audit-log?${query.toString()}`,
      );
    },
  });
}
