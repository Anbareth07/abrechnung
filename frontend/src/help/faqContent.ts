/** Häufige Fragen (FAQ) – Frage + Antwort-Schritte für das Akkordeon. */

export interface FaqItem {
  question: string;
  answer: string[];
  /** Zielseite (Route) für einen direkten Link "wo muss ich etwas tun". */
  to?: { path: string; label: string };
  /** Weitere Zielseiten (optional, z. B. wenn eine Frage mehrere Seiten betrifft). */
  more?: { path: string; label: string }[];
}

export const faqItems: FaqItem[] = [
  {
    question: "Ich habe eine neue Stromrechnung. Was ist zu tun?",
    to: { path: "/strom", label: "Zur Strom-Seite" },
    answer: [
      "Die Stromrechnung wird NICHT über „Rechnungen“ erfasst, sondern über die Seite „Strom“.",
      "Öffne die Seite „Strom“ und wähle das Objekt.",
      "Lege die Zuordnung zur Abrechnung fest: eigene Zeile „Strom“ oder eine bestehende Kostenstelle (z. B. Hausbeleuchtung).",
      "Trage für den Zeitraum der Rechnung die Tarife ein: Grundgebühr (€/Jahr), Arbeitspreis (€/kWh) und Stromsteuer (€/kWh) – jeweils mit Zeitraum, Satz und MwSt (Standard 19 %).",
      "Erfasse die Zählerstände des Hauptzählers (Datum + Wert in kWh) – für den Rechnungszeitraum, idealerweise Jahresanfang und Jahresende.",
      "Optional: Unterzähler (z. B. Heizstrom) nur, wenn „Unterzähler berücksichtigen“ aktiv ist – der Verbrauch wird dann abgezogen.",
      "Bei Zählerwechsel: Stand als „Wert vor Zählerwechsel“ markieren und ggf. den Startwert des neuen Zählers angeben.",
      "Die Abrechnung berechnet die Stromkosten automatisch aus Tarifen und Verbrauch.",
    ],
  },
  {
    question: "Ich habe eine neue Wasserrechnung. Was ist zu tun?",
    to: { path: "/wasser", label: "Zur Wasser-Seite" },
    answer: [
      "Die Wasserrechnung wird NICHT über „Rechnungen“ erfasst, sondern über die Seite „Wasser“.",
      "Öffne die Seite „Wasser“ und wähle das Objekt.",
      "Lege je Art die Zuordnung zur Abrechnung fest: Trinkwasser, Schmutzwasser und Niederschlagswasser (jeweils eine bestehende Kostenstelle).",
      "Trage die Tarife ein: Trink-/Schmutzwasser (€/m³), Niederschlagswasser (€/m²/Jahr) und Grundgebühr (€/Jahr) – jeweils mit Zeitraum, Satz und MwSt.",
      "Erfasse die Zählerstände: Hauptzähler oder je Wohnung (Wohnungs-Wasserzähler, optional Waschmaschinen-Zähler).",
      "Bei Zählerwechsel: Stand als „Wert vor Zählerwechsel“ markieren und ggf. den Startwert des neuen Zählers angeben.",
      "Die Abrechnung berechnet die Wasserkosten automatisch aus Tarifen und Verbrauch.",
    ],
  },
  {
    question: "Ich habe eine neue Rechnung, z. B. Garten oder Versicherung. Was ist zu tun?",
    to: { path: "/rechnungen", label: "Zur Rechnungen-Seite" },
    answer: [
      "Solche Rechnungen gehören zu den „Rechnungen“.",
      "Öffne die Seite „Rechnungen“ und klicke „Neue Rechnung“.",
      "Wähle Objekt und Jahr (Standard: aktuelles Jahr).",
      "Wähle die passende Kostenstelle (z. B. Garten/Pflege oder Versicherung) – falls sie fehlt, lege sie in den Stammdaten unter Umlageschlüssel an.",
      "Gib einen Titel (z. B. „Gärtner 2025“ oder „Haftpflicht 2025“) und die Summe in € (brutto, inkl. MwSt) ein.",
      "Klicke „Speichern“ – die Rechnung fließt über den Umlageschlüssel der Kostenstelle in die Abrechnung des Jahres ein.",
      "Tipp: Für wiederkehrende Kosten (z. B. Versicherungen) die Rechnung per „Klonen“ ins Folgejahr übernehmen.",
    ],
  },
  {
    question: "Ich habe selbstabgelesene Zählerstände für Wasser und Strom. Was ist zu tun?",
    to: { path: "/strom", label: "Zur Strom-Seite" },
    more: [{ path: "/wasser", label: "Zur Wasser-Seite" }],
    answer: [
      "Zählerstände werden auf den jeweiligen Seiten erfasst – Strom und Wasser getrennt.",
      "Strom: Öffne die Seite „Strom“ und erfasse die Zählerstände des Hauptzählers (Datum + Wert in kWh).",
      "Wasser: Öffne die Seite „Wasser“ und erfasse die Zählerstände (Hauptzähler oder je Wohnung: Wohnungs-Wasserzähler, ggf. Waschmaschinen-Zähler).",
      "Trage für jeden Stand Datum und Wert ein – idealerweise Jahresanfang und Jahresende, damit der Verbrauch in die Abrechnung einfließt.",
      "Bei Zählerwechsel: Stand als „Wert vor Zählerwechsel“ markieren und ggf. den Startwert des neuen Zählers angeben.",
      "Die Abrechnung berechnet den Verbrauch automatisch aus den Differenzen der Zählerstände.",
    ],
  },
  {
    question: "Ich habe eine neue Gasrechnung. Was ist zu tun?",
    to: { path: "/techem", label: "Zur Techem-Seite" },
    answer: [
      "Die Gasrechnung gehört zu den Heizkosten und wird über die Seite „Techem“ erfasst.",
      "Öffne die Seite „Techem“ und wähle das Objekt.",
      "Wähle den Zeitraum (Heizperiode, Standard: 01.07. – 30.06. des Folgejahres).",
      "Trage bei Gas die verbrauchte Menge (kWh) und die Kosten (€) ein – sowie ggf. Wartung Heizung und Kaminfeger.",
      "Speichere – der Zeitraum erscheint unter „Gespeicherte Zeiträume“.",
      "Hinweis: Die Techem-/Heizkosten-Daten fließen NICHT in die Mieter-Abrechnung ein.",
    ],
  },
  {
    question: "Ich habe eine Rückerstattung/Gutschrift (z. B. Strompreisbremse). Wie trage ich sie ein?",
    to: { path: "/rechnungen", label: "Zur Rechnungen-Seite" },
    answer: [
      "Öffne die Seite „Rechnungen“ und klicke „Neue Rechnung“.",
      "Wähle Objekt, Jahr und die passende Kostenstelle.",
      "Gib bei der Summe einen negativen Betrag ein (z. B. -200,00) – der Hinweis „Gutschrift/Erstattung“ erscheint.",
      "Speichere – die Abrechnung verrechnet die Gutschrift automatisch: Sie verringert die Kosten der Kostenstelle bzw. ergibt eine Erstattung.",
    ],
  },
  {
    question: "Wie erstelle ich die Jahresabrechnung?",
    to: { path: "/abrechnung", label: "Zur Abrechnung" },
    answer: [
      "Öffne die Seite „Abrechnung“ und wähle Objekt und Jahr (Standard: Vorjahr).",
      "Beachte die Hinweise (z. B. „Noch fehlende Daten“ oder Warnungen zu fehlenden Rechnungen/Zählerständen).",
      "Prüfe je Mieter die Kostenstellen – über „?“ auf den Beträgen siehst du die Berechnung.",
      "Klicke „Abrechnung finalisieren“, um den Stand einzufrieren.",
      "Lade je Mieter das PDF herunter (Button „PDF“) oder exportiere alles als Excel.",
    ],
  },
  {
    question: "Wo trage ich die Zählerstände zu Ein-/Auszug ein?",
    to: { path: "/wasser", label: "Zur Wasser-Seite" },
    answer: [
      "Bei Wohnungs-Wasserzählern: Öffne die Seite „Wasser“ → Zählerstände der betroffenen Wohnung.",
      "Erfasse den Stand zum Auszug des alten und zum Einzug des neuen Mieters (Datum + Wert).",
      "Fehlt ein Stand, weist die Abrechnung darauf hin und der Verbrauch kann nicht exakt aufgeteilt werden.",
      "Bei Zählerwechseln: Stand als „Wert vor Zählerwechsel“ markieren und ggf. den Startwert des neuen Zählers angeben.",
    ],
  },
  {
    question: "Was bedeutet „Keine Rechnung dieses Jahr“?",
    to: { path: "/abrechnung", label: "Zur Abrechnung" },
    answer: [
      "Wenn für eine Kostenstelle in einem Jahr keine Rechnung vorliegt, kannst du das in der Abrechnung markieren.",
      "Die Kostenstelle erscheint dann in der Abrechnung mit 0 €, statt als fehlend gemeldet zu werden.",
      "Das ist z. B. sinnvoll, wenn eine Kostenart nicht jedes Jahr anfällt – etwa der Legionellen-Test, der nur alle paar Jahre durchgeführt wird.",
    ],
  },
  {
    question: "Was macht die Schaltfläche „Klonen“ bei Rechnungen?",
    to: { path: "/rechnungen", label: "Zur Rechnungen-Seite" },
    answer: [
      "„Klonen“ legt eine Kopie der Rechnung für das Folgejahr an.",
      "Die Felder (Kostenstelle, Titel, Summe) sind bereits vorbelegt – du musst sie nur noch prüfen und speichern.",
      "Ideal für wiederkehrende Kosten wie Versicherungen, Grundsteuer oder Wartungsverträge.",
    ],
  },
  {
    question: "Was ist „Restwasser (Leerstand)“ in der Abrechnung?",
    to: { path: "/abrechnung", label: "Zur Abrechnung" },
    answer: [
      "Wenn die Summe der verbrauchsabhängigen Wasseranteile der Mieter nicht der gesamten Wassermenge entspricht, bleibt ein Rest übrig.",
      "Das passiert z. B. bei Leerstand oder wenn Zählerstände fehlen.",
      "Der nicht umgelegte Betrag wird in der Abrechnung als Hinweis ausgewiesen.",
    ],
  },
  {
    question: "Wo finde ich die PDFs der Mieterabrechnung?",
    to: { path: "/abrechnung", label: "Zur Abrechnung" },
    answer: [
      "Auf der Seite „Abrechnung“ nach der Finalisierung: Je Mieter gibt es einen „PDF“-Button.",
      "Das PDF zeigt die Kostenstellen mit Gesamtkosten, Verteilerschlüssel, Ihrem Anteil und dem Saldo (Nachzahlung/Gutschrift).",
      "Alternativ exportiert „Excel“ die gesamte Jahresabrechnung als Arbeitsmappe.",
    ],
  },
];
