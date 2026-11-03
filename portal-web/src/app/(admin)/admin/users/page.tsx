"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { AdminUsersTable } from "../../../../components/admin/admin-users-table";
import { useAdminUsersQuery } from "../../../../components/admin/admin-api-hooks";
import { CreateUserDialog } from "../../../../components/admin/create-user-dialog";
import { useI18n } from "../../../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../../../lib/i18n/messages-admin-en";

export default function AdminUsersListPage() {
  const router = useRouter();
  const { language } = useI18n();
  const t = getAdminMessages(language);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);

  const query = useAdminUsersQuery({ search, role, status, page });
  const data = query.data;
  const totalPages = data ? Math.max(1, Math.ceil(data.total_count / data.limit)) : 1;

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--color-text-primary)", margin: 0 }}>{t.users.title}</h1>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "4px 0 0" }}>{t.users.subtitle}</p>
        </div>
        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          style={{ background: "var(--color-accent)", color: "#fff", fontWeight: 700, border: "none", borderRadius: 8, padding: "8px 16px", cursor: "pointer" }}
        >
          {t.users.createButton}
        </button>
      </header>

      <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder={t.users.searchPlaceholder}
          style={{ flex: 1, minWidth: 240, height: 36, borderRadius: 8, border: "1px solid var(--color-border)", background: "var(--color-bg-secondary)", color: "var(--color-text-primary)", padding: "0 10px" }}
        />
        <select
          value={role}
          onChange={(e) => {
            setRole(e.target.value);
            setPage(1);
          }}
          style={{ height: 36, borderRadius: 8, border: "1px solid var(--color-border)", background: "var(--color-bg-secondary)", color: "var(--color-text-primary)" }}
        >
          <option value="">{t.users.roleFilterAll}</option>
          <option value="USER">USER</option>
          <option value="ADMIN">ADMIN</option>
          <option value="SUPERADMIN">SUPERADMIN</option>
        </select>
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
          style={{ height: 36, borderRadius: 8, border: "1px solid var(--color-border)", background: "var(--color-bg-secondary)", color: "var(--color-text-primary)" }}
        >
          <option value="">{t.users.statusFilterAll}</option>
          <option value="active">{t.users.statusActive}</option>
          <option value="inactive">{t.users.statusInactive}</option>
        </select>
      </div>

      <AdminUsersTable
        rows={data?.items ?? []}
        isLoading={query.isLoading}
        onOpen={(id) => router.push(`/admin/users/detail/?id=${id}`)}
      />

      {data && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12, fontSize: 13, color: "var(--color-text-secondary)" }}>
          <button type="button" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
            ←
          </button>
          <span>
            {data.page} / {totalPages}
          </span>
          <button type="button" onClick={() => setPage((p) => p + 1)} disabled={page >= totalPages}>
            →
          </button>
        </div>
      )}

      {createOpen && <CreateUserDialog onClose={() => setCreateOpen(false)} />}
    </div>
  );
}
