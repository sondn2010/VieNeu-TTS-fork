"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { apiFetch } from "../api/api-client-with-csrf";
import { useUserProfileQuery } from "../api/use-user-profile-query";
import { en } from "./messages-en";
import { vi, type Messages } from "./messages-vi";

export type Language = "vi" | "en";

const STORAGE_KEY = "vn_ui_language";

const CATALOGS: Record<Language, Messages> = { vi, en };

interface I18nContextValue {
  language: Language;
  setLanguage: (language: Language) => void;
  messages: Messages;
}

const I18nContext = createContext<I18nContextValue | null>(null);

function readStoredLanguage(): Language {
  if (typeof window === "undefined") return "vi";
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === "en" ? "en" : "vi";
  } catch {
    return "vi";
  }
}

function applyLanguage(language: Language): void {
  document.documentElement.setAttribute("lang", language);
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    // Private browsing / storage disabled: language still works for this tab.
  }
}

/** Vietnamese by default; same persistence model as `ThemeProvider`. */
export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(readStoredLanguage);
  const { data: profile } = useUserProfileQuery();

  // Render-phase adjustment (a state variable, not a ref — see
  // ThemeProvider for the full rationale), not an effect.
  const [lastSyncedProfileLanguage, setLastSyncedProfileLanguage] = useState<Language | undefined>(undefined);
  if (profile && profile.ui_language !== lastSyncedProfileLanguage) {
    setLastSyncedProfileLanguage(profile.ui_language);
    if (profile.ui_language !== language) {
      setLanguageState(profile.ui_language);
    }
  }

  useEffect(() => {
    applyLanguage(language);
  }, [language]);

  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next);
    apiFetch("/api/v1/user/profile", { method: "PATCH", body: { ui_language: next } }).catch(() => {
      // Best-effort: the UI already reflects the choice for this session.
    });
  }, []);

  const value = useMemo(
    () => ({ language, setLanguage, messages: CATALOGS[language] }),
    [language, setLanguage],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return ctx;
}

/** Rendered as a plain `<script>` text child (never `dangerouslySetInnerHTML`)
 * — a static, non-interpolated string we authored, not user content. */
export const I18N_BOOTSTRAP_SCRIPT = `(function(){try{var l=localStorage.getItem(${JSON.stringify(
  STORAGE_KEY,
)});if(l==="en"){document.documentElement.setAttribute("lang","en");}}catch(e){}})();`;
