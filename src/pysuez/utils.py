from datetime import date, datetime
import re
from pysuez.const import LITERS_PER_CUBIC_METER
from pysuez.exception import PySuezError


def cubic_meters_to_liters(value: float | None) -> None | float:
    if value is None:
        return None
    return value * LITERS_PER_CUBIC_METER


def extract_token(page: str) -> str:
    phrase = re.compile(
        "csrfToken\\\\u0022\\\\u003A\\\\u0022(.*)\\\\u0022,\\\\u0022targetUrl"
    )
    result = phrase.search(page)
    if result is None:
        raise PySuezError("Token not found in query")
    return result.group(1).encode().decode("unicode_escape")


def next_month(x: date | datetime) -> date | datetime:
    try:
        return x.replace(month=x.month + 1)
    except ValueError:
        if x.month == 12:
            return x.replace(year=x.year + 1, month=1)
        else:
            # Not handled for now
            raise
