import { describe, expect, it } from "vitest";

import { insertTextAtCaret } from "./insert-text-at-caret";

describe("insertTextAtCaret", () => {
  it("inserts in the middle of a sentence at the given caret position", () => {
    const result = insertTextAtCaret("Xin chao ban", "[cười] ", 3, 3);
    expect(result.text).toBe("Xin[cười]  chao ban");
    expect(result.caretPosition).toBe(3 + "[cười] ".length);
  });

  it("inserts at the end when the editor is not focused (selection null)", () => {
    const result = insertTextAtCaret("Xin chao", "[thở dài] ", null, null);
    expect(result.text).toBe("Xin chao[thở dài] ");
    expect(result.caretPosition).toBe(result.text.length);
  });

  it("replaces a non-empty selection instead of inserting inside it", () => {
    // "Xin chao ban": selecting [4, 9) covers "chao " (including the
    // trailing space), so the tag's own trailing space is the only one left.
    const result = insertTextAtCaret("Xin chao ban", "[hắng giọng] ", 4, 9);
    expect(result.text).toBe("Xin [hắng giọng] ban");
    expect(result.caretPosition).toBe(4 + "[hắng giọng] ".length);
  });

  it("inserts into an empty text", () => {
    const result = insertTextAtCaret("", "[cười] ", null, null);
    expect(result.text).toBe("[cười] ");
    expect(result.caretPosition).toBe("[cười] ".length);
  });
});
