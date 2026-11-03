"use client";

import { Sigma, X } from "lucide-react";
import { useState } from "react";

import { useI18n } from "../../lib/i18n/i18n-provider";

const DISMISSED_KEY = "vieneu_math_chem_banner_dismissed";

function readDismissed(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(DISMISSED_KEY) === "true";
  } catch {
    return false;
  }
}

export function MathChemFeatureBanner() {
  const { messages } = useI18n();
  const [dismissed, setDismissed] = useState<boolean>(readDismissed);

  if (dismissed) return null;

  function dismiss() {
    setDismissed(true);
    try {
      window.localStorage.setItem(DISMISSED_KEY, "true");
    } catch {
      // Private browsing / storage disabled: dismissed only for this view.
    }
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        background: "rgba(124,92,252,0.12)",
        border: "1px solid rgba(124,92,252,0.35)",
        borderRadius: 8,
        padding: "10px 14px",
        marginBottom: 12,
      }}
    >
      <Sigma size={18} aria-hidden color="var(--color-accent)" style={{ flexShrink: 0 }} />
      <p style={{ flex: 1, fontSize: 13, color: "var(--color-text-primary)", margin: 0 }}>{messages.studio.bannerText}</p>
      <button
        type="button"
        onClick={dismiss}
        aria-label={messages.common.close}
        style={{ background: "none", border: "none", cursor: "pointer", color: "var(--color-text-secondary)" }}
      >
        <X size={16} aria-hidden />
      </button>
    </div>
  );
}
