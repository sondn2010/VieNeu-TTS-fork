"use client";

import { useUserProfileQuery } from "../../lib/api/use-user-profile-query";
import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import type { AdminUserRow } from "./admin-api-hooks";

const ROLES = ["USER", "ADMIN", "SUPERADMIN"] as const;

export interface RoleSelectWithGuardsProps {
  target: AdminUserRow;
  onChange: (role: string) => void;
  disabled?: boolean;
}

/** Hidden entirely for a plain `ADMIN` actor (role changes are
 * `SUPERADMIN`-only — the API enforces this too, this is convenience
 * only); disabled when the actor is viewing their own account, since
 * self-demotion is always rejected server-side.
 */
export function RoleSelectWithGuards({ target, onChange, disabled }: RoleSelectWithGuardsProps) {
  const { language } = useI18n();
  const t = getAdminMessages(language);
  const { data: profile } = useUserProfileQuery();

  if (!profile || profile.role !== "SUPERADMIN") {
    return null;
  }

  const isSelf = profile.id === target.id;

  return (
    <label style={{ fontSize: 12, color: "var(--color-text-secondary)", display: "flex", flexDirection: "column", gap: 4 }}>
      {t.userDetail.roleLabel}
      <select value={target.role} disabled={disabled || isSelf} onChange={(e) => onChange(e.target.value)} style={{ padding: 8 }}>
        {ROLES.map((role) => (
          <option key={role} value={role}>
            {role}
          </option>
        ))}
      </select>
      {isSelf && <span style={{ fontSize: 11 }}>{t.userDetail.roleAdminOnlyHint}</span>}
    </label>
  );
}
