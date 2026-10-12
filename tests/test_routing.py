import os
os.environ.update({'OIL_STRATEGIES':'OIL','GOLD_STRATEGIES':'GOLD'})
from app.config import Settings

def test_routes_are_isolated():
    i=Settings().instruments()
    assert i['WTOIL-PERP'].ctrader_symbol=='SPOTCRUDE'
    assert i['XAUUSD'].ctrader_symbol=='XAUUSD'
    assert i['WTOIL-PERP'].label != i['XAUUSD'].label
    assert 'OIL' in i['WTOIL-PERP'].allowed_strategies
    assert 'GOLD' in i['XAUUSD'].allowed_strategies
