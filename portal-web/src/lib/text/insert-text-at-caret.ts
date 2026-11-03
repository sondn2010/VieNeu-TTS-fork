/**
 * Caret-aware text insertion for the Studio editor's emotion-tag buttons
 * (TC-03): inserts at the current selection, replacing it when non-empty,
 * or at the end of the text when the editor isn't focused (`selectionStart`/
 * `selectionEnd` passed as `null`). Returns the caret position to restore
 * immediately after the inserted text.
 */
export interface CaretInsertionResult {
  text: string;
  caretPosition: number;
}

export function insertTextAtCaret(
  currentText: string,
  insertion: string,
  selectionStart: number | null,
  selectionEnd: number | null,
): CaretInsertionResult {
  const start = selectionStart ?? currentText.length;
  const end = selectionEnd ?? currentText.length;
  const text = currentText.slice(0, start) + insertion + currentText.slice(end);
  return { text, caretPosition: start + insertion.length };
}
