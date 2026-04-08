import type { ContentBlock } from "@/types/api";

/**
 * Extracts a string summary from a message's content, supporting multimodal (text, image, file).
 * - If text is present, returns the joined text.
 * - If not, returns a label for the first non-text modality (e.g., 'Image', 'Other').
 * - If unknown, returns 'Multimodal message'.
 */
export function getContentString(content: string | ContentBlock[] | undefined): string {
  if (typeof content === "string") return content;
  if (!content || !Array.isArray(content)) return "";

  const texts = content
    .filter((c): c is { type: "text"; text: string } => c.type === "text" && typeof c.text === "string")
    .map((c) => c.text);
  return texts.join(" ");
}
