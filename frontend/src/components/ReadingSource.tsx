import { Badge } from "@mantine/core";

/** Herkunft eines Zählerstands: "RECHNUNG" (vom Versorger übermittelt) | "ABLESUNG" (selbst abgelesen). */
export const READING_SOURCE_LABELS: Record<string, string> = {
  RECHNUNG: "Rechnung",
  ABLESUNG: "Ablesung",
};

/** Optionen für die Auswahl im Zählerstand-Dialog (Standard: Rechnung). */
export const READING_SOURCE_OPTIONS = [
  { value: "RECHNUNG", label: "Rechnung" },
  { value: "ABLESUNG", label: "Ablesung" },
];

/** Kleines Badge mit der Herkunft (Rechnung = grau, Ablesung = teal). */
export default function ReadingSource({ source }: { source?: string | null }) {
  const isAblesung = source === "ABLESUNG";
  const label = READING_SOURCE_LABELS[source ?? "RECHNUNG"] ?? source ?? "Rechnung";
  return (
    <Badge size="xs" variant="light" color={isAblesung ? "teal" : "gray"}>
      {label}
    </Badge>
  );
}
