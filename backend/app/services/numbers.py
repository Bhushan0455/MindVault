"""Step 15: bounded English cardinal parsing and explicit INR price mentions.

Word numbers: zero through nine hundred ninety-nine. No fractions, decimal
words, ordinals, signed words, lakh/crore or general natural-language reasoning.
Digit amounts support ungrouped, western and Indian comma grouping.
"""

from dataclasses import dataclass
from decimal import Decimal
import re


_SMALL_NAMES=("zero","one","two","three","four","five","six","seven","eight","nine",
              "ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen","nineteen")
_TENS_NAMES=("twenty","thirty","forty","fifty","sixty","seventy","eighty","ninety")
_SMALL={word:index for index,word in enumerate(_SMALL_NAMES)}
_TENS={word:(index+2)*10 for index,word in enumerate(_TENS_NAMES)}
_ONES_PATTERN="(?:"+"|".join(_SMALL_NAMES[1:10])+")"
_LOW_PATTERN="(?:"+"|".join(_SMALL_NAMES)+"|(?:"+"|".join(_TENS_NAMES)+r")(?:[\s-]+"+_ONES_PATTERN+")?)"
_WORDS_PATTERN=r"(?:"+_ONES_PATTERN+r"\s+hundred(?:\s+(?:and\s+)?"+_LOW_PATTERN+r")?|"+_LOW_PATTERN+r")"
_DIGITS_PATTERN=r"(?:\d{1,2}(?:,\d{2})+,\d{3}|\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?"
NUMBER_PATTERN="(?:"+_DIGITS_PATTERN+"|"+_WORDS_PATTERN+")"


def parse_number(raw: str) -> Decimal:
    """Parse the ENTIRE token. Malformed grouping/word sequences fail explicitly."""
    raw=raw.strip().casefold()
    if re.fullmatch(_DIGITS_PATTERN,raw): return Decimal(raw.replace(",",""))
    if not re.fullmatch(_WORDS_PATTERN,raw): raise ValueError("Unsupported number wording.")
    parts=raw.replace("-"," ").split()
    total=0
    if len(parts)>=2 and parts[1]=="hundred":
        total=_SMALL[parts[0]]*100
        parts=parts[2:]
        if parts and parts[0]=="and": parts=parts[1:]
    for part in parts: total+=_SMALL.get(part,_TENS.get(part,0))
    return Decimal(total)


def is_partial_number(text: str, start: int) -> bool:
    """Do not silently recover a smaller suffix of unsupported word/range input."""
    prefix=text[:start]
    if re.search(r"\d\s*[-–/]\s*$",prefix): return True
    last=re.search(r"([A-Za-z]+)[\s-]+$",prefix)
    number_words={*_SMALL,*_TENS,"hundred","thousand","million","billion","lakh","crore","point","minus","negative"}
    if last and last[1].casefold() in number_words:
        return True
    return bool(re.search(r"(?:\d|\b(?:"+"|".join(number_words)+r"))\s+(?:to|and)\s*$",prefix,re.I))


@dataclass(frozen=True)
class PriceMention:
    start: int
    end: int
    value: Decimal


_PRICE=re.compile(r"(?<![\w.,+\-])(?:(?:₹\s*|INR\s+|Rs\.?\s*)(?P<prefix_amount>"+NUMBER_PATTERN+r")"
    r"|(?P<suffix_amount>"+NUMBER_PATTERN+r")\s+(?:rupees?|INR))"
    r"(?!\w|[.,]\d)",re.I)


def iter_prices(text: str):
    """Explicit INR prefix or rupees/INR suffix; never bare unqualified numbers."""
    for match in _PRICE.finditer(text):
        if is_partial_number(text,match.start()): continue
        yield PriceMention(match.start(),match.end(),parse_number(match["prefix_amount"] or match["suffix_amount"]))
