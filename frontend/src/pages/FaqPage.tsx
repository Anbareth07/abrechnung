import { useEffect, useLayoutEffect, useState } from "react";
import { Accordion, Button, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";
import { faqItems } from "../help/faqContent";

const OPEN_KEY = "abrechnung.faq.open";
const SCROLL_KEY = "abrechnung.faq.scrollY";

function loadOpen(): string | null {
  try {
    return sessionStorage.getItem(OPEN_KEY);
  } catch {
    return null;
  }
}

/**
 * FAQ-Seite: Fragen als Akkordeon – Klick auf eine Frage klappt die
 * Antwort mit den passenden Hilfeschritten auf. Jede Antwort bietet
 * einen direkten Link zur Seite, auf der die Aktion stattfindet.
 *
 * Aufgeklappte Fragen und die Scroll-Position werden in sessionStorage
 * gemerkt, sodass man nach einem Klick auf einen Link und dem
 * Zurücknavigieren den vorherigen Stand wieder vorfindet.
 */
export default function FaqPage() {
  const [open, setOpen] = useState<string | null>(loadOpen);

  const handleChange = (value: string | null) => {
    setOpen(value);
    try {
      if (value == null) sessionStorage.removeItem(OPEN_KEY);
      else sessionStorage.setItem(OPEN_KEY, value);
    } catch {
      /* sessionStorage nicht verfügbar – ignorieren */
    }
  };

  // Scroll-Position beim Verlassen merken
  useEffect(() => {
    return () => {
      try {
        sessionStorage.setItem(SCROLL_KEY, String(window.scrollY));
      } catch {
        /* ignorieren */
      }
    };
  }, []);

  // Scroll-Position nach dem Zurückkehren wiederherstellen
  useLayoutEffect(() => {
    const raw = sessionStorage.getItem(SCROLL_KEY);
    if (raw == null) return;
    const y = Number(raw);
    const frame = requestAnimationFrame(() => window.scrollTo(0, y));
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <Stack gap="md">
      <Title order={2}>Häufige Fragen</Title>
      <Text size="sm" c="dimmed">
        Klicke auf eine Frage, um die Antwort zu sehen.
      </Text>
      <Accordion
        variant="separated"
        keepMounted={false}
        transitionDuration={0}
        value={open}
        onChange={handleChange}
      >
        {faqItems.map((item, i) => (
          <Accordion.Item key={i} value={String(i)}>
            <Accordion.Control>{item.question}</Accordion.Control>
            <Accordion.Panel>
              <Stack gap={6} pt="xs">
                {item.answer.map((line, j) => (
                  <Text key={j} size="sm" style={{ lineHeight: 1.7 }}>
                    • {line}
                  </Text>
                ))}
                {item.to && (
                  <Button
                    component={Link}
                    to={item.to.path}
                    variant="light"
                    size="compact-sm"
                    mt="sm"
                    w="fit-content"
                  >
                    {item.to.label} →
                  </Button>
                )}
                {item.more?.map((m, k) => (
                  <Button
                    key={k}
                    component={Link}
                    to={m.path}
                    variant="light"
                    size="compact-sm"
                    mt="sm"
                    w="fit-content"
                  >
                    {m.label} →
                  </Button>
                ))}
              </Stack>
            </Accordion.Panel>
          </Accordion.Item>
        ))}
      </Accordion>
    </Stack>
  );
}
