import { Modal, Stack, Text } from "@mantine/core";

export interface HelpSection {
  heading?: string;
  items: string[];
}

export interface HelpContent {
  title?: string;
  intro?: string;
  sections: HelpSection[];
}

/** Wiederverwendbarer Hilfedialog: erklärt je Seite, was zu tun ist. */
export default function HelpModal({
  opened,
  onClose,
  content,
}: {
  opened: boolean;
  onClose: () => void;
  content: HelpContent;
}) {
  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={content.title ?? "Hilfe"}
      // Breite dynamisch zur Browserbreite: bei breiten Fenstern weniger Zeilenumbrüche
      size="min(90vw, 1100px)"
    >
      <Stack gap="md">
        {content.intro && <Text size="sm">{content.intro}</Text>}
        {content.sections.map((s, i) => (
          <Stack key={i} gap={4}>
            {s.heading && (
              <Text fw={600} size="sm">
                {s.heading}
              </Text>
            )}
            {s.items.map((it, j) => (
              <Text key={j} size="sm" style={{ lineHeight: 1.6 }}>
                • {it}
              </Text>
            ))}
          </Stack>
        ))}
      </Stack>
    </Modal>
  );
}
