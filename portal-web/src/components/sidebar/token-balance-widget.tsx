"use client";

import { Wallet } from "lucide-react";

import { useI18n } from "../../lib/i18n/i18n-provider";
import { formatTokenBalance } from "../../lib/format/vietnamese-number-and-date-format";

export interface TokenBalanceWidgetProps {
  balance: number;
  quota: number;
}

export function TokenBalanceWidget({ balance, quota }: TokenBalanceWidgetProps) {
  const { messages } = useI18n();
  return (
    <div
      style={{
        display: "flex", alignItems: "center", gap: 8, padding: "10px 12px",
        borderRadius: 8, background: "var(--color-surface)", border: "1px solid var(--color-border)",
      }}
    >
      <Wallet size={16} color="var(--color-accent)" aria-hidden />
      <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0 }}>
        <span style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>{messages.sidebar.tokenBalance}</span>
        <span className="vn-mono" style={{ fontSize: 13, color: "var(--color-text-primary)" }}>
          {formatTokenBalance(balance, quota)}
        </span>
      </div>
    </div>
  );
}
