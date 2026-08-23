import { Button, Group, Modal, Stack, Text, TextInput } from "@mantine/core";
import { useState } from "react";

interface ConfirmDeleteModalProps {
  opened: boolean;
  title?: string;
  message: string;
  /** Text, der zum Bestätigen exakt eingetippt werden muss. */
  confirmText: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onClose: () => void;
}

/**
 * Lösch-Bestätigung mit Texteingabe: Das Löschen ist erst möglich, wenn der
 * Anzeigename exakt eingetippt wurde – verhindert versehentliches Klicken.
 */
export function ConfirmDeleteModal({
  opened,
  title = "Wirklich löschen?",
  message,
  confirmText,
  confirmLabel = "Löschen",
  onConfirm,
  onClose,
}: ConfirmDeleteModalProps) {
  const [input, setInput] = useState("");
  const match = input.trim() === confirmText;

  const close = () => {
    setInput("");
    onClose();
  };
  const confirm = () => {
    if (!match) return;
    setInput("");
    onConfirm();
  };

  return (
    <Modal opened={opened} onClose={close} title={title}>
      <Stack>
        <Text size="sm">{message}</Text>
        <Text size="sm" c="dimmed">
          Zur Bestätigung bitte exakt eingeben: <b>{confirmText}</b>
        </Text>
        <TextInput
          value={input}
          onChange={(e) => setInput(e.currentTarget.value)}
          placeholder={confirmText}
          data-autofocus
        />
        <Group justify="flex-end">
          <Button variant="light" onClick={close}>
            Abbrechen
          </Button>
          <Button color="red" disabled={!match} onClick={confirm}>
            {confirmLabel}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
