from app import models
from app.services.pdf import generate_tenant_pdf
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
