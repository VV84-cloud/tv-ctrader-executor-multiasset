# TradingView → cTrader Multi-Asset Executor

Unterstützt Öl und Gold in derselben Railway-Instanz.

## Routing
- `WTOIL-PERP` → `SPOTCRUDE`, Label `TV_OIL_3_0`
- `XAUUSD` → `XAUUSD`, Label `TV_GOLD_1_6`

Jedes Instrument hat eigene Strategie-Whitelist, Volume und Label. Exits schließen nur Positionen mit passendem Symbol, passender Richtung und passendem Label.

## Railway-Migration
1. Vorhandenes Repository sichern.
2. Ordner `app`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `.env.example` durch diese Version ersetzen.
3. Railway-Variablen aus `.env.example` ergänzen. Bestehende cTrader-Zugangsdaten und `WEBHOOK_TOKEN` nicht ändern.
4. Zunächst `DRY_RUN=true` setzen und deployen.
5. `/health` muss beide Mappings unter `symbols` anzeigen.
6. Gold-Dry-Run über `/docs` testen.
7. Erst danach `DRY_RUN=false` und Demo-Entry/Exit testen.

## Gold Testpayload
```json
{
  "strategy":"GOLD_1_6_A8V120_CORE_0800_1200_1400_1800",
  "action":"ENTRY_LONG",
  "symbol":"XAUUSD",
  "signal_price":4165.50,
  "stop_price":4155.50,
  "bar_time":1760210800000
}
```

Zum Testen mit historischem `bar_time` vorübergehend `MAX_SIGNAL_AGE_SECONDS=0`; anschließend wieder auf `300` setzen.

## Gold Pine Webhook-ID
Das Pine-Skript muss exakt `GOLD_1_6_A8V120_CORE_0800_1200_1400_1800` senden. Wenn dein aktueller Pine-Code eine andere ID sendet, trage genau diese in `GOLD_STRATEGIES` ein.

## Gold Volume
`GOLD_VOLUME=100` ist nur ein konservativer Startwert. Im Pepperstone-Demokonto prüfen, welche Lotgröße daraus resultiert, bevor Livebetrieb aktiviert wird.
