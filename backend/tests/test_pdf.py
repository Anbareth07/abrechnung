from app import models
from app.services.engine import compute_settlement
from app.services.pdf import _tenant_table_rows, generate_tenant_pdf
from tests.test_water import _build_objekt1


def test_pdf_generation(session):
    prop = _build_objekt1(session)

    mieter_a = session.query(models.Tenant).filter_by(name="Mieter A").one()
    pdf = generate_tenant_pdf(session, prop.id, 2026, mieter_a.id)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_pdf_unknown_tenant_raises(session):
    prop = _build_objekt1(session)

    try:
        generate_tenant_pdf(session, prop.id, 2026, 99999)
    except ValueError:
        pass
    else:
        raise AssertionError("ValueError erwartet")


def test_pdf_table_zeigt_einzelne_positionen(session):
    """Die PDF-Tabelle zeigt die einzelnen Kostenstellen (auch Wasser getrennt)
    statt einer aggregierten "Wasserverbrauch"-Zeile."""
    prop = _build_objekt1(session)
    result = compute_settlement(session, prop.id, 2026)
    line = next(ln for ln in result.tenant_lines if ln.name == "Mieter A")

    rows = _tenant_table_rows(line)
    names = [r[0] for r in rows]

    assert "Trinkwasser" in names
    assert "Schmutzwasser" in names
    assert "Grundsteuer" in names
    # Keine aggregierte Wasserzeile mehr
    assert not any("Wasserverbrauch" in n for n in names)

    # Verbrauchszeile: Verteilerschlüssel "Verbrauch", Basis in m³, Anteil > 0
    trink = next(r for r in rows if r[0] == "Trinkwasser")
    assert trink[2] == "Verbrauch"
    assert "m³" in trink[3]
    assert "m³" in trink[4]
    assert trink[6] != "0,00"

    # Flächenzeile: Verteilerschlüssel "Nutzfläche", Basis in m²
    grund = next(r for r in rows if r[0] == "Grundsteuer")
    assert grund[2] == "Nutzfläche"
    assert "m²" in grund[3]
    assert "m²" in grund[4]

    # Summe der Einzelanteile = Gesamtkosten des Mieters
    total = sum(float(r[6].replace(".", "").replace(",", ".")) for r in rows)
    assert abs(total - float(line.total_costs)) < 0.01


def test_pdf_enthaelt_einzelne_positionen_im_text(session):
    """Der erzeugte PDF-Text enthält die einzelnen Kostenstellen (Trink-/Schmutzwasser
    getrennt) und keine aggregierte "Wasserverbrauch"-Zeile."""
    from io import BytesIO

    from pypdf import PdfReader

    prop = _build_objekt1(session)
    mieter_a = session.query(models.Tenant).filter_by(name="Mieter A").one()
    pdf = generate_tenant_pdf(session, prop.id, 2026, mieter_a.id)

    text = "\n".join(p.extract_text() or "" for p in PdfReader(BytesIO(pdf)).pages)
    assert "Trinkwasser" in text
    assert "Schmutzwasser" in text
    assert "Grundsteuer" in text
    assert "Wasserverbrauch (Trink- + Schmutzwasser)" not in text
