from functools import lru_cache
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class InstrumentConfig(BaseModel):
    tv_symbol: str
    ctrader_symbol: str
    volume: int = Field(gt=0)
    label: str
    allowed_strategies: set[str]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore', case_sensitive=False)
    app_name: str = 'TradingView Multi-Asset cTrader Executor'
    dry_run: bool = True
    ctrader_env: str = 'demo'
    ctrader_client_id: str = ''
    ctrader_client_secret: str = ''
    ctrader_access_token: str = ''
    ctrader_account_id: int = 0
    webhook_token: str = 'change-me'
    max_signal_age_seconds: int = 300
    allow_pyramiding: bool = False
    db_path: str = 'data/execution.db'

    oil_tv_symbol: str = 'WTOIL-PERP'
    oil_ctrader_symbol: str = 'SPOTCRUDE'
    oil_volume: int = 100
    oil_label: str = 'TV_OIL_3_0'
    oil_strategies: str = 'OIL_2_2_OPT_MORNING_AFTERNOON_ADX'

    gold_tv_symbol: str = 'XAUUSD'
    gold_ctrader_symbol: str = 'XAUUSD'
    gold_volume: int = 100
    gold_label: str = 'TV_GOLD_1_6'
    gold_strategies: str = 'GOLD_1_6_A8V120_CORE_0800_1200_1400_1800'

    def instruments(self) -> dict[str, InstrumentConfig]:
        def split(v: str): return {x.strip() for x in v.split(',') if x.strip()}
        items = [
            InstrumentConfig(tv_symbol=self.oil_tv_symbol.upper(), ctrader_symbol=self.oil_ctrader_symbol,
                volume=self.oil_volume, label=self.oil_label, allowed_strategies=split(self.oil_strategies)),
            InstrumentConfig(tv_symbol=self.gold_tv_symbol.upper(), ctrader_symbol=self.gold_ctrader_symbol,
                volume=self.gold_volume, label=self.gold_label, allowed_strategies=split(self.gold_strategies)),
        ]
        return {x.tv_symbol: x for x in items}

@lru_cache
def get_settings():
    return Settings()
