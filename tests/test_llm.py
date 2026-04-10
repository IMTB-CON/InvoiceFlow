from rechnungen_poc.llm import extract_json_object


def test_extract_json_object_reads_plain_json() -> None:
    raw = '{"vendor_name":"ACME","gross_amount":119.0}'
    assert extract_json_object(raw) == {"vendor_name": "ACME", "gross_amount": 119.0}


def test_extract_json_object_reads_json_embedded_in_text() -> None:
    raw = 'Here is the result:\n{"vendor_name":"ACME","needs_review":true}\nThanks.'
    assert extract_json_object(raw) == {"vendor_name": "ACME", "needs_review": True}


def test_extract_json_object_ignores_braces_inside_strings() -> None:
    raw = '{"review_reason":"Check {weird} value","needs_review":true}'
    assert extract_json_object(raw) == {
        "review_reason": "Check {weird} value",
        "needs_review": True,
    }


def test_extract_json_object_returns_empty_dict_when_missing() -> None:
    assert extract_json_object("No structured payload here") == {}
