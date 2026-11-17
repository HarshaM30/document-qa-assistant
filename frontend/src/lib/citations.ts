/** Human-readable source location, e.g. "Item 7, p. 32" or "pp. 2–3". */
export function locationLabel(c: {
  item_code: string | null
  section_title: string
  page_start: number | null
  page_end: number | null
}): string {
  const parts: string[] = []
  if (c.item_code) parts.push(`Item ${c.item_code}`)
  // PDF sections are titled "Page N"; the page number below already says that.
  else if (c.section_title && !(c.page_start !== null && /^Page \d+$/.test(c.section_title)))
    parts.push(c.section_title)
  if (c.page_start !== null) {
    parts.push(
      c.page_end !== null && c.page_end !== c.page_start
        ? `pp. ${c.page_start}–${c.page_end}`
        : `p. ${c.page_start}`,
    )
  }
  return parts.join(', ')
}
