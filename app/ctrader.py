import logging, threading
from dataclasses import dataclass
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from ctrader_open_api import Client, TcpProtocol, EndPoints, Protobuf
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq, ProtoOAAccountAuthReq, ProtoOASymbolsListReq,
    ProtoOANewOrderReq, ProtoOAReconcileReq, ProtoOAClosePositionReq,
)
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrderType, ProtoOATradeSide

log=logging.getLogger(__name__)

@dataclass
class ResolvedInstrument:
    tv_symbol:str; ctrader_symbol:str; symbol_id:int; volume:int; label:str; strategies:set[str]

class CTraderGateway:
    def __init__(self,settings):
        self.s=settings; self.ready=False; self.error=None; self.client=None; self.instruments={}
        self.thread=threading.Thread(target=self._run,daemon=True); self.thread.start()
    def _run(self):
        reactor.callWhenRunning(self._connect)
        reactor.run(installSignalHandlers=False)
    def _wait(self,d,timeout=20):
        ev=threading.Event(); box={}
        d.addCallbacks(lambda x:(box.setdefault('v',x),ev.set()),lambda e:(box.setdefault('e',e),ev.set()))
        if not ev.wait(timeout): raise TimeoutError('cTrader request timed out')
        if 'e' in box: raise RuntimeError(str(box['e']))
        return box.get('v')
    def _submit(self,func,*args):
        from twisted.internet.threads import blockingCallFromThread
        return blockingCallFromThread(reactor,func,*args)
    @inlineCallbacks
    def _connect(self):
        try:
            host=EndPoints.PROTOBUF_DEMO_HOST if self.s.ctrader_env.lower()=='demo' else EndPoints.PROTOBUF_LIVE_HOST
            self.client=Client(host,EndPoints.PROTOBUF_PORT,TcpProtocol)
            yield self.client.startService()
            result=Protobuf.extract((yield self.client.send(ProtoOAApplicationAuthReq(clientId=self.s.ctrader_client_id,clientSecret=self.s.ctrader_client_secret))))
            result=Protobuf.extract((yield self.client.send(ProtoOAAccountAuthReq(ctidTraderAccountId=self.s.ctrader_account_id,accessToken=self.s.ctrader_access_token))))
            symbols=Protobuf.extract((yield self.client.send(ProtoOASymbolsListReq(ctidTraderAccountId=self.s.ctrader_account_id,includeArchivedSymbols=False))))
            if not hasattr(symbols,'symbol'):
                raise RuntimeError(f'OpenAPI symbols error: {symbols}')
            by_name={x.symbolName.upper():x for x in symbols.symbol}
            for tv,cfg in self.s.instruments().items():
                item=by_name.get(cfg.ctrader_symbol.upper())
                if not item: raise RuntimeError(f'cTrader symbol not found: {cfg.ctrader_symbol}')
                self.instruments[tv]=ResolvedInstrument(tv,cfg.ctrader_symbol,int(item.symbolId),cfg.volume,cfg.label,cfg.allowed_strategies)
            self.ready=True; self.error=None
            log.info('Ready instruments=%s',{k:v.ctrader_symbol for k,v in self.instruments.items()})
        except Exception as e:
            self.ready=False; self.error=str(e); log.exception('cTrader init failed')
    def instrument(self,tv_symbol):
        x=self.instruments.get(tv_symbol.upper())
        if not x: raise RuntimeError(f'Unsupported symbol: {tv_symbol}')
        return x
    def has_open(self,inst): return self._submit(self._has_open,inst)
    @inlineCallbacks
    def _has_open(self,inst):
        res=Protobuf.extract((yield self.client.send(ProtoOAReconcileReq(ctidTraderAccountId=self.s.ctrader_account_id))))
        return any(p.tradeData.symbolId==inst.symbol_id and p.tradeData.label==inst.label for p in res.position)
    def open(self,inst,action,signal_price,stop_price): return self._submit(self._open,inst,action,signal_price,stop_price)
    @inlineCallbacks
    def _open(self,inst,action,signal_price,stop_price):
        side=ProtoOATradeSide.BUY if action=='ENTRY_LONG' else ProtoOATradeSide.SELL
        rel=int(round(abs(signal_price-stop_price)*100000))
        req=ProtoOANewOrderReq(ctidTraderAccountId=self.s.ctrader_account_id,symbolId=inst.symbol_id,
            orderType=ProtoOAOrderType.MARKET,tradeSide=side,volume=inst.volume,label=inst.label,
            comment='TradingView multi-asset executor',relativeStopLoss=rel)
        out=Protobuf.extract((yield self.client.send(req)))
        return {'response_type':type(out).__name__,'symbol':inst.ctrader_symbol,'symbol_id':inst.symbol_id,'volume':inst.volume,'label':inst.label}
    def close(self,inst,action): return self._submit(self._close,inst,action)
    @inlineCallbacks
    def _close(self,inst,action):
        res=Protobuf.extract((yield self.client.send(ProtoOAReconcileReq(ctidTraderAccountId=self.s.ctrader_account_id))))
        want_buy=action=='EXIT_LONG'; closed=[]
        for p in res.position:
            td=p.tradeData
            if td.symbolId!=inst.symbol_id or td.label!=inst.label: continue
            if (td.tradeSide==ProtoOATradeSide.BUY)!=want_buy: continue
            out=Protobuf.extract((yield self.client.send(ProtoOAClosePositionReq(ctidTraderAccountId=self.s.ctrader_account_id,positionId=p.positionId,volume=p.tradeData.volume))))
            closed.append({'position_id':p.positionId,'response_type':type(out).__name__})
        return {'closed':len(closed),'positions':closed,'symbol':inst.ctrader_symbol,'label':inst.label}
