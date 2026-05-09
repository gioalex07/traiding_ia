# RAC - Robo Advisor / Autonomous Capital

Estado: diseno inicial para MVP productivo-controlado  
Fecha: 2026-05-09  
Principio rector: RAC puede automatizar deteccion, configuracion, analisis y ejecucion en paper trading, pero nunca debe sacrificar control humano, seguridad, trazabilidad, auditoria ni gestion de riesgo.

## 1. Alcance Y Restricciones

RAC es una plataforma modular para analizar mercados financieros, detectar oportunidades, aprender de datos historicos y en tiempo real, ejecutar operaciones automatizadas y operar primero en backtesting y paper trading antes de permitir dinero real.

Restricciones no negociables:

- No prometer rentabilidad garantizada.
- Live trading bloqueado por defecto y nunca activado automaticamente.
- Separacion estricta entre `dev`, `backtest`, `paper` y `live`.
- Toda orden debe pasar por `risk-manager`.
- Ninguna IA puede ejecutar ordenes, modificar limites de riesgo ni cambiar reglas de compliance.
- No usar APIs externas pagas de IA; IA local exclusivamente con Ollama.
- Modo degradado explicito cuando falten dependencias, modelos, broker, GPU, cache, datos o servicios.
- Auditoria completa de senales, prompts, decisiones, ordenes, rechazos y cambios de configuracion.

## 2. Comparativa De Brokers/APIs

Fuentes verificadas en mayo de 2026:

- Alpaca Trading API y paper trading: https://docs.alpaca.markets/docs/trading-api
- Alpaca rate limit: https://alpaca.markets/support/usage-limit-api-calls
- Alpaca crypto fees: https://docs.alpaca.markets/docs/crypto-fees
- Interactive Brokers TWS API: https://interactivebrokers.github.io/
- IBKR TWS limits y paper trading: https://interactivebrokers.github.io/tws-api/introduction.html
- IBKR market data: https://interactivebrokers.github.io/tws-api/market_data.html
- IBKR historical limitations: https://interactivebrokers.github.io/tws-api/historical_limitations.html
- Coinbase Advanced Trade API: https://docs.cdp.coinbase.com/api-reference/advanced-trade-api/rest-api/introduction
- Coinbase WebSocket: https://docs.cdp.coinbase.com/coinbase-business/advanced-trade-apis/websocket/websocket-overview
- Coinbase WebSocket rate limits: https://docs.cdp.coinbase.com/coinbase-business/advanced-trade-apis/websocket/websocket-rate-limits
- Coinbase fees/help: https://help.coinbase.com/en-gb/coinbase/trading-and-funding/advanced-trade/what-is-advanced-trade
- OANDA v20 introduction: https://developer.oanda.com/rest-live-v20/introduction/
- OANDA best practices/rate guidance: https://developer.oanda.com/rest-live-v20/best-practices/
- OANDA pricing: https://www.oanda.com/us-en/trading/our-pricing/
- Binance.US API documentation notice: https://support.binance.us/en/articles/9843443-binance-us-launches-new-api-documentation-portal-for-traders-and-developers
- Binance.US API key/security note: https://support.binance.us/en/articles/9842800-how-to-create-an-api-key-on-binance-us

| Broker/API | Activos | Paper/demo | APIs | Python | Costos | Liquidez | Limits relevantes | Regulacion/compliance | Evaluacion MVP |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Alpaca | Acciones/ETFs USA, opciones segun disponibilidad, crypto | Paper trading gratuito y real-time | REST, WebSocket, SSE | SDK maduro | Acciones/ETFs retail sin comision; crypto por bps segun volumen | Buena para US equities, menor que brokers globales | Trading API aprox. 200 req/min por cuenta | Broker API-first; requiere revisar jurisdiccion del usuario | Mejor MVP para equities por paper simple, REST claro y bajo costo operativo |
| Interactive Brokers | Acciones, ETFs, opciones, futuros, forex, bonos, fondos, crypto segun region | Paper disponible para cuentas aprobadas/fondeadas | TWS/IB Gateway socket, Client Portal REST parcial | Oficial y librerias como ib_insync | Comisiones bajas, datos de mercado usualmente pagos | Muy alta, multi-mercado global | TWS acepta aprox. 50 msg/s; historicos con pacing y 60 req/10 min | Fuerte regulacion; complejo operacionalmente | Excelente fase avanzada; demasiado complejo para primer MVP |
| Binance/Binance.US | Crypto spot principalmente segun jurisdiccion | Testnet depende del producto/region; validar disponibilidad | REST, WebSocket | Excelente ecosistema | Muy competitivo; Binance.US anuncio tarifas spot bajas en 2026 | Alta global; Binance.US mas limitada | WebSocket y REST con limites por peso/conexion; cambios frecuentes | Riesgo regulatorio y disponibilidad por pais/estado | No recomendado como broker unico MVP en US por riesgo regulatorio |
| Coinbase Advanced Trade | Crypto | No es paper trading nativo general para Advanced Trade | REST, WebSocket | SDK/ejemplos disponibles | Maker/taker por volumen, hasta aprox. 0.4/0.6% en tiers basicos segun docs/help | Alta en pares principales, fuerte marca US | WebSocket: limites documentados, 750 conexiones/s por IP y 8 msg/s sin auth | Mejor encaje regulatorio US crypto que Binance | Buen conector crypto, pero falta paper nativo robusto |
| OANDA | Forex/CFDs segun region | Demo/practice | REST v20, streaming, FIX para institucional | Integracion Python sencilla | Spread-only o rebates segun volumen | Alta en FX majors | Recomendado: 2 nuevas conexiones/s, 100 req/s en conexion persistente | Broker FX regulado por division; disponibilidad regional | Excelente si MVP fuera forex; menos generalista que Alpaca |

Recomendacion para MVP: Alpaca.

Razon: ofrece paper trading gratuito y directo, REST/WebSocket simples, buen soporte Python, acciones/ETFs USA como universo inicial comprensible, friccion baja de integracion y menor complejidad operacional que IBKR. RAC debe implementar conectores abstractos desde el inicio para permitir IBKR, OANDA, Coinbase y Binance despues sin reescribir la arquitectura.

Politica de autodeteccion de broker:

- `environment-discovery-service` inspecciona variables de entorno, secretos montados y endpoints alcanzables.
- Si detecta varias configuraciones, no elige live automaticamente; prioriza `paper`, luego `sandbox/demo`, luego `read_only`.
- Si solo hay credenciales live, el sistema queda en `live_blocked` hasta aprobacion humana explicita, doble confirmacion y cambio de politica firmado.
- Si no hay broker valido, RAC arranca en modo `research_only`.

## 3. Arquitectura General

Servicios desacoplados:

- `environment-discovery-service`: inventario de hardware, GPU, RAM, broker, modelos Ollama, bases, cache, bus, servicios, estrategias y datasets.
- `market-data-ingestor`: ingesta OHLCV, trades, quotes, fundamentals disponibles, calendarios, eventos y noticias si son fuentes permitidas.
- `feature-engine`: indicadores tecnicos, features estadisticas, features macro/economicas y normalizacion.
- `strategy-engine`: sistema plug-in de estrategias, validacion de completitud y generacion de senales.
- `model-training`: entrenamiento ML local, tracking de experimentos y seleccion de modelos.
- `backtesting-engine`: simulacion historica aislada, costos, slippage, latencia, walk-forward y metricas.
- `risk-manager`: limites, drawdown, sizing maximo, kill switch, cooldown, validacion pre-trade y post-trade.
- `order-executor`: adaptadores broker, idempotencia, reconciliacion y ejecucion solo despues de aprobacion de riesgo.
- `portfolio-manager`: posiciones, PnL, exposicion, cash, NAV, rebalanceo y conciliacion.
- `local-ai-service`: Ollama, prompts versionados, embeddings locales, explicacion de senales y reportes.
- `notification-service`: alertas Telegram/email, eventos criticos y reportes.
- `observability-service`: metricas, logs, trazas, dashboards y alertas.
- `admin-dashboard`: panel humano para estado, ordenes, cartera, metricas, auditoria y kill switch.

### Diagrama Logico

```text
                         +---------------------------+
                         | admin-dashboard           |
                         | human approval/kill switch|
                         +-------------+-------------+
                                       |
                                       v
+-------------------+      +-----------+-------------+      +------------------+
| environment       |----->| config/capability store |----->| all services     |
| discovery service |      | Postgres + Redis        |      | feature flags    |
+-------------------+      +-------------------------+      +------------------+

+-------------------+      +-------------------------+      +------------------+
| market/broker     |----->| market-data-ingestor    |----->| event bus        |
| APIs              |      | REST/WS adapters        |      | Redpanda/NATS    |
+-------------------+      +-------------------------+      +--------+---------+
                                                                  |
                                                                  v
                +----------------+     +----------------+     +----------------+
                | feature-engine |---->| strategy-engine|---->| signal topic   |
                +-------+--------+     +--------+-------+     +--------+-------+
                        |                       |                      |
                        v                       v                      v
                +---------------+       +---------------+       +--------------+
                | time-series DB|       | local-ai      |       | risk-manager |
                | Timescale/CH  |       | Ollama only   |       +------+-------+
                +-------+-------+       +-------+-------+              |
                        |                       |                      v
                        v                       v              +-------+--------+
                +---------------+       +---------------+      | order-executor |
                | backtesting   |       | audit log     |      | broker adapter |
                | model-training|       | prompts/reply |      +-------+--------+
                +-------+-------+       +---------------+              |
                        |                                              v
                        v                                      +-------+--------+
                +---------------+                              | broker paper   |
                | MLflow/models |                              | live blocked   |
                +---------------+                              +----------------+
```

### Flujo De Datos

1. `environment-discovery-service` publica `capabilities.detected`.
2. `market-data-ingestor` valida broker/data source y publica `market.ohlcv`, `market.quote`, `market.trade`.
3. `feature-engine` consume datos, valida calidad y publica `features.computed`.
4. `strategy-engine` ejecuta plug-ins validos y publica `signals.generated`.
5. `local-ai-service` puede explicar o resumir senales, pero no puede emitir ordenes.
6. `risk-manager` consume senales, portafolio y limites; emite `orders.approved` o `orders.rejected`.
7. `order-executor` solo consume `orders.approved`, crea orden idempotente y envia a broker configurado.
8. `portfolio-manager` reconcilia fills, posiciones y cash.
9. `observability-service` captura metricas, logs, trazas y alertas.
10. `admin-dashboard` muestra estado y permite pausas, desbloqueos controlados y kill switch manual.

### Separacion De Entornos

| Entorno | Proposito | Ordenes reales | Datos | Estado |
| --- | --- | --- | --- | --- |
| `dev` | desarrollo local | No | fixtures/sandbox | permisivo pero auditado |
| `backtest` | simulacion historica | No | historico versionado | aislado de broker |
| `paper` | simulacion broker | No | real-time/paper | MVP activo |
| `live` | dinero real | Si, condicionado | real-time live | bloqueado por defecto |

Controles de separacion:

- Bases separadas por entorno o schemas estrictamente prefijados.
- Topics separados: `paper.orders.approved` no puede mezclarse con `live.orders.approved`.
- Credenciales separadas y scopes minimos.
- Configuracion `RAC_TRADING_MODE=paper` por defecto.
- `RAC_LIVE_TRADING_ENABLED=false` por defecto.
- Live requiere `RAC_LIVE_TRADING_ENABLED=true`, secreto `LIVE_UNLOCK_TOKEN`, aprobacion humana en dashboard, checklist de produccion y doble confirmacion.

## 4. Stack Tecnologico Final

Backend:

- Python 3.12+
- FastAPI
- Pydantic v2
- SQLAlchemy/Alembic
- httpx, websockets, tenacity

Procesamiento:

- `asyncio` para I/O concurrente.
- Redpanda como bus Kafka-compatible recomendado para MVP.
- NATS como alternativa liviana autodetectable.
- Kafka completo para produccion con mayor escala.

Persistencia:

- PostgreSQL como sistema transaccional.
- TimescaleDB para OHLCV, indicadores, senales y metricas temporales en MVP.
- ClickHouse opcional para analytics masivo.
- Redis para cache, locks, idempotencia y rate limiting.
- pgvector como opcion simple de embeddings; Qdrant si se requiere busqueda vectorial dedicada.

ML:

- scikit-learn para baselines.
- XGBoost/LightGBM para tabular.
- PyTorch para modelos secuenciales o deep learning cuando haya evidencia de valor.
- MLflow para experimentos, artefactos y modelos.

GPU:

- CUDA solo si se detecta NVIDIA compatible y el workload lo justifica.
- RAPIDS/cuDF para ETL/feature engineering grande.
- CuPy para computo numerico vectorizado.
- CPU por defecto para MVP pequeno/mediano.

IA local:

- Ollama como runtime exclusivo.
- Modelos instalados autodetectados.
- Prompts versionados y auditados.
- Embeddings locales opcionales; si faltan, vectorizacion desactivada sin romper el sistema.

Observabilidad:

- Prometheus, Grafana, Loki, OpenTelemetry.

Orquestacion:

- Docker Compose para MVP.
- Kubernetes para produccion.

Seguridad:

- Variables de entorno en desarrollo.
- Vault o secret manager compatible para produccion.
- Contenedores no-root.
- MFA obligatoria en broker.
- API keys sin permisos de retiro cuando el broker lo permita.

## 5. Local AI Service Con Ollama

Uso permitido:

- Explicacion de senales.
- Reportes para humanos.
- Resumen de backtests.
- Analisis semantico de eventos, documentos internos o teoria economica.
- Clasificacion textual de noticias/documentos si se incorporan fuentes autorizadas.
- Asistente de diagnostico operacional.

Uso prohibido:

- Ejecutar ordenes.
- Modificar reglas de riesgo.
- Cambiar limites.
- Desbloquear live trading.
- Reescribir estrategias activas sin revision humana.
- Tomar decisiones finales de asignacion de capital.

Seleccion automatica:

1. Consultar `GET /api/tags` de Ollama.
2. Probar latencia con prompts cortos estandarizados.
3. Registrar memoria estimada y estabilidad.
4. Clasificar modelos:
   - `analysis`: modelo general estable.
   - `summary`: modelo rapido de menor latencia.
   - `classification`: modelo rapido/estable.
   - `technical_reasoning`: modelo mas capaz disponible.
   - `embeddings`: modelo embedding si existe.
5. Si no hay Ollama: `local_ai.status=disabled`.
6. Si no hay embedding model: `embeddings.status=disabled`, sin fallo global.

Contratos principales:

```http
GET /health
GET /capabilities
POST /v1/explain-signal
POST /v1/summarize-backtest
POST /v1/classify-document
POST /v1/embed
```

Toda solicitud registra:

- `prompt_template_id`
- `prompt_version`
- `model_name`
- `model_digest` si esta disponible
- parametros
- input hash
- output
- latencia
- usuario/servicio solicitante
- entorno
- correlacion con senal, backtest u orden

## 6. Estrategias

Sistema plug-in:

```text
strategies/
  trend_following/
    strategy.py
    manifest.yaml
  mean_reversion/
  breakout/
  volatility_filter/
  ensemble/
```

Contrato minimo de estrategia:

- `name`
- `version`
- `supported_assets`
- `required_features`
- `generate_signal(context) -> Signal`
- `stop_loss_rule`
- `take_profit_rule`
- `position_sizing_rule`
- `invalidation_rules`
- `risk_tags`
- `min_data_points`
- `backtest_required=true`

Estrategias iniciales:

- Trend following: medias moviles, momentum, ADX opcional.
- Mean reversion: z-score, Bollinger Bands, RSI, distancia a media.
- Breakout: ruptura de rango, volumen, confirmacion de volatilidad.
- Volatility filter: filtro transversal para activar/desactivar exposicion.
- Ensemble: combinacion ponderada de senales con reglas explicitas, no caja negra.

Validacion automatica:

- No activar si falta stop loss, take profit, sizing o invalidacion.
- No activar si no hay backtest aprobado.
- No activar si faltan features requeridas.
- No activar si excede limites por activo, tipo de activo o frecuencia.
- No activar si version del plug-in no esta firmada/aprobada para entorno.

## 7. Gestion De Riesgo

`risk-manager` es obligatorio y sin bypass.

Limites minimos:

- Perdida maxima diaria.
- Perdida maxima semanal.
- Capital maximo por operacion.
- Exposicion maxima por activo.
- Exposicion maxima por clase de activo.
- Maximo numero de posiciones simultaneas.
- Maximo numero de ordenes por minuto/hora.
- Drawdown maximo desde high-water mark.
- Cooldown por racha de perdidas.
- Kill switch automatico por perdida, errores API, divergencia de cartera, latencia o datos corruptos.
- Kill switch manual desde dashboard.

Politica de orden:

```text
signal -> pre_trade_validation -> sizing -> risk decision -> approved/rejected -> order-executor
```

Una orden rechazada registra razon estructurada:

- `limit_daily_loss`
- `limit_weekly_loss`
- `limit_asset_exposure`
- `invalid_stop_loss`
- `missing_take_profit`
- `cooldown_active`
- `kill_switch_active`
- `stale_market_data`
- `broker_unavailable`
- `live_blocked`

## 8. Ejecucion De Ordenes

`BrokerAdapter` abstracto:

```python
class BrokerAdapter:
    async def capabilities(self) -> BrokerCapabilities: ...
    async def get_account(self) -> AccountSnapshot: ...
    async def get_positions(self) -> list[Position]: ...
    async def submit_order(self, order: OrderRequest) -> OrderAck: ...
    async def cancel_order(self, broker_order_id: str) -> CancelAck: ...
    async def stream_fills(self) -> AsyncIterator[FillEvent]: ...
```

Implementaciones:

- `AlpacaBrokerAdapter`
- `IBKRBrokerAdapter`
- `BinanceBrokerAdapter`
- `CoinbaseAdvancedTradeAdapter`
- `OandaBrokerAdapter`

Soporte inicial:

- Market
- Limit
- Stop
- Stop-limit cuando el broker lo soporte

Controles:

- Idempotency key obligatoria: `env:strategy:signal_id:order_intent_hash`.
- Validacion de simbolo, precision, tick size, min notional y horario.
- Registro completo de payload normalizado y respuesta broker.
- Reconciliacion periodica de ordenes/fills/posiciones.
- Circuit breaker por broker.

## 9. Datos Y Base De Datos

### Entidades Principales

```text
environments
capabilities
brokers
assets
market_data_ohlcv
market_quotes
features
economic_theory_documents
mathematical_theory_documents
document_embeddings
strategies
strategy_versions
signals
risk_decisions
orders
fills
positions
portfolio_snapshots
backtests
backtest_metrics
model_runs
model_artifacts
ai_prompt_templates
ai_interactions
audit_events
notifications
kill_switch_events
```

### Diseno Logico DB

PostgreSQL:

- Configuracion, usuarios, permisos, auditoria, ordenes, fills, estrategias, prompts y governance.

TimescaleDB:

- `market_data_ohlcv(time, broker, symbol, timeframe, open, high, low, close, volume, source_quality)`
- `features(time, symbol, feature_set, values_jsonb)`
- `signals(time, strategy_id, symbol, direction, confidence, raw_payload)`
- `portfolio_snapshots(time, nav, cash, exposure_jsonb, pnl_daily, drawdown)`
- `system_metrics(time, service, metric, value, labels_jsonb)`

pgvector/Qdrant:

- Teoria economica y matematica.
- Documentos internos de estrategia.
- Reportes y explicaciones versionadas.

Tablas para teoria economica y matematica:

```sql
economic_theory_documents(
  id uuid primary key,
  title text not null,
  domain text not null,
  source_type text not null,
  source_uri text,
  license text,
  content_hash text not null,
  version int not null,
  created_at timestamptz not null
)

mathematical_theory_documents(
  id uuid primary key,
  title text not null,
  topic text not null,
  notation_system text,
  source_type text not null,
  source_uri text,
  license text,
  content_hash text not null,
  version int not null,
  created_at timestamptz not null
)

document_embeddings(
  id uuid primary key,
  document_id uuid not null,
  document_type text not null,
  embedding_model text not null,
  embedding vector,
  chunk_text text not null,
  chunk_hash text not null,
  created_at timestamptz not null
)
```

Uso de teoria:

- Recuperacion semantica para explicar regimenes, tendencias, inflacion, tasas, ciclos, volatilidad, correlaciones y supuestos matematicos.
- Nunca como fuente unica para operar.
- Siempre con trazabilidad a documento, version, licencia y fecha.

Validaciones:

- Datos incompletos: gaps, velas faltantes, timezone, mercado cerrado.
- Outliers: z-score robusto, winsorization opcional, comparacion multi-fuente si existe.
- Normalizacion: split/dividend adjustment para equities, precision por broker, timezone UTC.
- Staleness: ninguna senal operable si los datos exceden TTL por timeframe.

## 10. Seguridad Y Compliance

Controles minimos:

- No hardcodear claves.
- Secretos en variables de entorno solo para local; Vault en produccion.
- API keys por entorno y permisos minimos.
- Retiro/desposito deshabilitado en APIs cuando el broker lo permita.
- MFA obligatoria en broker.
- Separacion fisica/logica de paper/live.
- Auditoria append-only para eventos criticos.
- Firma/versionado de estrategias y reglas de riesgo.
- Contenedores no-root.
- Imagenes escaneadas.
- SBOM en CI.
- Dependencias fijadas.
- Politicas de retencion de logs.
- Cifrado en transito y en reposo.
- RBAC en dashboard.
- Revision humana para live.

Compliance financiero:

- RAC debe presentarse como software de analisis/ejecucion controlada, no como garantia de retorno.
- Reportes deben incluir supuestos, riesgos, periodo, costos, slippage y limitaciones.
- Mantener registros de decisiones y ordenes.
- Implementar suitability/appropriateness si se ofrece a terceros.
- Revisar regulacion local antes de operar dinero real o gestionar capital de terceros.

## 11. Contenerizacion

Servicios minimos MVP:

- `api`
- `worker`
- `scheduler`
- `postgres`
- `redis`
- `redpanda`
- `grafana`
- `prometheus`
- `loki`
- `mlflow`
- `ollama` opcional por perfil/local host

Perfiles:

- `dev`
- `backtest`
- `paper`
- `live-blocked`
- `gpu`
- `observability`

GPU:

- Requiere NVIDIA Container Toolkit.
- El sistema debe detectar GPU antes de activar workloads CUDA.
- Si no hay GPU, continuar en CPU.

## 12. CI/CD

GitHub Actions:

- `ruff`/lint.
- `mypy` o pyright.
- Unit tests.
- Integration tests con servicios.
- Contract tests para adaptadores broker con mocks.
- Backtest regression tests.
- Security scan: pip-audit, Trivy/Grype, secret scanning.
- Build de imagenes.
- SBOM.
- Bloqueo de deploy si falla cualquier control requerido.
- Deploy live requiere ambiente protegido, aprobadores y checklist.

## 13. Observabilidad

Metricas:

- PnL diario/semanal/mensual.
- Drawdown.
- Win rate.
- Profit factor.
- Sharpe/Sortino en backtests.
- Exposicion por activo/clase.
- Ordenes aprobadas/rechazadas.
- Rechazos por razon.
- Latencia API broker.
- Errores API broker.
- Staleness de datos.
- Drift de features/modelos.
- Uso CPU/RAM/GPU.
- Latencia local AI.
- Fallos de Ollama/modelos.

Alertas:

- Kill switch activado.
- Perdida diaria cerca del limite.
- Drawdown excedido.
- Broker caido.
- Datos stale.
- Divergencia cartera RAC vs broker.
- Error rate alto.
- Latencia excesiva.
- Intento de live trading bloqueado.
- Cambio de estrategia/riesgo.

Canales:

- Telegram.
- Email.
- Webhook interno.

## 14. Dashboard

Vistas:

- Estado del bot: modo, broker detectado, capacidades, servicios.
- Portafolio: NAV, cash, posiciones, exposiciones.
- Ordenes: intentos, aprobadas, rechazadas, fills, broker ack.
- Riesgo: limites, drawdown, cooldowns, kill switch.
- Estrategias: activas, invalidas, version, backtest aprobado.
- Backtests: metricas, equity curve, parametros, costos.
- ML: modelos, experimentos, drift, version activa.
- IA local: modelos Ollama, prompts, latencia, interacciones.
- Logs/auditoria: filtro por correlacion, orden, senal, usuario.
- Kill switch: activar manualmente, requiere confirmacion y motivo.

## 15. Autodeteccion Del Sistema

Capacidades a detectar:

- Hardware: CPU, RAM, disco, GPU, CUDA.
- Ollama: endpoint, modelos instalados, embedding models.
- Broker: variables/secretos, entorno paper/live, endpoints.
- Bases: PostgreSQL, Timescale, ClickHouse opcional.
- Cache: Redis.
- Bus: Redpanda/Kafka/NATS.
- Servicios activos: health checks.
- Estrategias validas.
- Datos disponibles: cobertura historica, gaps, calidad.

Estados degradados:

| Falta | Modo |
| --- | --- |
| Broker | `research_only` |
| Redis | sin cache distribuida, no trading automatico |
| Bus | modo local/dev solamente |
| Ollama | sin explicaciones IA |
| Embeddings | busqueda vectorial desactivada |
| GPU | CPU |
| Datos historicos | sin backtest/aprendizaje |
| Risk-manager | sistema no opera |
| Postgres | sistema no inicia modo trading |

Reglas:

- Nunca fallar silenciosamente.
- Nunca asumir capacidades no verificadas.
- Nunca activar live trading automaticamente.
- Publicar un reporte de capacidades al arranque.
- Exponer `GET /capabilities` por servicio.

## 16. Contratos De Servicios

Eventos base:

```json
{
  "event_id": "uuid",
  "event_type": "signals.generated",
  "schema_version": "1.0",
  "environment": "paper",
  "correlation_id": "uuid",
  "created_at": "2026-05-09T00:00:00Z",
  "producer": "strategy-engine",
  "payload": {}
}
```

Topics recomendados:

- `capabilities.detected`
- `market.ohlcv`
- `market.quote`
- `features.computed`
- `signals.generated`
- `risk.decisions`
- `orders.approved`
- `orders.rejected`
- `orders.submitted`
- `orders.filled`
- `portfolio.snapshots`
- `ai.interactions`
- `audit.events`
- `alerts.critical`

APIs minimas:

```http
GET /health
GET /ready
GET /capabilities
GET /metrics
POST /admin/pause
POST /admin/resume
POST /admin/kill-switch
```

## 17. Roadmap

Fase 0: investigacion

- Definir jurisdiccion, universo inicial y broker MVP.
- Crear threat model.
- Definir politicas de riesgo.
- Elegir stack final.

Fase 1: datos

- Ingesta Alpaca paper/market data.
- Modelo OHLCV.
- Validacion de calidad.
- TimescaleDB.

Fase 2: backtesting

- Motor de backtesting aislado.
- Costos, slippage, walk-forward.
- Reportes y MLflow.

Fase 3: paper trading

- BrokerAdapter Alpaca.
- Risk-manager obligatorio.
- Order-executor idempotente.
- Reconciliacion y dashboard basico.

Fase 4: ML

- Baselines sklearn/XGBoost/LightGBM.
- Feature store inicial.
- Drift y seleccion de modelos.
- GPU solo si hay ganancia medible.

Fase 5: dashboard

- Admin operacional.
- Kill switch.
- Auditoria navegable.
- Reportes IA local.

Fase 6: live controlado

- Checklist produccion.
- Revision legal/compliance.
- Limites microscopicos iniciales.
- Aprobacion humana por despliegue.

Fase 7: optimizacion

- Multi-broker.
- Portfolio construction.
- Mejoras de latencia.
- Kubernetes.
- Hardening SRE.

## 18. Backlog Tecnico

Prioridad P0:

- Crear estructura monorepo.
- Configuracion central con Pydantic.
- Docker Compose dev/paper.
- Postgres/Timescale/Redis/Redpanda.
- `environment-discovery-service`.
- Contratos de eventos.
- `risk-manager` inicial.
- `BrokerAdapter` abstracto.
- `AlpacaBrokerAdapter` paper.
- Auditoria append-only.
- Kill switch manual y automatico.

Prioridad P1:

- Ingesta OHLCV.
- Feature-engine.
- Estrategias trend/mean/breakout.
- Backtesting engine.
- MLflow.
- Observabilidad Prometheus/Grafana/Loki.
- Local AI con Ollama.

Prioridad P2:

- Dashboard completo.
- Embeddings teoria economica/matematica.
- Ensemble.
- Drift detection.
- NATS/Kafka autodetect.
- Coinbase/OANDA adapters en paper/sandbox si aplica.

Prioridad P3:

- Kubernetes.
- Vault.
- IBKR adapter.
- ClickHouse.
- GPU/RAPIDS.
- Live controlado.

## 19. Analisis De Riesgos

| Riesgo | Impacto | Mitigacion |
| --- | --- | --- |
| Perdidas financieras | Alto | Paper primero, limites duros, kill switch, live bloqueado |
| Sobreajuste | Alto | Walk-forward, out-of-sample, costos/slippage, regression tests |
| Datos corruptos/stale | Alto | Validacion, TTL, gaps, circuit breaker |
| Fallo broker/API | Alto | Retries limitados, circuit breaker, reconciliacion |
| IA alucinando | Medio/alto | IA solo explica, no ejecuta ni cambia riesgo |
| Secretos expuestos | Alto | Vault, no hardcode, scans, permisos minimos |
| Mezcla paper/live | Alto | Entornos, topics, DB y credenciales separadas |
| Riesgo regulatorio | Alto | Revision legal, logs, disclaimers, no gestion de terceros sin marco legal |
| Drift de mercado | Medio/alto | Monitoreo, cooldown, reentrenamiento controlado |
| GPU innecesaria/costo | Medio | CPU por defecto, benchmarks antes de activar |

## 20. Criterios De Paso A Produccion

Live trading solo puede considerarse si:

- Backtests reproducibles y aprobados.
- Paper trading estable por un periodo definido, por ejemplo 60-90 dias, sin incidentes criticos.
- Max drawdown y perdidas dentro de limites.
- Risk-manager con tests unitarios, integracion y caos.
- Kill switch probado manual y automatico.
- Reconciliacion broker vs RAC sin divergencias materiales.
- Secretos en Vault o equivalente.
- CI/CD bloqueante activo.
- Observabilidad y alertas funcionando.
- Runbooks de incidentes.
- Revision legal/compliance.
- Aprobacion humana documentada.
- Limites live iniciales muy bajos.
- Rollback probado.

## 21. Perfil Financiero Y Economista

RAC debe incorporar una capa de conocimiento financiero/economico sin confundirla con una autorizacion automatica para operar.

Responsabilidades del perfil financiero:

- Definir universo de activos y restricciones.
- Validar supuestos de costos, liquidez, slippage y horarios.
- Revisar metricas de performance y riesgo.
- Aprobar politicas de asignacion y limites.

Responsabilidades del perfil economista:

- Mantener repositorio de teoria economica relevante.
- Definir variables macro, regimenes y escenarios.
- Interpretar tendencias, tasas, inflacion, crecimiento, empleo, liquidez y ciclos.
- Documentar supuestos teoricos usados en analisis.

Base de conocimiento:

- Teoria economica.
- Finanzas cuantitativas.
- Estadistica y probabilidad.
- Algebra lineal, optimizacion, series temporales.
- Microestructura de mercado.
- Gestion de portafolio.
- Regulacion y compliance.

Esta base debe ser versionada, trazable, consultable por embeddings locales y citada en reportes. No debe reemplazar validacion empirica, gestion de riesgo ni aprobacion humana.
