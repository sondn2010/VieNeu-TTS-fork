"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { LibraryFilterBar } from "../../../components/library/library-filter-bar";
import { LibraryRecordingCard } from "../../../components/library/library-recording-card";
import { LibrarySummaryFooter } from "../../../components/library/library-summary-footer";
import { apiFetch } from "../../../lib/api/api-client-with-csrf";
import { recordingsLibraryQueryKey, useRecordingsLibraryQuery } from "../../../lib/api/use-recordings-library-query";
import { useI18n } from "../../../lib/i18n/i18n-provider";

export default function VoicesPage() {
  const { messages } = useI18n();
  const t = messages.library;
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [voiceId, setVoiceId] = useState("");

  const query = useRecordingsLibraryQuery({ search, voiceId });
  const pages = query.data?.pages ?? [];
  const items = pages.flatMap((page) => page.items);
  const lastPage = pages[pages.length - 1];
  const voicesUsed = lastPage?.voices_used ?? [];
  const voiceNameById = Object.fromEntries(voicesUsed.map((v) => [v.id, v.name]));
  const shownCount = lastPage?.total_count ?? 0;
  const overallCount = lastPage?.overall_count ?? 0;
  const totalDurationSeconds = lastPage?.total_duration_seconds ?? 0;

  async function handleDelete(id: string) {
    try {
      await apiFetch(`/api/v1/tts/recordings/${id}`, { method: "DELETE" });
      await queryClient.invalidateQueries({ queryKey: recordingsLibraryQueryKey({ search, voiceId }) });
    } catch {
      // Best-effort: the card stays until the next manual refresh/retry.
    }
  }

  return (
    <div style={{ padding: 24, maxWidth: 980, margin: "0 auto", display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <header style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--color-text-primary)", margin: 0 }}>{t.title}</h1>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "4px 0 0" }}>{t.subtitle}</p>
      </header>

      <LibraryFilterBar search={search} onSearchChange={setSearch} voiceId={voiceId} onVoiceIdChange={setVoiceId} voicesUsed={voicesUsed} />

      <div style={{ flex: 1 }}>
        {query.isLoading && <p style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>{messages.common.loading}</p>}
        {query.isError && <p style={{ color: "var(--color-danger-text)", fontSize: 13 }}>{t.errorLoading}</p>}
        {!query.isLoading && !query.isError && items.length === 0 && (
          <div style={{ textAlign: "center", padding: "60px 0" }}>
            <p style={{ color: "var(--color-text-primary)", fontWeight: 600, margin: 0 }}>{t.emptyTitle}</p>
            <p style={{ color: "var(--color-text-secondary)", fontSize: 13, margin: "4px 0 0" }}>{t.emptySubtitle}</p>
          </div>
        )}
        {items.map((item) => (
          <LibraryRecordingCard key={item.id} recording={item} voiceName={voiceNameById[item.voice_id] ?? ""} onDelete={handleDelete} />
        ))}
        {query.hasNextPage && (
          <div style={{ textAlign: "center", marginTop: 8 }}>
            <button
              type="button"
              onClick={() => query.fetchNextPage()}
              disabled={query.isFetchingNextPage}
              style={{
                background: "none",
                border: "1px solid var(--color-border)",
                color: "var(--color-text-secondary)",
                borderRadius: 8,
                padding: "8px 16px",
                cursor: query.isFetchingNextPage ? "not-allowed" : "pointer",
              }}
            >
              {t.loadMoreButton}
            </button>
          </div>
        )}
      </div>

      <LibrarySummaryFooter shownCount={shownCount} totalCount={overallCount} totalDurationSeconds={totalDurationSeconds} />
    </div>
  );
}
