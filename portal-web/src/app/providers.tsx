"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { I18nProvider } from "../lib/i18n/i18n-provider";
import { ThemeProvider } from "../lib/theme/theme-provider";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: false } } }));
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <I18nProvider>{children}</I18nProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
