from pii_rules import detect_pii


def get_types(text):
    return [item["type"] for item in detect_pii(text)]


def test_email_not_detected_as_upi():

    text = "Email: rahul.sharma@example.com"

    results = detect_pii(text)

    assert len(results) == 1
    assert results[0]["type"] == "EMAIL"


def test_upi_detected():

    text = "UPI: rahul@upi"

    results = detect_pii(text)

    assert len(results) == 1
    assert results[0]["type"] == "UPI"


def test_multiple_pii():

    text = """
    Email: rahul@example.com
    Phone: +91 9876543210
    Aadhaar: 1234 5678 9012
    PAN: ABCDE1234F
    UPI: rahul@upi
    IFSC: SBIN0001234
    """

    types = get_types(text)

    assert "EMAIL" in types
    assert "PHONE" in types
    assert "AADHAAR" in types
    assert "PAN" in types
    assert "UPI" in types
    assert "IFSC" in types


def test_normal_numbers_not_detected_as_pii():

    text = """
    Price: ₹12,999
    Order ID: 123456789
    OTP expires in 10 minutes
    Quantity: 25
    """

    results = detect_pii(text)

    assert len(results) == 0