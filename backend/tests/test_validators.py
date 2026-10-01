import pytest
from sqlalchemy.exc import IntegrityError

from app.core.errors import constraint_name_of
from app.core.validators import (
    is_pdf_magic,
    normalize_phone,
    normalize_registration_number,
    validate_email,
    validate_password,
)
from app.modules.users.models import User
from tests.factories import _DEFAULT_HASH


@pytest.mark.parametrize("value", ["a@b.co", "first.last+tag@sub.campushire.dev", "UPPER@Example.COM"])
def test_email_valid_invalid_ok(value):
    assert validate_email(value) == validate_email(value).lower()


@pytest.mark.parametrize("value", ["plainaddress", "a@b", "a..b@c.com", "a@b..com", "@campushire.dev", "a b@c.com", ""])
def test_email_valid_invalid_rejected(value):
    with pytest.raises(ValueError):
        validate_email(value)


def test_email_is_lowercased():
    assert validate_email("Foo@Campushire.Dev") == "foo@campushire.dev"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+919876543210", "+919876543210"),
        ("9876543210", "9876543210"),
        ("+1 (415) 555-2671", "+14155552671"),
        ("98765-43210", "9876543210"),
        ("+91 98765 43210", "+919876543210"),
    ],
)
def test_phone_ok(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["12345", "+1234567890123456", "abcdefghij", "0123456789", "+0123456789012", "98765 4321x"])
def test_phone_bad(raw):
    with pytest.raises(ValueError):
        normalize_phone(raw)


@pytest.mark.parametrize(
    ("password", "fragment"),
    [
        ("alllower1!", "uppercase"),
        ("ALLUPPER1!", "lowercase"),
        ("NoDigits!!", "digit"),
        ("NoSpecial12", "special"),
        ("Sh0rt!a", "at least 8"),
    ],
)
def test_password_rejected(password, fragment):
    with pytest.raises(ValueError, match=fragment):
        validate_password(password)


def test_password_ok():
    assert validate_password("Admin@12345") == "Admin@12345"
    assert validate_password("Abcdef1!") == "Abcdef1!"  # exactly 8


def test_password_too_long():
    with pytest.raises(ValueError):
        validate_password("Aa1!" + "x" * 125)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("U72200KA2015PTC082345", "U72200KA2015PTC082345"),
        ("l40100tn2012plc087654", "L40100TN2012PLC087654"),
        (" US-DE5567123 ", "US-DE5567123"),
        ("us-de 5567123", "US-DE5567123"),
        ("GB-ABC123", "GB-ABC123"),
    ],
)
def test_registration_number_ok(raw, expected):
    assert normalize_registration_number(raw) == expected


@pytest.mark.parametrize("raw", ["ABC", "", "U72200KA2015PTC08234", "X72200KA2015PTC082345", "US-AB12", "USA-ABC1234"])
def test_registration_number_bad(raw):
    with pytest.raises(ValueError):
        normalize_registration_number(raw)


def test_pdf_magic():
    assert is_pdf_magic(b"%PDF-1.7\n...")
    assert is_pdf_magic(b"%PDF-")
    assert not is_pdf_magic(b"%PDF")
    assert not is_pdf_magic(b"PK\x03\x04")
    assert not is_pdf_magic(b"")


# ---- last line of defence: DB CHECK constraints ---------------------------------------------------------


@pytest.mark.parametrize("bad_phone", ["12345", "1234567890123456", "abcdefghijk", "0123456789"])
async def test_db_check_rejects_bad_phone(db, bad_phone):
    user = User(email="dbcheck@campushire.dev", password_hash=_DEFAULT_HASH, role="STUDENT", full_name="Db Check", phone=bad_phone)
    with pytest.raises(IntegrityError) as exc:
        async with db.begin_nested():
            db.add(user)
            await db.flush()
    assert constraint_name_of(exc.value) == "ck_users_phone"


async def test_db_check_rejects_bad_email_and_role(db):
    for kwargs, name in [
        ({"email": "not-an-email", "role": "STUDENT"}, "ck_users_email"),
        ({"email": "ok@campushire.dev", "role": "SUPERUSER"}, "ck_users_role"),
    ]:
        user = User(password_hash=_DEFAULT_HASH, full_name="Db Check", **kwargs)
        with pytest.raises(IntegrityError) as exc:
            async with db.begin_nested():
                db.add(user)
                await db.flush()
        assert constraint_name_of(exc.value) == name
