"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Ban, CheckCircle2, Scale } from "lucide-react";
import { useState } from "react";

import { apiFetch } from "../../lib/api/api-client-with-csrf";
import { USER_PROFILE_QUERY_KEY } from "../../lib/api/use-user-profile-query";
import { useI18n } from "../../lib/i18n/i18n-provider";

export const TERMS_ACCEPTED_STORAGE_KEY = "vieneu_tts_terms_v1_accepted";

export interface TermsConsentModalProps {
  termsVersion: string;
  onAccepted: () => void;
}

/**
 * Blocks interaction until the current Terms are accepted. No close on
 * backdrop click or `Escape` (TC-01) — there is deliberately no `onClick`
 * on the backdrop and no `keydown` handler for Escape.
 */
export function TermsConsentModal({ termsVersion, onAccepted }: TermsConsentModalProps) {
  const { messages } = useI18n();
  const t = messages.terms;
  const queryClient = useQueryClient();
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleAccept() {
    if (!checked || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiFetch("/api/v1/user/terms/accept", { method: "POST", body: { terms_version: termsVersion } });
      try {
        window.localStorage.setItem(TERMS_ACCEPTED_STORAGE_KEY, "true");
      } catch {
        // Private browsing / storage disabled: the server flag still gates access.
      }
      await queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
      onAccepted();
    } catch {
      setError(t.genericError);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      role="presentation"
      style={{
        position: "fixed", inset: 0, background: "rgba(5,5,10,0.78)", backdropFilter: "blur(4px)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 60, overflow: "hidden",
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t.title}
        style={{
          width: "100%", maxWidth: 520, maxHeight: "85vh", background: "#13131c",
          border: "1px solid #28283c", borderRadius: 14, display: "flex", flexDirection: "column",
        }}
      >
        <header style={{ display: "flex", alignItems: "center", gap: 12, padding: "16px 20px" }}>
          <span
            aria-hidden
            style={{
              width: 36, height: 36, borderRadius: 10, background: "rgba(124,92,252,0.15)",
              display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
            }}
          >
            <Scale size={18} color="var(--color-accent)" />
          </span>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "#fff", margin: 0 }}>{t.title}</h2>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: 0 }}>{t.subtitle}</p>
          </div>
        </header>

        <div style={{ padding: "0 20px", overflowY: "auto", flex: 1 }}>
          <p style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>{t.intro}</p>

          <div
            style={{
              background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.3)",
              borderRadius: 10, padding: "14px 16px", marginBottom: 12,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#34d399", fontWeight: 700, marginBottom: 6 }}>
              <CheckCircle2 size={16} aria-hidden />
              {t.allowedTitle}
            </div>
            <p style={{ color: "#6ee7b7", fontSize: 13, margin: 0 }}>{t.allowedText}</p>
          </div>

          <div
            style={{
              background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: 10, padding: "14px 16px", marginBottom: 12,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#f87171", fontWeight: 700, marginBottom: 6 }}>
              <Ban size={16} aria-hidden />
              {t.prohibitedTitle}
            </div>
            <ul style={{ color: "#fca5a5", fontSize: 13, margin: 0, paddingLeft: 18 }}>
              {t.prohibitedItems.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </div>

        <footer style={{ padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
          <label style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: 13, color: "var(--color-text-primary)" }}>
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              style={{ marginTop: 2 }}
            />
            {t.checkboxLabel}
          </label>
          {error && <p style={{ color: "var(--color-danger-text)", fontSize: 12, margin: 0 }}>{error}</p>}
          <button
            type="button"
            disabled={!checked || submitting}
            onClick={handleAccept}
            style={{
              width: "100%", height: 42, borderRadius: 8, background: "#7c5cfc", color: "#fff",
              fontWeight: 700, border: "none", cursor: checked && !submitting ? "pointer" : "not-allowed",
              opacity: checked && !submitting ? 1 : 0.5,
            }}
          >
            {t.acceptButton}
          </button>
        </footer>
      </div>
    </div>
  );
}
