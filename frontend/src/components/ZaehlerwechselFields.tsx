import { Button, Checkbox, NumberInput, Stack } from "@mantine/core";

/**
 * Zählerwechsel-Felder für Zählerstandseingaben: „Wert vor Zählerwechsel" +
 * „Startwert des neuen Zählers" (Standard 0).
 * Die Checkbox erscheint nur, solange der Stand NICHT als Zählerwechsel markiert
 * ist; danach wird nur noch der Startwert angezeigt (mit „rückgängig"-Option).
 */
export default function ZaehlerwechselFields({
  vor,
  start,
  onVor,
  onStart,
}: {
  vor: boolean;
  start: string;
  onVor: (v: boolean) => void;
  onStart: (v: string) => void;
}) {
  if (!vor) {
    return (
      <Checkbox label="Wert vor Zählerwechsel" checked={vor} onChange={(e) => onVor(e.currentTarget.checked)} />
    );
  }
  return (
    <Stack gap="xs">
      <NumberInput
        label="Startwert des neuen Zählers"
        value={start === "" ? "" : Number(start)}
        onChange={(v) => onStart(String(v ?? ""))}
        decimalScale={4}
        min={0}
      />
      <Button size="compact-xs" variant="subtle" color="gray" onClick={() => onVor(false)}>
        Zählerwechsel rückgängig machen
      </Button>
    </Stack>
  );
}
