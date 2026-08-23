from enum import Enum


class AllocationKey(str, Enum):
    """Umlageschlüssel einer Kostenart (je Objekt konfigurierbar)."""

    WF = "WF"  # Wohnfläche
    NF = "NF"  # Nutzfläche
    WOHNUNG = "WOHNUNG"  # je Wohnung: Kosten gehen 1:1 gleichmäßig auf jede belegte Einheit
    CONSUMPTION = "CONSUMPTION"  # Verbrauch (Zähler, z. B. Wasser)
    NONE = "NONE"  # nicht umgelegt (z. B. Abfall, Heizung/Gas)


class MeterType(str, Enum):
    APARTMENT_WATER = "APARTMENT_WATER"  # Wohnungs-Wasserzähler
    WASHING_MACHINE = "WASHING_MACHINE"  # Waschmaschinen-Zähler (je Mieteinheit)
    GARDEN = "GARDEN"  # Gartenwasser-Zähler
    HEATING_ELECTRICITY = "HEATING_ELECTRICITY"  # Heizstrom-Extrazähler
    GAS = "GAS"
    ELECTRICITY = "ELECTRICITY"
    OTHER = "OTHER"


class MeterUnit(str, Enum):
    M3 = "m3"
    KWH = "kWh"


class SettlementStatus(str, Enum):
    DRAFT = "DRAFT"
    FINAL = "FINAL"


class TechemKind(str, Enum):
    GAS = "GAS"
    HEATING_ELECTRICITY = "HEATING_ELECTRICITY"


class InvoiceKind(str, Enum):
    """Art einer Rechnung – steuert Eingabelayout und Verteilung."""

    GRUNDSTEUER = "GRUNDSTEUER"  # wiederkehrend: gültig ab + Jahresbetrag, bis neuer Bescheid
    WASSER = "WASSER"
    STROM = "STROM"
    VERSICHERUNG_HAFTPFLICHT = "VERSICHERUNG_HAFTPFLICHT"
    VERSICHERUNG_WOHNGEBAEUDE = "VERSICHERUNG_WOHNGEBAEUDE"
    GARTEN = "GARTEN"
    LEGIONELLEN = "LEGIONELLEN"
    SCHORNSTEINFEGER = "SCHORNSTEINFEGER"  # objekt- oder wohneinheitbezogen
    SONSTIGE = "SONSTIGE"
