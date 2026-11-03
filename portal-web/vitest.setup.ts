import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

import "@testing-library/jest-dom/vitest";

afterEach(() => {
  cleanup();
});

// jsdom's Blob/File implementation does not provide `.text()`/`.arrayBuffer()`
// (real browsers do) — polyfilled via `FileReader`, which jsdom does
// implement, purely so file-import tests can exercise production code
// unchanged.
if (typeof Blob !== "undefined" && typeof Blob.prototype.text !== "function") {
  Blob.prototype.text = function (): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(reader.error);
      reader.readAsText(this);
    });
  };
}
if (typeof Blob !== "undefined" && typeof Blob.prototype.arrayBuffer !== "function") {
  Blob.prototype.arrayBuffer = function (): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as ArrayBuffer);
      reader.onerror = () => reject(reader.error);
      reader.readAsArrayBuffer(this);
    });
  };
}
