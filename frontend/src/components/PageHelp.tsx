import { useState } from "react";
import { ActionIcon, Tooltip } from "@mantine/core";
import HelpModal, { type HelpContent } from "./HelpModal";

/** „?“-Button neben dem Seitentitel, öffnet die Hilfe zu dieser Seite. */
export default function PageHelp({ content }: { content: HelpContent }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Tooltip label="Hilfe zu dieser Seite" withArrow>
        <ActionIcon variant="subtle" color="gray" size="lg" onClick={() => setOpen(true)} aria-label="Hilfe">
          ?
        </ActionIcon>
      </Tooltip>
      <HelpModal opened={open} onClose={() => setOpen(false)} content={content} />
    </>
  );
}
