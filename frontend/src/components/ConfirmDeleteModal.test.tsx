import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ConfirmDeleteModal } from "./ConfirmDeleteModal";

const renderModal = (overrides: Partial<Parameters<typeof ConfirmDeleteModal>[0]> = {}) => {
  const onConfirm = vi.fn();
  const onClose = vi.fn();
  render(
    <MantineProvider>
      <ConfirmDeleteModal
        opened
        message="Wirklich löschen?"
        confirmText="Testobjekt"
        onConfirm={onConfirm}
        onClose={onClose}
        {...overrides}
      />
    </MantineProvider>,
  );
  return { onConfirm, onClose };
};

describe("ConfirmDeleteModal", () => {
  it("hat den Löschen-Button initial deaktiviert", () => {
    renderModal();
    expect(screen.getByRole("button", { name: "Löschen" })).toBeDisabled();
  });

  it("bleibt bei falscher Eingabe deaktiviert und löscht nicht", async () => {
    const user = userEvent.setup();
    const { onConfirm } = renderModal();

    await user.type(screen.getByRole("textbox"), "Testobj");
    expect(screen.getByRole("button", { name: "Löschen" })).toBeDisabled();
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("aktiviert das Löschen erst bei exakt passender Eingabe", async () => {
    const user = userEvent.setup();
    const { onConfirm } = renderModal();

    await user.type(screen.getByRole("textbox"), "Testobjekt");
    const button = screen.getByRole("button", { name: "Löschen" });
    expect(button).toBeEnabled();

    await user.click(button);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("ruft beim Abbrechen nicht onConfirm auf", async () => {
    const user = userEvent.setup();
    const { onConfirm, onClose } = renderModal();

    await user.type(screen.getByRole("textbox"), "Testobjekt");
    await user.click(screen.getByRole("button", { name: "Abbrechen" }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});
