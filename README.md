# IPRO — Inteligência de Pedidos PRO (MVP Técnico)

Este repositório contém o MVP técnico do **IPRO**, um pipeline + API para:
- receber planilhas Excel (`.xlsx`) de pedidos/vendas,
- **extrair e normalizar** colunas (mesmo quando variam de nome),
- salvar datasets em **MongoDB**,
- gerar **métricas (RFM / Mix / KPIs)**,
- e **exportar relatórios em Excel**.

> Status: **em desenvolvimento**. Existem rotas e módulos legados dentro do repo. Este README descreve **o que está no código hoje** e lista as pendências reais para produção.

---

## O que existe no código (de verdade)

### Backend (FastAPI)
- `main.py` — aplicação FastAPI
- `routers/` — endpoints `/api/...`
  - `dataset_router.py` — upload/processamento/summary
  - `alerts_router.py` — alertas R.I.C.O
  - `export_router.py` — export de Excel (atualmente legado)
  - `analytics_router.py` — **WIP** (há inconsistências/duplicidades)

### Pipeline / Serviços
- `services/extractor.py` — leitura e extração de `.xlsx`
- `services/schema_aliases.py` — aliases de nomes de colunas
- `ipro/pipeline/normalize.py` — **normalização canônica** (colunas padrão)
- `analytics/metrics.py` — métricas (RFM, KPIs, produto)
- `services/report_builder.py` — **gera Excel padrão V2 (5 abas)**

### Frontend estático (painel simples)
- `src/static/index.html` — UI simples para upload e consumo de rotas

### Banco (MongoDB)
- `docker-compose.yml` + `init-mongo.js` — cria usuário e coleções:
  - `datasets`, `transactions`, `customers`, `analytics_customer`, `analytics_product`, `requests`

---

## Rotas principais (as que fazem sentido como core)

> Prefixo: `/api`

### 1) Upload batch (grava no Mongo)
`POST /api/upload-batch`

- multipart/form-data com `files[]`
- cria `dataset_id`
- extrai dados e grava `transactions` e `customers`

### 2) Processar um arquivo e devolver Excel (V2 - 5 abas)
`POST /api/process`

- recebe 1 arquivo `.xlsx`
- devolve um `.xlsx` com 5 abas padrão:
  1. Identificação do Cliente
  2. Histórico Comercial
  3. Inteligência de Mix
  4. Relacional e Atendimento
  5. Inteligência Comportamental

### 3) Resumo do dataset
`GET /api/dataset/{dataset_id}/summary`

### 4) Alertas R.I.C.O
`GET /api/alerts/rico/{dataset_id}`

### 5) Export Excel do dataset
`GET /api/export/{dataset_id}/excel`

> Atenção: hoje este export usa um builder legado (`services/reports.py`) e não está alinhado ao padrão V2 de 5 abas.
> Para produção, a recomendação é padronizar tudo no `services/report_builder.py`.

---

## Variáveis de ambiente

Usadas no código:

- `MONGO_URL` (default: mongodb://localhost:27017)
- `DB_NAME` (default: ipro)
- `APP_PORT` (default: 8000; também lê `PORT`)
- `IPRO_API_KEY` (chave de API; existe suporte em `core/dependencies.py`, mas ainda não está aplicado nas rotas)
- `JWT_SECRET` (referenciado no app, mas o módulo de auth ainda está em consolidação)
- `ALLOWED_ORIGINS` (CORS; lista separada por vírgula)
- `TIMEZONE` (default: America/Sao_Paulo)
- `MAX_INSERT_BATCH` (default: 5000)
- `CHUNK_ROWS` (default: 50000)
- `PRODUCTION_ENV` (se "true", reduz verbosidade do logger)

Exemplo mínimo (`.env`):
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=ipro
APP_PORT=8000
IPRO_API_KEY=trocar_esta_chave
TIMEZONE=America/Sao_Paulo
ALLOWED_ORIGINS=http://localhost:5000
