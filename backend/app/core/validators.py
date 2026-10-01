"""Authoritative validators (plan 8.1 / spec section 2). Raise ``ValueError`` so they plug into Pydantic."""

import re
from decimal import Decimal, InvalidOperation

import phonenumbers
from email_validator import EmailNotValidError
from email_validator import validate_email as _validate_email

PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,128}$")
PHONE_RE = re.compile(r"^\+?[1-9][0-9]{9,14}$")
REG_NO_RE = re.compile(r"^([LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}|[A-Z]{2}-[A-Z0-9]{6,15})$")
PDF_MAGIC = b"%PDF-"


def validate_email(value: str) -> str:
    """RFC 5322 style validation via email-validator (no DNS lookups); returns the lowercased address."""
    if not isinstance(value, str):
        raise ValueError("Email must be a string")
    try:
        result = _validate_email(value.strip(), check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValueError(f"Invalid email address: {exc}") from exc
    return result.normalized.lower()


def normalize_phone(value: str) -> str:
    """Strip spaces, dashes, dots and parentheses; must be 10-15 digits with optional leading +.

    When the number starts with ``+`` and ``phonenumbers`` can parse it, it is re-formatted to E.164.
    """
    if not isinstance(value, str):
        raise ValueError("Phone must be a string")
    cleaned = re.sub(r"[\s\-().]", "", value)
    if not PHONE_RE.match(cleaned):
        raise ValueError("Phone number must have 10 to 15 digits, with an optional leading +")
    if cleaned.startswith("+"):
        try:
            parsed = phonenumbers.parse(cleaned, None)
            formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            if PHONE_RE.match(formatted):
                return formatted
        except phonenumbers.NumberParseException:
            pass
    return cleaned


def validate_password(value: str) -> str:
    """>= 8 chars with upper, lower, digit and special character (max 128)."""
    if not isinstance(value, str):
        raise ValueError("Password must be a string")
    problems = []
    if len(value) < 8:
        problems.append("at least 8 characters")
    if len(value) > 128:
        problems.append("at most 128 characters")
    if not re.search(r"[a-z]", value):
        problems.append("a lowercase letter")
    if not re.search(r"[A-Z]", value):
        problems.append("an uppercase letter")
    if not re.search(r"\d", value):
        problems.append("a digit")
    if not re.search(r"[^A-Za-z0-9]", value):
        problems.append("a special character")
    if problems:
        raise ValueError("Password must contain " + ", ".join(problems))
    return value


def normalize_registration_number(value: str) -> str:
    """Upper-case, strip whitespace, then require Indian CIN or international ``CC-XXXXXX`` format."""
    if not isinstance(value, str):
        raise ValueError("Registration number must be a string")
    cleaned = re.sub(r"\s+", "", value).upper()
    if not REG_NO_RE.match(cleaned):
        raise ValueError(
            "Registration number must be an Indian CIN (e.g. U72200KA2015PTC082345) "
            "or CC-XXXXXX (e.g. US-DE5567123)"
        )
    return cleaned


def is_pdf_magic(head: bytes) -> bool:
    """True when the first bytes are the PDF header ``%PDF-``."""
    return head[: len(PDF_MAGIC)] == PDF_MAGIC


def validate_gpa(value: float | int | str | Decimal) -> Decimal:
    try:
        d = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("GPA must be a number") from exc
    if d < 0 or d > 4:
        raise ValueError("GPA must be between 0.0 and 4.0")
    return d
