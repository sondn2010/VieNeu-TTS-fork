"use client";

import { useI18n } from "../../lib/i18n/i18n-provider";

export interface LibrarySummaryFooterProps {
  shownCount: number;
  totalCount: number;
  totalDurationSeconds: number;
}

/** TC-07: `X trong số Y giọng nói` / `Tổng thời lượng: ...s`. */
export function LibrarySummaryFooter({ shownCount, totalCount, totalDurationSeconds }: LibrarySummaryFooterProps) {
  const { messages } = useI18n();
  const t = messages.library;

  return (
    <div
      style={{
        position: "sticky",
        bottom: 0,
        display: "flex",
        justifyContent: "space-between",
        padding: "12px 4px",
        fontSize: 13,
        color: "var(--color-text-secondary)",
        background: "var(--color-bg-primary)",
        borderTop: "1px solid var(--color-border)",
      }}
    >
      <span>
        {shownCount} {t.countInfix} {totalCount} {t.countSuffix}
      </span>
      <span>
        {t.totalDurationLabel} {totalDurationSeconds.toFixed(1)}s
      </span>
    </div>
  );
}
