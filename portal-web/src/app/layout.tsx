import type { Metadata } from "next";
import type { ReactNode } from "react";

import { I18N_BOOTSTRAP_SCRIPT } from "../lib/i18n/i18n-provider";
import { THEME_BOOTSTRAP_SCRIPT } from "../lib/theme/theme-provider";
import "../styles/globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "VieNeu",
  description: "VieNeu TTS Platform",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi" data-theme="dark" suppressHydrationWarning>
      <head>
        {/* Plain `<script>` text children (not `dangerouslySetInnerHTML`):
            static, non-interpolated strings we authored, read `localStorage`
            before paint so there is no flash of the wrong theme/language. */}
        <script>{THEME_BOOTSTRAP_SCRIPT}</script>
        <script>{I18N_BOOTSTRAP_SCRIPT}</script>
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
