import { Stack, Text, Title } from "@mantine/core";
import type { HelpContent } from "../components/HelpModal";

/**
 * Anleitungsseite: zeigt einen Anleitungs-Inhalt als dedizierte Seite
 * (statt als Overlay-Dialog) – gleiches Layout wie die übrigen Seiten.
 */
export default function HelpPage({ content }: { content: HelpContent }) {
  return (
    <Stack gap="md">
      <Title order={2}>{content.title ?? "Anleitung"}</Title>
      {content.intro && (
        <Text size="sm" c="dimmed">
          {content.intro}
        </Text>
      )}
      {content.sections.map((s, i) => (
        <Stack key={i} gap={6}>
          {s.heading && (
            <Text fw={600} size="md" mt={i > 0 ? "sm" : 0}>
              {s.heading}
            </Text>
          )}
          {s.items.map((it, j) => (
            <Text key={j} size="sm" style={{ lineHeight: 1.7 }}>
              • {it}
            </Text>
          ))}
        </Stack>
      ))}
    </Stack>
  );
}
