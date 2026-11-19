import re

from fastapi import HTTPException, status


_INDIAN_MOBILE = re.compile(r"^[6-9][0-9]{9}$")
_E164 = re.compile(r"^\+[1-9][0-9]{7,14}$")


def normalize_mobile(value: str) -> str:
    """Return the canonical E.164 mobile number used for identity lookups.

    DukaanPulse currently serves Indian wholesalers, so a plain ten-digit
    Indian mobile number is accepted and canonicalised with +91. Any other
    input must already be a syntactically valid E.164 number.
    """
    compact = re.sub(r"[\s()\-]", "", value or "")
    if _INDIAN_MOBILE.fullmatch(compact):
        return f"+91{compact}"
    if compact.startswith("00"):
        compact = f"+{compact[2:]}"
    if not _E164.fullmatch(compact):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter a valid mobile number.",
        )
    return compact
