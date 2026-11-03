/**
 * Loads editor text from an uploaded/dropped file: `.txt` verbatim, `.srt`
 * with cue index/timing lines stripped, `.docx` via `mammoth` (browser
 * build — runs entirely client-side, never uploaded anywhere).
 */
import * as mammoth from "mammoth/mammoth.browser";

export const MAX_IMPORT_FILE_BYTES = 2 * 1024 * 1024;

export class ImportFileTooLargeError extends Error {}
export class UnsupportedImportFileError extends Error {}

const SRT_CUE_INDEX = /^\d+$/;
const SRT_TIMING = /^\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}/;

export function stripSrtMarkup(raw: string): string {
  return raw
    .split(/\r?\n/)
    .filter((line) => !SRT_CUE_INDEX.test(line.trim()) && !SRT_TIMING.test(line.trim()))
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export async function importTextFromFile(file: File): Promise<string> {
  if (file.size > MAX_IMPORT_FILE_BYTES) {
    throw new ImportFileTooLargeError(`${file.name} exceeds the 2 MB import limit`);
  }
  const name = file.name.toLowerCase();
  if (name.endsWith(".docx")) {
    const arrayBuffer = await file.arrayBuffer();
    const result = await mammoth.extractRawText({ arrayBuffer });
    return result.value.trim();
  }
  const text = await file.text();
  if (name.endsWith(".srt")) {
    return stripSrtMarkup(text);
  }
  if (name.endsWith(".txt")) {
    return text.trim();
  }
  throw new UnsupportedImportFileError(`unsupported file type: ${file.name}`);
}
