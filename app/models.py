from typing import Literal, Any
from pydantic import BaseModel, Field, model_validator

Action = Literal['ENTRY_LONG','ENTRY_SHORT','EXIT_LONG','EXIT_SHORT']

class WebhookSignal(BaseModel):
    strategy: str
    action: Action
    symbol: str
    signal_price: float
    stop_price: float | None = None
    reason: str | None = None
    signal_id: str | None = None
    bar_time: int | None = None
    timeframe: str | None = None
    adx_trigger: float | None = None

    @model_validator(mode='after')
    def validate_entry(self):
        if self.action.startswith('ENTRY'):
            if self.stop_price is None:
                raise ValueError('stop_price is required for entries')
            if self.action == 'ENTRY_LONG' and self.stop_price >= self.signal_price:
                raise ValueError('Long stop_price must be below signal_price')
            if self.action == 'ENTRY_SHORT' and self.stop_price <= self.signal_price:
                raise ValueError('Short stop_price must be above signal_price')
        return self

class WebhookResponse(BaseModel):
    accepted: bool
    duplicate: bool = False
    dry_run: bool
    action: str
    signal_id: str
    routed_to: str | None = None
    details: dict[str, Any] = {}
