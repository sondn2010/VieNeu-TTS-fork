"use client";

import { Gauge } from "lucide-react";

/** Mirrors `SPEED_CHOICES` in `request_models_and_validation.py`. */
export const SPEED_CHOICES = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0] as const;

export interface SpeedSelectorProps {
  value: number;
  onChange: (value: number) => void;
}

export function SpeedSelector({ value, onChange }: SpeedSelectorProps) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--color-text-primary)" }}>
      <Gauge size={16} aria-hidden color="var(--color-text-secondary)" />
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ background: "#1a1a26", border: "1px solid #2e2e42", borderRadius: 6, color: "inherit", padding: "4px 6px" }}
      >
        {SPEED_CHOICES.map((speed) => (
          <option key={speed} value={speed}>
            {speed}x
          </option>
        ))}
      </select>
    </label>
  );
}
