import { useEffect, useRef, useState } from "react";
import { TextInput } from "@mantine/core";

interface InlineEditProps {
  value: string;
  onSave: (value: string) => void;
  w?: number | string;
}

/**
 * Leichtgewichtiger Inline-Texteditor: speichert per Enter/Blur,
 * verwirft Änderungen per Escape. Sieht wie normaler Text aus.
 */
export function InlineEdit({ value, onSave, w }: InlineEditProps) {
  const [draft, setDraft] = useState(value);
  const committedRef = useRef(value); // zuletzt gespeicherter Wert (idempotent)
  const cancelRef = useRef(false); // Escape → Blur soll nicht speichern
  const ref = useRef<HTMLInputElement>(null);

  // Externe Änderungen (z. B. nach Refetch) übernehmen
  useEffect(() => {
    setDraft(value);
    committedRef.current = value;
  }, [value]);

  const commit = () => {
    if (cancelRef.current) {
      cancelRef.current = false;
      setDraft(committedRef.current);
      return;
    }
    const next = draft.trim();
    setDraft(next);
    if (next === committedRef.current) return;
    committedRef.current = next;
    onSave(next);
  };

  return (
    <TextInput
      ref={ref}
      value={draft}
      w={w}
      size="xs"
      variant="unstyled"
      aria-label="Kostenart"
      onChange={(e) => setDraft(e.currentTarget.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          commit();
          ref.current?.blur();
        } else if (e.key === "Escape") {
          cancelRef.current = true;
          setDraft(committedRef.current);
          ref.current?.blur();
        }
      }}
    />
  );
}
