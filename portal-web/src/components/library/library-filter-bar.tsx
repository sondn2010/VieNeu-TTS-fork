"use client";

import { Plus, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useI18n } from "../../lib/i18n/i18n-provider";

export interface LibraryFilterBarProps {
  search: string;
  onSearchChange: (value: string) => void;
  voiceId: string;
  onVoiceIdChange: (value: string) => void;
  voicesUsed: { id: string; name: string }[];
}

const SEARCH_DEBOUNCE_MS = 250;

export function LibraryFilterBar({ search, onSearchChange, voiceId, onVoiceIdChange, voicesUsed }: LibraryFilterBarProps) {
  const { messages } = useI18n();
  const t = messages.library;
  const router = useRouter();
  const [draft, setDraft] = useState(search);

  useEffect(() => {
    const timer = setTimeout(() => onSearchChange(draft), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
    // Only the debounce timer depends on `draft`; `onSearchChange` is
    // expected to be referentially stable from the caller's state setter.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft]);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
      <div style={{ position: "relative", width: 420 }}>
        <Search
          size={16}
          aria-hidden
          style={{ position: "absolute", left: 12, top: 12, color: "var(--color-text-secondary)" }}
        />
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={t.searchPlaceholder}
          style={{
            width: "100%",
            height: 40,
            borderRadius: 8,
            border: "1px solid var(--color-border)",
            background: "var(--color-bg-secondary)",
            color: "var(--color-text-primary)",
            padding: "0 12px 0 36px",
          }}
        />
      </div>
      <select
        value={voiceId}
        onChange={(e) => onVoiceIdChange(e.target.value)}
        style={{
          height: 40,
          borderRadius: 8,
          border: "1px solid var(--color-border)",
          background: "var(--color-bg-secondary)",
          color: "var(--color-text-primary)",
          padding: "0 10px",
        }}
      >
        <option value="">{t.voiceFilterAll}</option>
        {voicesUsed.map((v) => (
          <option key={v.id} value={v.id}>
            {v.name}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={() => router.push("/studio/")}
        style={{
          marginLeft: "auto",
          display: "flex",
          alignItems: "center",
          gap: 6,
          background: "var(--color-accent)",
          color: "#fff",
          fontWeight: 700,
          border: "none",
          borderRadius: 8,
          padding: "0 16px",
          height: 40,
          cursor: "pointer",
        }}
      >
        <Plus size={16} aria-hidden />
        {t.createNewButton}
      </button>
    </div>
  );
}
