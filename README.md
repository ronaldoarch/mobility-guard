# Mobility Guard

[![CI](https://github.com/ronaldoarch/mobility-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/ronaldoarch/mobility-guard/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![Next.js](https://img.shields.io/badge/Next.js-16-black)
![License](https://img.shields.io/badge/license-portfolio-lightgrey)

Plataforma de engenharia de IA para cobranças de mobilidade. Registra transações, detecta
anomalias com regras auditáveis, enriquece explicações de forma assíncrona e apresenta a operação
em um dashboard responsivo.

## Stack

- Python 3.12+, FastAPI, Pydantic e arquitetura hexagonal.
- PostgreSQL + SQLAlchemy em produção; SQLite como fallback local.
- Alembic para migrações versionadas.
- Redis + Celery para enriquecimento assíncrono.
- OpenAI Responses API opcional, com fallback determinístico.
- Next.js 16, React 19 e TypeScript strict no dashboard.
- Prometheus, request ID, healthcheck, Docker Compose, Ruff, mypy e pytest.

## Executar sem Docker

O modo local usa SQLite e não exige Redis nem chave externa.

```bash
make install
make check
make run
```

Em outro terminal:

```bash
cd dashboard
npm install
npm run dev
```

- Dashboard: [http://localhost:3000](http://localhost:3000)
- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)
- Métricas: [http://localhost:8000/metrics](http://localhost:8000/metrics)

## Executar a stack completa

Com o Docker Desktop ativo:

```bash
docker compose up --build
```

O Compose inicia PostgreSQL, Redis, API, worker Celery e dashboard. A API executa `alembic
upgrade head` antes de aceitar tráfego.

Para habilitar explicações generativas, copie `.env.example` para `.env` e configure
`OPENAI_API_KEY`. Identificadores de cliente não são enviados ao provedor.

## Fluxo assíncrono

1. A API valida a entrada e calcula um score determinístico.
2. A transação é persistida antes da publicação na fila.
3. O cliente recebe a resposta sem esperar pelo provedor generativo.
4. O worker enriquece a explicação e atualiza `enrichment_status`.
5. Se a fila estiver indisponível, a cobrança permanece registrada e o status muda para `failed`.

Esse desenho evita que uma dependência externa interrompa o caminho crítico da transação.

## API

```text
POST /v1/transactions
GET  /v1/transactions?customer_id=...
GET  /v1/transactions/{external_id}
GET  /v1/customers/{customer_id}/billing-summary
GET  /health
GET  /metrics
```

Exemplo:

```bash
curl -X POST http://localhost:8000/v1/transactions \
  -H 'Content-Type: application/json' \
  -d '{
    "external_id": "tx-001",
    "customer_id": "customer-001",
    "amount": "12.50",
    "occurred_at": "2026-08-17T14:30:00-03:00",
    "category": "toll",
    "merchant": "Rodovia SP-123 Km 42"
  }'
```

Defina `API_KEY` para proteger os endpoints e envie seu valor no header `X-API-Key`.

## Detecção atual

- possível duplicidade no mesmo estabelecimento em até cinco minutos;
- valor fora do padrão por mediana e desvio absoluto mediano;
- transação em horário pouco usual;
- sinalização explícita quando ainda há pouco histórico.

O score combina os sinais por `1 - produto(1 - peso)`. O limiar padrão é `0.65`. As regras são
uma baseline explicável para triagem e não devem ser tratadas como decisão definitiva de fraude.

## Qualidade e migrações

```bash
make check             # Ruff + mypy strict + pytest
make dashboard-check   # ESLint + TypeScript + build Next.js
make seed              # dados sintéticos no backend local
alembic upgrade head   # aplica migrações usando DATABASE_URL
```

Veja [docs/architecture.md](docs/architecture.md) para limites, decisões e evolução sugerida.
Não use dados pessoais reais neste projeto de portfólio.

