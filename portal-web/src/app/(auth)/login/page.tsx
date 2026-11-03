"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { apiFetch } from "../../../lib/api/api-client-with-csrf";
import { ApiError } from "../../../lib/api/api-error";
import { USER_PROFILE_QUERY_KEY } from "../../../lib/api/use-user-profile-query";
import { useI18n } from "../../../lib/i18n/i18n-provider";

export default function LoginPage() {
  const { messages } = useI18n();
  const t = messages.auth;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await apiFetch("/api/v1/auth/login", { method: "POST", body: { email, password } });
      await queryClient.invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY });
      router.replace("/studio/");
    } catch (err) {
      if (err instanceof ApiError && err.code === "INVALID_CREDENTIALS") {
        setError(t.invalidCredentials);
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(t.genericError);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <form onSubmit={handleSubmit} style={{ width: 320, display: "flex", flexDirection: "column", gap: 12 }}>
        <h1 style={{ fontSize: 20, margin: 0, color: "var(--color-text-primary)" }}>{t.loginTitle}</h1>
        <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
          {t.emailLabel}
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ width: "100%", padding: 8, marginTop: 4 }}
          />
        </label>
        <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
          {t.passwordLabel}
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ width: "100%", padding: 8, marginTop: 4 }}
          />
        </label>
        {error && <p style={{ color: "var(--color-danger-text)", fontSize: 13, margin: 0 }}>{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          style={{
            background: "var(--color-accent)", color: "#fff", border: "none", borderRadius: 8,
            padding: "10px 0", fontWeight: 700, cursor: submitting ? "not-allowed" : "pointer",
          }}
        >
          {t.loginButton}
        </button>
        <Link href="/signup/" style={{ fontSize: 13, color: "var(--color-text-secondary)", textAlign: "center" }}>
          {t.goToSignup}
        </Link>
      </form>
    </main>
  );
}
