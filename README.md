# IPRO — Inteligência de Pedidos

Motor analítico de priorização comercial por ciclo para dados de vendas B2B.

---

# PROJECT STATUS

Current Version: v7  
Status: architecture under revision  
Last update: 2026-03

Este repositório contém **o motor analítico do IPRO**.

Não contém interface final de produto nem sistema SaaS completo.

---

# PROJECT PURPOSE

O objetivo do IPRO é transformar histórico de pedidos em **decisão comercial acionável**.

Em vez de apenas detectar eventos estatísticos, o sistema busca responder:

- quem abordar
- quando abordar
- sobre qual produto ou mix abordar
- com qual prioridade

O foco é padronizar a leitura comercial com base em:

- comportamento do cliente
- comportamento do produto dentro do cliente
- ciclo de compra
- janela de recompra
- risco de atraso

---

# NON GOALS

Este projeto **não é**:

- sistema de ERP
- sistema de CRM
- sistema de BI / dashboard
- sistema de gestão de estoque

Qualquer funcionalidade relacionada a essas áreas está **fora do escopo do IPRO**.

---

# CORE CONCEPT

O IPRO funciona como um **motor de priorização comercial por ciclo**.

Fluxo simplificado:

dataset de transações  
↓  
extração e estruturação  
↓  
normalização  
↓  
validação  
↓  
cálculo de métricas  
↓  
classificação de comportamento  
↓  
decisão comercial  
↓  
saídas operacionais e alertas

Princípio central:

**CRM registra.  
IPRO decide.**

---

# ANALYTICAL MODEL

A V2 opera em dois níveis complementares:

## 1. Customer Layer

Responsável por entender o comportamento global de compra do cliente.

Principais métricas:

- último pedido
- dias sem comprar
- frequência
- ticket médio
- ciclo médio de compra
- percentual do ciclo consumido
- atraso em relação ao ciclo esperado

## 2. Customer × Product Layer

Responsável por entender o comportamento do SKU dentro de cada cliente.

Principais métricas:

- última compra do SKU
- dias sem comprar o SKU
- frequência de compra do SKU
- ciclo médio do SKU naquele cliente
- percentual do ciclo consumido do SKU
- atraso do SKU em relação ao padrão esperado

Esse modelo evita abordagem genérica e permite antecipar reposição com mais precisão.

---

# CLASSIFICATION LOGIC

A principal régua operacional do IPRO é baseada no consumo do ciclo.

Fórmula central:

`cycle_consumption_pct = days_since_last_purchase / avg_cycle_days`

Classificação padrão:

- `< 0.50` → frio
- `0.50 a < 0.80` → aquecimento
- `0.80 a <= 1.20` → ataque
- `> 1.20` → risco

Essa lógica deve existir tanto no nível do cliente quanto no nível cliente x produto.

---

# OUTPUT MODEL

A principal saída do sistema é um item de prioridade comercial.

Estrutura esperada:

- `customer`
- `sku`
- `days_since_last_purchase`
- `avg_cycle_days`
- `cycle_consumption_pct`
- `reorder_window_status`
- `priority_score`
- `risk_level`
- `diagnosis`
- `recommended_action`
- `suggested_message`
- `confidence`

O objetivo não é apenas medir comportamento, mas orientar execução comercial.

---

# ALERT MODEL

Alertas continuam existindo, mas como camada complementar ao motor principal.

Todos os alertas seguem o mesmo modelo:

## Alert

- `dataset_id`
- `client`
- `sku`
- `type`
- `insight`
- `diagnosis`
- `recommended_action`
- `reliability`
- `suggested_deadline`

Esses alertas ajudam a reforçar a leitura comercial, especialmente em casos de:

- ruptura
- instabilidade
- contração
- outlier

---

# ANALYTICS FRAMEWORK

O sistema utiliza o framework **R.I.C.O.** como camada complementar de leitura de eventos:

- **R** → Ruptura
- **I** → Instabilidade
- **C** → Contração
- **O** → Outlier

Cada evento detectado pertence a uma dessas categorias.

Na V2, esse framework deixa de ser a identidade central do produto e passa a atuar como suporte analítico para a decisão comercial.

---

# PROJECT STRUCTURE

IPRO  
├── analytics  
├── services  
├── routers  
├── core  
├── ipro  
├── src  
└── tests  

- `analytics` → cálculo analítico, classificação e geração de insights
- `services` → ingestão, normalização, validação e exportação
- `routers` → endpoints da API
- `core` → configuração e infraestrutura do sistema
- `ipro/pipeline` → orquestração do fluxo de processamento

---

# DATA MODEL EXPECTED

O motor analítico espera transações com os seguintes campos mínimos:

- `client`
- `sku`
- `date`
- `qty`
- `subtotal`

Dependendo da evolução da V2, campos adicionais poderão ser suportados para melhorar a confiabilidade do cálculo de ciclo e priorização.

---

# IMPLEMENTED FEATURES

- ingestão de datasets
- normalização de dados
- validação estrutural
- análise estatística
- geração de alertas
- segmentação de clientes
- exportação de relatórios

---

# TARGET FEATURES FOR V2

- cálculo de ciclo por cliente
- cálculo de ciclo por cliente x produto
- classificação de janela de recompra
- priorização comercial por item
- diagnóstico operacional
- ação recomendada
- mensagem sugerida
- integração leve com CRM

---

# FUTURE FEATURES

- recomendação de pedido ou mix
- priorização avançada com múltiplos pesos
- estimativa de oportunidade financeira
- interface visual operacional
- integração nativa com CRM
- automação comercial
- versão SaaS multi-tenant

---

# TECHNOLOGY STACK

- Python
- FastAPI
- Pandas
- NumPy
- Docker
- MongoDB

---

# DESIGN PRINCIPLE

O IPRO não foi projetado para gerar dashboards.

Ele foi projetado para gerar **decisão comercial acionável**.

Seu papel é antecipar a próxima ação com base em:

- ciclo
- comportamento
- contexto transacional

---

# MAINTENANCE NOTE

Este repositório representa uma versão em evolução do motor analítico do IPRO.

A arquitetura e os contratos internos podem sofrer mudanças conforme a V2 consolida a transição de um modelo centrado em eventos para um modelo centrado em priorização comercial por ciclo.
