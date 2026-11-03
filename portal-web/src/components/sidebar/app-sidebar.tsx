"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Moon, Sun } from "lucide-react";

import { useI18n, type Language } from "../../lib/i18n/i18n-provider";
import { useTheme } from "../../lib/theme/theme-provider";
import type { UserProfile } from "../../lib/api/use-user-profile-query";
import { ACCOUNT_GROUP, ADMIN_GROUP, CREATE_GROUP, LIBRARY_GROUP, type NavGroup } from "./sidebar-nav-groups";
import { TokenBalanceWidget } from "./token-balance-widget";
import { UserProfileCard } from "./user-profile-card";

const ADMIN_ROLES = new Set(["ADMIN", "SUPERADMIN"]);

export interface AppSidebarProps {
  profile: UserProfile;
}

function NavGroupSection({ group }: { group: NavGroup }) {
  const pathname = usePathname();
  const { messages } = useI18n();
  return (
    <div style={{ marginBottom: 16 }}>
      <div
        style={{
          fontSize: 11, letterSpacing: "0.05em", color: "var(--color-text-muted)",
          padding: "0 12px", marginBottom: 6,
        }}
      >
        {messages.sidebar[group.titleKey]}
      </div>
      {group.items.map((item) => {
        const Icon = item.icon;
        const active = pathname === item.href;
        const label = messages.sidebar[item.labelKey];
        if (!item.live) {
          return (
            <div
              key={item.href}
              aria-disabled="true"
              title={messages.common.comingSoon}
              style={{
                display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: 8,
                color: "var(--color-text-muted)", fontSize: 13, cursor: "not-allowed",
              }}
            >
              <Icon size={16} aria-hidden />
              <span style={{ flex: 1 }}>{label}</span>
              <span
                style={{
                  fontSize: 10, padding: "1px 6px", borderRadius: 999,
                  background: "var(--color-bg-secondary)", border: "1px solid var(--color-border)",
                }}
              >
                {messages.common.comingSoon}
              </span>
            </div>
          );
        }
        return (
          <Link
            key={item.href}
            href={item.href}
            style={{
              display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: 8,
              color: active ? "#fff" : "var(--color-text-secondary)",
              background: active ? "var(--color-accent)" : "transparent", fontSize: 13,
            }}
          >
            <Icon size={16} aria-hidden />
            {label}
          </Link>
        );
      })}
    </div>
  );
}

export function AppSidebar({ profile }: AppSidebarProps) {
  const { messages, language, setLanguage } = useI18n();
  const { theme, setTheme } = useTheme();
  const isAdmin = ADMIN_ROLES.has(profile.role);

  return (
    <aside
      style={{
        width: 240, flexShrink: 0, height: "100vh", display: "flex", flexDirection: "column",
        background: "var(--color-bg-secondary)", borderRight: "1px solid var(--color-border)",
      }}
    >
      <div style={{ padding: "16px 12px", display: "flex", alignItems: "center", gap: 10 }}>
        <span
          aria-hidden
          style={{
            width: 28, height: 28, borderRadius: 8, background: "var(--color-accent)",
            display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 700,
          }}
        >
          V
        </span>
        <span style={{ fontWeight: 700, color: "#fff" }}>{messages.common.appName}</span>
      </div>

      <nav style={{ flex: 1, overflowY: "auto", padding: "4px 8px" }}>
        <NavGroupSection group={CREATE_GROUP} />
        <NavGroupSection group={LIBRARY_GROUP} />
        <NavGroupSection group={ACCOUNT_GROUP} />
        {isAdmin && <NavGroupSection group={ADMIN_GROUP} />}
      </nav>

      <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 10, borderTop: "1px solid var(--color-border)" }}>
        <TokenBalanceWidget balance={profile.token_balance} quota={profile.token_quota_total} />
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            type="button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label="toggle theme"
            style={{
              background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 6,
              width: 32, height: 32, display: "flex", alignItems: "center", justifyContent: "center",
              color: "var(--color-text-secondary)", cursor: "pointer",
            }}
          >
            {theme === "dark" ? <Sun size={14} aria-hidden /> : <Moon size={14} aria-hidden />}
          </button>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            aria-label="language"
            style={{
              background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 6,
              padding: "6px 8px", color: "var(--color-text-secondary)", fontSize: 12,
            }}
          >
            <option value="vi">VI</option>
            <option value="en">EN</option>
          </select>
        </div>
        <UserProfileCard profile={profile} />
      </div>
    </aside>
  );
}
