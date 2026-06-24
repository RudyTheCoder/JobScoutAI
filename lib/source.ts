const SOURCE_LABELS: Record<string, string> = {
  fixture: "Fixture",
  demo_fixture: "Fixture",
  "generic/html": "Generic HTML",
  generic: "Generic HTML",
  generic_html: "Generic HTML",
  greenhouse: "Greenhouse",
  lever: "Lever",
  ashby: "Ashby",
  playwright: "JavaScript fixture",
  paginated_fixture: "Paginated fixture",
  detail_fixture: "Detail fixture",
};

export function sourceLabel(value: string | null | undefined) {
  if (!value) return "Unknown";
  return SOURCE_LABELS[value] ?? value.replace(/_/g, " ");
}
