from __future__ import annotations

from enum import Enum
from urllib.error import HTTPError


class ErrorClass(str, Enum):
    HTTP_404 = "http_404"
    HTTP_5XX = "http_5xx"
    HTTP_OTHER = "http_other"
    NETWORK_TIMEOUT = "network_timeout"
    EMPTY_RESPONSE = "empty_response"
    PARSE_ERROR = "parse_error"
    MANIFEST_ERROR = "manifest_error"


def classify_http_exception(exc: HTTPError) -> ErrorClass:
    code = int(getattr(exc, "code", 0) or 0)
    if code == 404:
        return ErrorClass.HTTP_404
    if code in {429, 500, 502, 503, 504}:
        return ErrorClass.HTTP_5XX
    return ErrorClass.HTTP_OTHER
