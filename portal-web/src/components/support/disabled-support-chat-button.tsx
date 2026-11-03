"use client";

import { MessageCircleQuestion } from "lucide-react";

import { useI18n } from "../../lib/i18n/i18n-provider";

/** Floating support chat button (bottom-right), deferred to C2 — rendered
 * disabled with a "Sắp có"/"Soon" tooltip. */
export function DisabledSupportChatButton() {
  const { messages } = useI18n();
  return (
    <button
      type="button"
      disabled
      title={messages.common.comingSoon}
      aria-label={`${messages.sidebar.help} — ${messages.common.comingSoon}`}
      style={{
        position: "fixed", bottom: 24, right: 24, width: 52, height: 52, borderRadius: "50%",
        background: "var(--color-accent)", opacity: 0.5, border: "none", cursor: "not-allowed",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 40,
      }}
    >
      <MessageCircleQuestion color="#fff" size={22} aria-hidden />
    </button>
  );
}
