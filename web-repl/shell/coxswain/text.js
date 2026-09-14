// NFR-7 output encoding -- DOM-free cap-and-truncate plus the single
// set_text primitive every Coxswain renderer must route string writes
// through. Centralizing it here is what makes AC-15's structural grep
// meaningful rather than a per-file discipline.

/** NFR-7's stated maximums, mirrored kernel-side in records.STRING_CAPS. */
export const STRING_CAPS = Object.freeze({
  nl_restatement: 400,
  candidate_label: 120,
  warning_badge_text: 64,
  edited_field_value: 200,
  override_justification: 500,
  confirmation_phrase: 60,
});

/**
 * Truncate *value* to at most *cap* characters on a word boundary, suffixed
 * with an ellipsis. A string within the cap passes through unchanged; an
 * oversized string is NEVER rejected silently (NFR-7). Non-string input
 * degrades to "" rather than rendering something unreviewed.
 */
export function truncateText(value, cap) {
  if (typeof value !== "string") return "";
  if (!Number.isInteger(cap) || cap <= 0) return "";
  if (value.length <= cap) return value;
  let head = value.slice(0, Math.max(cap - 1, 0));
  const cut = head.lastIndexOf(" ");
  if (cut > 0) head = head.slice(0, cut);
  return head.replace(/\s+$/, "") + "…";
}

/** Cap by NFR-7 string class. Unknown classes throw: a silent uncapped write
 * is exactly what this module exists to prevent. */
export function capText(kind, value) {
  const cap = STRING_CAPS[kind];
  if (typeof cap !== "number") {
    throw new Error(`capText: unknown string-cap class "${kind}"`);
  }
  return truncateText(value, cap);
}

/**
 * The ONLY sanctioned way any renderer under shell/coxswain/ writes a string
 * into a DOM node (NFR-7: textContent, never markup). Full *untruncated*
 * value goes to node.title as a PROPERTY, so the complete text stays reachable.
 */
export function setText(node, s, { title = null } = {}) {
  node.textContent = typeof s === "string" ? s : "";
  const full = title === null ? node.textContent : title;
  if (full && "title" in node) {
    node.title = full;
  }
  return node;
}
