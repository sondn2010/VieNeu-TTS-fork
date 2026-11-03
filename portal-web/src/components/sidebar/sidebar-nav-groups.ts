import {
  BarChart3,
  BookOpen,
  Clapperboard,
  Code2,
  CreditCard,
  Download,
  Grid2x2,
  Mic,
  Presentation,
  Radio,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Users,
  Volume2,
  type LucideIcon,
} from "lucide-react";

import type { Messages } from "../../lib/i18n/messages-vi";

export interface NavItem {
  href: string;
  labelKey: keyof Messages["sidebar"];
  icon: LucideIcon;
  /** Only `studio` and `voices` are live in C1; everything else renders
   * disabled with a "Sắp có"/"Soon" badge. */
  live: boolean;
}

export interface NavGroup {
  titleKey: keyof Messages["sidebar"];
  items: readonly NavItem[];
}

export const CREATE_GROUP: NavGroup = {
  titleKey: "groupCreate",
  items: [
    { href: "/studio/", labelKey: "studio", icon: Mic, live: true },
    { href: "/podcast/", labelKey: "podcast", icon: Radio, live: false },
    { href: "/stories/", labelKey: "stories", icon: BookOpen, live: false },
    { href: "/dubbing/", labelKey: "dubbing", icon: Clapperboard, live: false },
    { href: "/lectures/", labelKey: "lectures", icon: Presentation, live: false },
  ],
};

export const LIBRARY_GROUP: NavGroup = {
  titleKey: "groupLibrary",
  items: [
    { href: "/voices/", labelKey: "voices", icon: Volume2, live: true },
    { href: "/leaderboard/", labelKey: "leaderboard", icon: BarChart3, live: false },
    { href: "/voice-cloning/", labelKey: "voiceCloning", icon: Sparkles, live: false },
    { href: "/community/", labelKey: "community", icon: Users, live: false },
    { href: "/download/", labelKey: "downloadApp", icon: Download, live: false },
  ],
};

export const ACCOUNT_GROUP: NavGroup = {
  titleKey: "groupAccount",
  items: [
    { href: "/dashboard/", labelKey: "dashboard", icon: Grid2x2, live: false },
    { href: "/billing/", labelKey: "billing", icon: CreditCard, live: false },
    { href: "/developer/", labelKey: "developer", icon: Code2, live: false },
    { href: "/dictionary/", labelKey: "dictionary", icon: ScrollText, live: false },
  ],
};

/** Visible only to ADMIN/SUPERADMIN (cosmetic only — the API enforces
 * roles). Live since phase 14 built these pages; the `(admin)` layout
 * itself re-checks the role and redirects a non-admin to `/studio/`. */
export const ADMIN_GROUP: NavGroup = {
  titleKey: "groupAdmin",
  items: [
    { href: "/admin/users/", labelKey: "adminUsers", icon: Users, live: true },
    { href: "/admin/dictionaries/", labelKey: "adminDictionaries", icon: ScrollText, live: true },
    { href: "/admin/voices/", labelKey: "adminVoices", icon: Volume2, live: true },
    { href: "/admin/audit-log/", labelKey: "adminAuditLog", icon: ShieldCheck, live: true },
  ],
};
