"use client";

import { useState } from "react";

import { AuditLogTable } from "../../../../components/admin/audit-log-table";
import { useAdminAuditLogQuery } from "../../../../components/admin/admin-api-hooks";
import { useI18n } from "../../../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../../../lib/i18n/messages-admin-en";

export default function AdminAuditLogPage() {
  const { language } = useI18n();
  const t = getAdminMessages(language);
  const [actor, setActor] = useState("");
  const [action, setAction] = useState("");
  const [targetType, setTargetType] = useState("");
  const [targetId, setTargetId] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(1);

  const query = useAdminAuditLogQuery({ actor, action, targetType, targetId, from, to, page });
  const data = query.data;
  const totalPages = data ? Math.max(1, Math.ceil(data.total_count / data.limit)) : 1;

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}>
      <header style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--color-text-primary)", margin: 0 }}>{t.auditLog.title}</h1>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)", margin: "4px 0 0" }}>{t.auditLog.subtitle}</p>
      </header>

      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", fontSize: 12 }}>
        <input value={actor} onChange={(e) => { setActor(e.target.value); setPage(1); }} placeholder={t.auditLog.actorFilterPlaceholder} style={{ padding: 6 }} />
        <input value={action} onChange={(e) => { setAction(e.target.value); setPage(1); }} placeholder={t.auditLog.actionFilterPlaceholder} style={{ padding: 6 }} />
        <input value={targetType} onChange={(e) => { setTargetType(e.target.value); setPage(1); }} placeholder={t.auditLog.targetTypeFilterPlaceholder} style={{ padding: 6 }} />
        <input value={targetId} onChange={(e) => { setTargetId(e.target.value); setPage(1); }} placeholder={t.auditLog.targetIdFilterPlaceholder} style={{ padding: 6 }} />
        <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
          {t.auditLog.fromLabel}
          <input type="date" value={from} onChange={(e) => { setFrom(e.target.value); setPage(1); }} />
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
          {t.auditLog.toLabel}
          <input type="date" value={to} onChange={(e) => { setTo(e.target.value); setPage(1); }} />
        </label>
      </div>

      <AuditLogTable rows={data?.items ?? []} isLoading={query.isLoading} />

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
    </div>
  );
}
