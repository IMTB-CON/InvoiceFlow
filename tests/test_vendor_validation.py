from rechnungen_poc.llm import flag_own_company_as_vendor
from rechnungen_poc.models import InvoiceData


OWN_NAMES: frozenset[str] = frozenset({"IMTB", "IMTB Consulting GmbH"})


def test_clears_vendor_name_on_exact_match() -> None:
    invoice = InvoiceData(vendor_name="IMTB Consulting GmbH")
    result = flag_own_company_as_vendor(invoice, OWN_NAMES)
    assert result.vendor_name is None
    assert result.needs_review is True
    assert result.review_reason is not None


def test_clears_vendor_name_when_short_token_matches_longer_name() -> None:
    # "IMTB" (from own_company_names) is a substring of "IMTB Academy GmbH"
    invoice = InvoiceData(vendor_name="IMTB Academy GmbH")
    result = flag_own_company_as_vendor(invoice, OWN_NAMES)
    assert result.vendor_name is None
    assert result.needs_review is True


def test_clears_vendor_name_when_vendor_is_substring_of_own_name() -> None:
    # vendor "IMTB" is a substring of own name "IMTB Consulting GmbH"
    invoice = InvoiceData(vendor_name="IMTB")
    result = flag_own_company_as_vendor(invoice, OWN_NAMES)
    assert result.vendor_name is None
    assert result.needs_review is True


def test_case_insensitive_matching() -> None:
    invoice = InvoiceData(vendor_name="imtb consulting gmbh")
    result = flag_own_company_as_vendor(invoice, OWN_NAMES)
    assert result.vendor_name is None
    assert result.needs_review is True


def test_preserves_existing_review_reason() -> None:
    invoice = InvoiceData(vendor_name="IMTB", needs_review=True, review_reason="Betrag unklar")
    result = flag_own_company_as_vendor(invoice, OWN_NAMES)
    assert result.review_reason is not None
    assert "Betrag unklar" in result.review_reason
    assert "IMTB" in result.review_reason


def test_unrelated_vendor_is_unchanged() -> None:
    invoice = InvoiceData(vendor_name="Acme GmbH")
    result = flag_own_company_as_vendor(invoice, OWN_NAMES)
    assert result.vendor_name == "Acme GmbH"
    assert result.needs_review is False
    assert result is invoice  # same object, no copy needed


def test_no_op_when_own_company_names_is_empty() -> None:
    invoice = InvoiceData(vendor_name="IMTB")
    result = flag_own_company_as_vendor(invoice, frozenset())
    assert result.vendor_name == "IMTB"
    assert result is invoice


def test_no_op_when_vendor_name_is_none() -> None:
    invoice = InvoiceData(vendor_name=None)
    result = flag_own_company_as_vendor(invoice, OWN_NAMES)
    assert result.vendor_name is None
    assert result.needs_review is False
    assert result is invoice
