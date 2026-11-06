from datetime import date
from decimal import Decimal
from typing import Literal, Annotated
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class BrandIn(StrictModel):
    name: str = Field(min_length=1, max_length=120)


class ProductIn(StrictModel):
    brand_id: str
    name: str = Field(min_length=1,max_length=120)
    aliases: list[Annotated[str,Field(min_length=1,max_length=120)]] = Field(default_factory=list,max_length=30)


class ProductAliases(StrictModel):
    aliases: list[Annotated[str,Field(min_length=1,max_length=120)]] = Field(max_length=30)


class RuleIn(StrictModel):
    brand_id: str
    code: str = Field(min_length=1, max_length=40)
    instruction: str = Field(min_length=1, max_length=12000)
    category: Literal['general','claims','terminology','disclaimer','tone'] = 'claims'
    severity: Literal['critical','high','medium','low'] = 'medium'
    authority: Literal['non_overridable','core','scoped','exception'] = 'core'
    priority: int = Field(default=0,ge=-2147483648,le=2147483647)
    scope_channel: list[str] = Field(default_factory=list)
    scope_audience: list[str] = Field(default_factory=list)
    scope_region: list[str] = Field(default_factory=list)
    scope_content_type: list[str] = Field(default_factory=list)
    scope_campaign: list[str] = Field(default_factory=list)
    forbidden_terms: list[str] = Field(default_factory=list)
    preferred_terms: dict[str,str] = Field(default_factory=dict)
    required_text: str | None = None
    requires_claim_evidence: bool = False
    effective_from: date | None = None
    effective_to: date | None = None
    source_document_id: str | None = Field(default=None,max_length=36)
    source_location: str | None = Field(default=None,max_length=100)
    source_excerpt: str | None = Field(default=None,max_length=12000)

    @model_validator(mode='after')
    def valid(self):
        if self.effective_from and self.effective_to and self.effective_from > self.effective_to:
            raise ValueError('Invalid effective date range')
        for values in [self.scope_channel,self.scope_audience,self.scope_region,self.scope_content_type,self.scope_campaign,self.forbidden_terms]:
            if any(not s.strip() for s in values): raise ValueError('Blank tags or terms')
        if self.category == 'disclaimer' and not self.required_text:
            raise ValueError('Disclaimer rules need required_text')
        if self.category == 'terminology' and not self.forbidden_terms:
            raise ValueError('Terminology rules need forbidden_terms')
        return self


class FactIn(StrictModel):
    brand_id: str
    product: str = Field(min_length=1, max_length=120)
    attribute: Literal['price','battery_life','warranty','claim']
    value_text: str = Field(min_length=1, max_length=255)
    value_num: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False, max_digits=16, decimal_places=2)
    unit: str | None = Field(default=None,max_length=40)
    market: str = Field(min_length=1, max_length=20)
    qualifier: Literal['exact','up_to'] = 'exact'
    valid_from: date | None = None
    valid_to: date | None = None
    source_document_id: str | None = Field(default=None,max_length=36)
    source_location: str | None = Field(default=None,max_length=100)
    source_excerpt: str | None = Field(default=None,max_length=12000)

    @model_validator(mode='after')
    def valid(self):
        units = {'price':['INR'], 'battery_life':['hours'], 'warranty':['years','months']}
        if self.attribute != 'claim' and (self.value_num is None or self.unit not in units[self.attribute]):
            raise ValueError('Numeric facts need a supported value and unit')
        if self.attribute in ('price','claim') and self.qualifier != 'exact': raise ValueError('Unsupported qualifier')
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to: raise ValueError('Invalid valid date range')
        return self


class CandidateApproval(StrictModel):
    # Reviewer confirms all details, including market and dates absent from source.
    knowledge: RuleIn | FactIn


class ClarityAccept(StrictModel):
    proposal_id: str
    instruction: str = Field(min_length=1, max_length=12000)
