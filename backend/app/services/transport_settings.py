"""Shared bounded Gemini deadlines. SDK HttpOptions.timeout uses milliseconds."""

from contextlib import contextmanager
import math
import os
import time


def request_timeout_ms():
    raw=os.getenv("GEMINI_TIMEOUT_SECONDS","30")
    try:value=float(raw)
    except ValueError:raise ValueError("GEMINI_TIMEOUT_SECONDS must be a number from 5 to 60.") from None
    if not math.isfinite(value) or not 5<=value<=60:
        raise ValueError("GEMINI_TIMEOUT_SECONDS must be from 5 to 60.")
    return int(value*1000)


def remaining_timeout_ms(deadline):
    remaining=int((deadline-time.monotonic())*1000)
    if remaining<=0:raise TimeoutError("AI analysis time budget exhausted.")
    return min(request_timeout_ms(),remaining)


@contextmanager
def temporary_timeout(seconds):
    previous=os.environ.get("GEMINI_TIMEOUT_SECONDS")
    try:
        if seconds is not None:os.environ["GEMINI_TIMEOUT_SECONDS"]=str(seconds)
        request_timeout_ms()  # validate before any API call
        yield
    finally:
        if previous is None:os.environ.pop("GEMINI_TIMEOUT_SECONDS",None)
        else:os.environ["GEMINI_TIMEOUT_SECONDS"]=previous
