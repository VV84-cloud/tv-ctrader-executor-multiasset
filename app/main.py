import hashlib, logging, time
from fastapi import FastAPI, HTTPException
from .config import get_settings
from .models import WebhookSignal, WebhookResponse
from .store import SignalStore
from .ctrader import CTraderGateway

logging.basicConfig(level=logging.INFO)
s=get_settings(); app=FastAPI(title=s.app_name); store=SignalStore(s.db_path); gateway=CTraderGateway(s)

def signal_id(x):
    if x.signal_id: return x.signal_id
    if x.bar_time: return f'{x.strategy}:{x.bar_time}:{x.action}'
    raw=f'{x.strategy}:{x.symbol}:{x.action}:{x.signal_price}:{x.reason}:{int(time.time()//60)}'
    return hashlib.sha256(raw.encode()).hexdigest()[:32]

@app.get('/health')
def health():
    return {'status':'ok','dry_run':s.dry_run,'ctrader_env':s.ctrader_env,'ctrader_ready':gateway.ready,
      'ctrader_error':gateway.error,'symbols':{k:{'ctrader':v.ctrader_symbol,'volume':v.volume,'label':v.label} for k,v in gateway.instruments.items()}}

@app.post('/webhook/{token}',response_model=WebhookResponse)
def webhook(token:str,x:WebhookSignal):
    if token!=s.webhook_token: raise HTTPException(401,'Invalid webhook token')
    cfg=s.instruments().get(x.symbol.upper())
    if not cfg: raise HTTPException(403,f'Symbol not allowed: {x.symbol}')
    if x.strategy not in cfg.allowed_strategies: raise HTTPException(403,f'Strategy not allowed for {x.symbol}: {x.strategy}')
    if s.max_signal_age_seconds>0 and x.bar_time:
        age=abs(time.time()-x.bar_time/1000)
        if age>s.max_signal_age_seconds: raise HTTPException(409,f'Signal is stale ({int(age)}s)')
    sid=signal_id(x)
    if not store.claim(sid): return WebhookResponse(accepted=True,duplicate=True,dry_run=s.dry_run,action=x.action,signal_id=sid,routed_to=cfg.ctrader_symbol)
    if s.dry_run:
        return WebhookResponse(accepted=True,dry_run=True,action=x.action,signal_id=sid,routed_to=cfg.ctrader_symbol,details={'message':'DRY_RUN: no broker request sent','volume':cfg.volume,'label':cfg.label})
    if not gateway.ready: raise HTTPException(503,f'cTrader not ready: {gateway.error}')
    inst=gateway.instrument(x.symbol)
    if x.action.startswith('ENTRY'):
        if not s.allow_pyramiding and gateway.has_open(inst): raise HTTPException(409,'An executor-managed position is already open for this instrument')
        details=gateway.open(inst,x.action,x.signal_price,x.stop_price)
    else:
        details=gateway.close(inst,x.action)
    return WebhookResponse(accepted=True,dry_run=False,action=x.action,signal_id=sid,routed_to=cfg.ctrader_symbol,details=details)
