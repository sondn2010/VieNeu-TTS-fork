import { describe, expect, it, vi } from "vitest";

vi.mock("mammoth/mammoth.browser", () => ({
  extractRawText: vi.fn(async () => ({ value: "văn bản từ docx" })),
}));

import {
  ImportFileTooLargeError,
  MAX_IMPORT_FILE_BYTES,
  UnsupportedImportFileError,
  importTextFromFile,
  stripSrtMarkup,
} from "./text-file-import";

function makeFile(name: string, content: string, type = "text/plain"): File {
  return new File([content], name, { type });
}

describe("stripSrtMarkup", () => {
  it("removes cue index and timing lines, keeping the dialogue text", () => {
    const srt = [
      "1",
      "00:00:01,000 --> 00:00:03,500",
      "Xin chào các bạn.",
      "",
      "2",
      "00:00:03,600 --> 00:00:05,000",
      "Hôm nay chúng ta học TTS.",
    ].join("\n");
    expect(stripSrtMarkup(srt)).toBe("Xin chào các bạn.\n\nHôm nay chúng ta học TTS.");
  });
});

describe("importTextFromFile", () => {
  it("returns .txt content verbatim (trimmed)", async () => {
    const file = makeFile("note.txt", "  hello world  \n");
    await expect(importTextFromFile(file)).resolves.toBe("hello world");
  });

  it("strips .srt markup", async () => {
    const file = makeFile("captions.srt", "1\n00:00:01,000 --> 00:00:02,000\nXin chào\n");
    await expect(importTextFromFile(file)).resolves.toBe("Xin chào");
  });

  it("extracts text from .docx via mammoth", async () => {
    const file = makeFile("doc.docx", "ignored binary content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
    await expect(importTextFromFile(file)).resolves.toBe("văn bản từ docx");
  });

  it("rejects a file over the 2 MB limit", async () => {
    const big = new File([new Uint8Array(MAX_IMPORT_FILE_BYTES + 1)], "big.txt");
    await expect(importTextFromFile(big)).rejects.toBeInstanceOf(ImportFileTooLargeError);
  });

  it("rejects an unsupported file extension", async () => {
    const file = makeFile("audio.mp3", "not text");
    await expect(importTextFromFile(file)).rejects.toBeInstanceOf(UnsupportedImportFileError);
  });
});
