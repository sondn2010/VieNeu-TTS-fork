/** Vietnamese-locale number/date formatting (the token widget: `140.574 / 150.000`). */

export function formatVietnameseNumber(value: number): string {
  return new Intl.NumberFormat("vi-VN").format(Math.trunc(value));
}

export function formatTokenBalance(balance: number, quota: number): string {
  return `${formatVietnameseNumber(balance)} / ${formatVietnameseNumber(quota)}`;
}

export function formatVietnameseDate(isoDate: string | Date): string {
  const date = typeof isoDate === "string" ? new Date(isoDate) : isoDate;
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium" }).format(date);
}

/** `HH:mm DD/MM/YYYY` — the recording-card timestamp format (spec 02/04). */
export function formatRecordingTimestamp(isoDate: string | Date): string {
  const date = typeof isoDate === "string" ? new Date(isoDate) : isoDate;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getHours())}:${pad(date.getMinutes())} ${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()}`;
}
