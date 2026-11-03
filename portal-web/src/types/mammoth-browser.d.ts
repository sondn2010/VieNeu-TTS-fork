/** `mammoth` ships no types for its browser entry point. */
declare module "mammoth/mammoth.browser" {
  export function extractRawText(input: { arrayBuffer: ArrayBuffer }): Promise<{ value: string; messages: unknown[] }>;
}
