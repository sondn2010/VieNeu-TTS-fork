import { ApiError } from "../../lib/api/api-error";
import type { AdminMessages } from "../../lib/i18n/messages-admin-vi";

/** Maps the admin guard error codes (phase 13's `role_change_guards.py` and
 * `user_account_admin_service.py`) to localized messages shared by every
 * admin mutation that can hit them. */
export function mapAdminGuardError(err: unknown, t: AdminMessages): string {
  if (!(err instanceof ApiError)) return t.guard.genericError;
  switch (err.code) {
    case "FORBIDDEN_ROLE":
      return t.guard.forbiddenRole;
    case "LAST_SUPERADMIN":
      return t.guard.lastSuperadmin;
    case "SELF_MODIFICATION":
      return t.guard.selfModification;
    case "EMAIL_TAKEN":
      return t.guard.emailTaken;
    default:
      return err.message || t.guard.genericError;
  }
}
