import type { HelpContent } from "../components/HelpModal";

export const stammdatenHelp: HelpContent = {
  title: "Stammdaten",
  intro: "Grunddaten der Objekte pflegen – die Basis für alle weiteren Module.",
  sections: [
    {
      heading: "Objekte",
      items: [
        "Objekte anlegen/ändern (Name, Adresse).",
        "Versiegelte Fläche (m²) angeben – Berechnungsgrundlage für Niederschlagswasser (€/m²/Jahr).",
        "Testobjekte markieren, um sie in Listen und Dropdowns ausblenden zu können (Schalter oben rechts).",
      ],
    },
    {
      heading: "Mieteinheiten",
      items: [
        "Je Objekt die Wohnungen/Einheiten mit Wohnfläche (WF) und Extrafläche anlegen.",
        "Die Nutzfläche (NF) wird automatisch als WF + Extra berechnet.",
      ],
    },
    {
      heading: "Mieter",
      items: [
        "Mieter je Einheit mit Einzug/Auszug und monatlicher Vorauszahlung anlegen.",
        "Vorauszahlungs-Zeiträume: Änderungen werden automatisch auf den Monatsanfang gesetzt (z. B. 01.07.).",
        "Bei Auszug/Mieterwechsel werden die Zeiträume anteilig berechnet.",
      ],
    },
    {
      heading: "Umlageschlüssel",
      items: [
        "Je Objekt die Kostenarten mit Verteilerschlüssel festlegen: Wohnfläche, Nutzfläche, Verbrauch, Wohnung (1:1) oder nicht umgelegt.",
        "Die Reihenfolge (▲▼) bestimmt die Reihenfolge der Kostenstellen in der Abrechnung.",
        "Kostenarten lassen sich direkt in der Tabelle umbenennen (Enter speichert).",
      ],
    },
  ],
};

export const rechnungenHelp: HelpContent = {
  title: "Rechnungen",
  intro: "Objektweite Kosten je Jahr erfassen – sie fließen über den Umlageschlüssel in die Abrechnung.",
  sections: [
    {
      heading: "Wiederkehrende Aufgabe: Rechnung erfassen",
      items: [
        "„Neue Rechnung“ → Objekt, Jahr, Kostenstelle, Titel und Summe angeben.",
        "Kostenstelle „Wohnung“ verlangt zusätzlich die Auswahl der betroffenen Wohnung (je-Wohnung-Kosten).",
        "Mit „Dialog offen lassen“ kannst du mehrere Rechnungen in Folge erfassen.",
      ],
    },
    {
      heading: "Tipps",
      items: [
        "„Klonen“ legt eine Rechnung für das Folgejahr mit vorbelegten Feldern an – ideal für wiederkehrende Kosten (z. B. Versicherungen).",
        "Fehlt eine Rechnung in einem Jahr, kannst du sie in der Abrechnung als „Keine Rechnung dieses Jahr“ markieren.",
        "Rechnungen werden je Objekt und Jahr gruppiert angezeigt.",
      ],
    },
  ],
};

export const stromHelp: HelpContent = {
  title: "Strom",
  intro: "Stromkosten erfassen und an die Abrechnung anbinden (Hauptzähler + optionaler Unterzähler).",
  sections: [
    {
      heading: "1. Zuordnung zur Abrechnung",
      items: [
        "Lege fest, wohin die Stromkosten fließen: eigene Zeile „Strom“ oder in eine bestehende Kostenstelle (z. B. Hausbeleuchtung).",
      ],
    },
    {
      heading: "2. Tarif",
      items: [
        "Je Art (Grundgebühr €/Jahr, Arbeitspreis €/kWh, Stromsteuer €/kWh) Zeiträume mit Satz und MwSt erfassen.",
        "MwSt-Standard ist 19 %; bei abweichenden Sätzen anpassen.",
      ],
    },
    {
      heading: "3. Zählerstände",
      items: [
        "Hauptzähler-Stände erfassen (Datum + Wert in kWh).",
        "Unterzähler (z. B. Heizstrom) nur, wenn „Unterzähler berücksichtigen“ aktiv ist – der Verbrauch wird dann abgezogen.",
        "Zählerwechsel: Stand als „Wert vor Zählerwechsel“ markieren und ggf. den Startwert des neuen Zählers angeben.",
      ],
    },
  ],
};

export const wasserHelp: HelpContent = {
  title: "Wasser",
  intro: "Wasser-/Abwasserkosten erfassen und an die Abrechnung anbinden (Hauptzähler oder Wohnungszähler).",
  sections: [
    {
      heading: "1. Zuordnung zur Abrechnung",
      items: [
        "Wähle je Art (Trinkwasser, Schmutzwasser, Niederschlagswasser) die bestehende Kostenstelle in der Abrechnung.",
        "Ist eine Kostenstelle mit „Verbrauch“ zugeordnet, wird automatisch mit den Wohnungszählern gerechnet, sonst mit dem Hauptzähler.",
      ],
    },
    {
      heading: "2. Tarif",
      items: [
        "Je Art Zeiträume erfassen: Trink-/Schmutzwasser €/m³, Niederschlagswasser €/m²/Jahr, Grundgebühr €/Jahr.",
        "MwSt-Standards: Trinkwasser und Grundgebühr 7 %, Schmutzwasser und Niederschlagswasser 0 %.",
      ],
    },
    {
      heading: "3. Zählerstände & Optionen",
      items: [
        "Hauptzähler oder je Wohnung 2 Zähler – Wohnung + Waschmaschine (letzteres, wenn eine Kostenstelle mit „Verbrauch“ zugeordnet ist).",
        "„Waschmaschinen-Zähler berücksichtigen“: deaktiviert, wenn nur die Wohnungs-Wasserzähler zählen sollen.",
        "Zählerwechsel: Stand als „Wert vor Zählerwechsel“ markieren und ggf. Startwert des neuen Zählers angeben.",
      ],
    },
  ],
};

export const abrechnungHelp: HelpContent = {
  title: "Abrechnung",
  intro: "Die Jahresabrechnung je Objekt – Vollständigkeit prüfen, Ergebnisse kontrollieren und finalisieren.",
  sections: [
    {
      heading: "Wiederkehrende Aufgabe: Abrechnung prüfen und finalisieren",
      items: [
        "Objekt und Jahr wählen (Standard: Vorjahr).",
        "Gelbe Hinweise („Noch fehlende Daten“) und orangefarbene Warnhinweise beachten – z. B. fehlende Rechnungen oder unvollständige Strom-/Wasser-Zählerstände.",
        "Je Mieter die Kostenstellen prüfen; über „?“ auf den Beträgen siehst du die Berechnung (Rechnungen, Tarife inkl. MwSt).",
        "Im eingeklappten Kopf siehst du sofort, ob Nachzahlung (-) oder Guthaben entstanden ist.",
        "Anschließend „Abrechnung finalisieren“ – der Stand wird eingefroren und je Mieter als PDF herunterladbar.",
      ],
    },
    {
      heading: "Tipps",
      items: [
        "„Ansicht: Live“ zeigt die laufende Berechnung, „Finalisiert“ den eingefrorenen Stand.",
        "Restwasser (Leerstand/Abweichung) wird als Hinweis ausgewiesen.",
      ],
    },
  ],
};

export const techemHelp: HelpContent = {
  title: "Techem – Heizkosten-Datenaufbereitung",
  intro: "Heizkosten-Daten je Objekt und Heizperiode erfassen. Fließt NICHT in die Mieter-Abrechnung ein.",
  sections: [
    {
      heading: "Wiederkehrende Aufgabe: Heizperiode erfassen",
      items: [
        "Objekt wählen und Zeitraum setzen (Standard: 01.07. – 30.06. des Folgejahres).",
        "Heizstrom (kWh/€) wird automatisch aus dem Unterzähler übernommen.",
        "Gas (kWh/€), Wartung Heizung und Kaminfeger manuell eintragen, Notizen optional.",
        "Mit „Speichern“ wird der Zeitraum in der Liste „Gespeicherte Zeiträume“ abgelegt.",
      ],
    },
  ],
};

export const stammdatenSetupGuide: HelpContent = {
  title: "Stammdaten – Erstkonfiguration",
  intro:
    "Diese Schritte sind meist nur einmal nötig (z. B. bei einem neuen Objekt). " +
    "Bei späteren Änderungen genügt meist die Anleitung „Mieterwechsel“.",
  sections: [
    {
      heading: "1. Objekt anlegen",
      items: [
        "Objekt mit Name und Adresse anlegen.",
        "Versiegelte Fläche (m²) angeben – Grundlage für das Niederschlagswasser (€/m²/Jahr).",
      ],
    },
    {
      heading: "2. Mieteinheiten erfassen",
      items: [
        "Je Objekt die Wohnungen/Einheiten mit Wohnfläche (WF) und Extrafläche anlegen.",
        "Die Nutzfläche (NF) wird automatisch als WF + Extra berechnet.",
      ],
    },
    {
      heading: "3. Mieter anlegen",
      items: [
        "Je Einheit den Mieter mit Einzug und monatlicher Vorauszahlung erfassen.",
        "Vorauszahlungs-Zeiträume werden zum Monatsanfang angesetzt (z. B. 01.07.).",
      ],
    },
    {
      heading: "4. Umlageschlüssel festlegen",
      items: [
        "Je Objekt die Kostenarten mit Verteilerschlüssel definieren (Wohnfläche, Nutzfläche, Verbrauch, Wohnung, nicht umgelegt).",
        "Reihenfolge mit ▲▼ einstellen – sie bestimmt die Darstellung in der Abrechnung.",
      ],
    },
    {
      heading: "Hinweis",
      items: [
        "Rechnungen sowie Strom-/Wasser-Zähler und Tarife sind wiederkehrende Aufgaben – siehe Anleitung „Abrechnung erstellen“.",
      ],
    },
  ],
};

export const mieterwechselGuide: HelpContent = {
  title: "Mieterwechsel",
  intro:
    "Wenn ein Mieter auszieht und ein neuer einzieht, genügen wenige Anpassungen – " +
    "die Abrechnung rechnet die Zeiträume automatisch anteilig.",
  sections: [
    {
      heading: "1. Auszug eintragen",
      items: [
        "Beim alten Mieter das Auszug-Datum setzen (Stammdaten → Mieter).",
        "Vorauszahlungen des alten Mieters prüfen – sie gelten bis zum Auszug.",
      ],
    },
    {
      heading: "2. Neuen Mieter anlegen",
      items: [
        "In derselben Mieteinheit den neuen Mieter mit Einzug-Datum und Vorauszahlung anlegen.",
        "Vorauszahlungs-Zeiträume werden zum Monatsanfang angesetzt.",
      ],
    },
    {
      heading: "3. Zählerstände zu Ein-/Auszug (Wasser)",
      items: [
        "Bei Wohnungszählern Stände zu Auszug und Einzug erfassen – so wird der Verbrauch exakt auf die beiden Mieter aufgeteilt.",
        "Fehlt ein Stand, weist die Abrechnung darauf hin.",
      ],
    },
    {
      heading: "4. Kontrolle",
      items: [
        "In der Abrechnung prüfen, dass beide Mieter mit ihren anteiligen Zeiträumen erscheinen.",
      ],
    },
  ],
};

export const settlementGuide: HelpContent = {
  title: "Abrechnung erstellen – wiederkehrende Aufgaben",
  intro:
    "Die wiederkehrenden Schritte für eine Abrechnung je Objekt und Jahr. Stammdaten sind " +
    "meist fix – nur bei Änderungen anpassen (siehe unten).",
  sections: [
    {
      heading: "1. Stammdaten prüfen",
      items: [
        "Objekt, Mieteinheiten und Mieter sind in der Regel bereits angelegt – nur bei Bedarf anpassen.",
        "Mieterwechsel (Ein-/Auszug, ggf. Zählerstände): siehe Anleitung „Mieterwechsel“.",
        "Erstkonfiguration eines neuen Objekts: siehe Anleitung „Stammdaten – Erstkonfiguration“.",
      ],
    },
    {
      heading: "2. Rechnungen eintragen (wiederkehrend)",
      items: [
        "Je Objekt und Jahr die Rechnungen erfassen (Kostenstelle, Titel, Summe).",
        "Wiederkehrende Rechnungen per „Klonen“ ins Folgejahr übernehmen.",
        "Fehlende Rechnungen in der Abrechnung als „Keine Rechnung dieses Jahr“ markieren.",
      ],
    },
    {
      heading: "3. Strom eingeben (wiederkehrend)",
      items: [
        "Zuordnung zur Abrechnung wählen, Tarife und Zählerstände (Haupt-/Unterzähler) erfassen.",
        "Zählerwechsel als „Wert vor Zählerwechsel“ markieren.",
      ],
    },
    {
      heading: "4. Wasser eingeben (wiederkehrend)",
      items: [
        "Zuordnung wählen, Tarife und Zählerstände (Hauptzähler oder Wohnungszähler) erfassen.",
        "Waschmaschinen-Zähler optional berücksichtigen.",
      ],
    },
    {
      heading: "5. Abrechnung prüfen und finalisieren",
      items: [
        "Objekt + Jahr wählen und die Vollständigkeits- und Warnhinweise prüfen (z. B. fehlende Rechnungen, unvollständige Zählerstände).",
        "Mieterabrechnungen kontrollieren (Saldo, Hover-Infos zu den Berechnungen).",
        "„Abrechnung finalisieren“ und je Mieter das PDF herunterladen.",
      ],
    },
    {
      heading: "Siehe auch",
      items: [
        "„Stammdaten – Erstkonfiguration“ und „Mieterwechsel“ stehen in der Anleitung (links) bereit.",
      ],
    },
  ],
};
