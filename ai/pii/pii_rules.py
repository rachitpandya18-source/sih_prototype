import re


PII_PATTERNS = {
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",

    "PHONE": r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)",

    "AADHAAR": r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)",

    "PAN": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",

    "UPI": r"\b[A-Za-z0-9._-]+@[A-Za-z0-9_-]+\b",

    "IFSC": r"\b[A-Z]{4}0[A-Z0-9]{6}\b"
}


def overlaps(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1


def detect_pii(text):
    findings = []

    # First detect EMAILs.
    email_matches = list(
        re.finditer(PII_PATTERNS["EMAIL"], text, re.IGNORECASE)
    )

    for match in email_matches:
        findings.append({
            "type": "EMAIL",
            "text": match.group(),
            "start": match.start(),
            "end": match.end(),
            "confidence": 1.0,
            "source": "regex"
        })

    # Detect remaining PII types.
    for pii_type, pattern in PII_PATTERNS.items():

        if pii_type == "EMAIL":
            continue

        matches = re.finditer(pattern, text, re.IGNORECASE)

        for match in matches:

            start = match.start()
            end = match.end()

            # Do not classify part of an email as UPI.
            if pii_type == "UPI":
                is_inside_email = False

                for email in email_matches:
                    if overlaps(
                        start,
                        end,
                        email.start(),
                        email.end()
                    ):
                        is_inside_email = True
                        break

                if is_inside_email:
                    continue

            findings.append({
                "type": pii_type,
                "text": match.group(),
                "start": start,
                "end": end,
                "confidence": 1.0,
                "source": "regex"
            })

    return findings


if __name__ == "__main__":

    test_text = """
    Name: Rahul Sharma
    Email: rahul.sharma@example.com
    Phone: +91 9876543210
    Aadhaar: 1234 5678 9012
    PAN: ABCDE1234F
    UPI: rahul@upi
    IFSC: SBIN0001234

    Price: ₹12,999
    Order ID: 123456789
    OTP expires in 10 minutes
    GST: 24ABCDE1234F1Z5
    """

    results = detect_pii(test_text)

    for result in results:
        print(result)