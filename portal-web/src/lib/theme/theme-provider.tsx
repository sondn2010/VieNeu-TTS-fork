"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { apiFetch } from "../api/api-client-with-csrf";
import { useUserProfileQuery } from "../api/use-user-profile-query";

export type Theme = "dark" | "light";

const STORAGE_KEY = "vn_ui_theme";

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function readStoredTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Private browsing / storage disabled: theme still works for this tab.
  }
}

/**
 * Dark by default; `localStorage` sets the first paint (via the inline
 * blocking script in the root layout), the server profile is authoritative
 * once it loads, and a manual toggle persists both immediately.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(readStoredTheme);
  const { data: profile } = useUserProfileQuery();

  // Adjust state when the server value changes — the React-docs "adjusting
  // state when a prop changes" pattern: a plain state variable (not a ref,
  // which the lint rules forbid reading/writing during render) remembers
  // the last profile value seen, and setting it mid-render here bails out
  // of this render and immediately re-renders with the synced value — no
  // extra commit, no flicker, and never an effect doing the setState.
  const [lastSyncedProfileTheme, setLastSyncedProfileTheme] = useState<Theme | undefined>(undefined);
  if (profile && profile.ui_theme !== lastSyncedProfileTheme) {
    setLastSyncedProfileTheme(profile.ui_theme);
    if (profile.ui_theme !== theme) {
      setThemeState(profile.ui_theme);
    }
  }

  // The actual DOM/localStorage side effect belongs in an effect: it
  // synchronizes an external system with the latest React state, whatever
  // caused `theme` to change (profile sync above, or a manual toggle).
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    apiFetch("/api/v1/user/profile", { method: "PATCH", body: { ui_theme: next } }).catch(() => {
      // Best-effort: the UI already reflects the choice for this session.
    });
  }, []);

  const value = useMemo(() => ({ theme, setTheme }), [theme, setTheme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return ctx;
}

/** Rendered as a plain `<script>` text child (never `dangerouslySetInnerHTML`)
 * — a static, non-interpolated string we authored, not user content. */
export const THEME_BOOTSTRAP_SCRIPT = `(function(){try{var t=localStorage.getItem(${JSON.stringify(
  STORAGE_KEY,
)});if(t==="light"){document.documentElement.setAttribute("data-theme","light");}}catch(e){}})();`;
