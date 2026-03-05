
# IPRO — Inteligência de Pedidos

Motor analítico para detecção de eventos comerciais em dados de vendas B2B.

---

# PROJECT STATUS

Current Version: v7  
Status: development paused  
Last update: 2025-01  

Este repositório contém **o motor analítico do IPRO**.

Não contém interface final de produto ou sistema SaaS completo.

---

# PROJECT PURPOSE

O objetivo do IPRO é analisar histórico de pedidos e detectar eventos comerciais relevantes.

Exemplos:

- risco de ruptura de compra
- queda anormal de faturamento
- comportamento de compra fora do padrão

O sistema gera **alertas estruturados para ação comercial**.

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

IPRO funciona como um **motor de detecção de eventos comerciais**.

Fluxo simplificado:

dataset de transações  
↓  
normalização de dados  
↓  
análise estatística  
↓  
detecção de eventos  
↓  
alertas comerciais

---

# ALERT MODEL

Todos os eventos detectados seguem o mesmo modelo:

Alert

- dataset_id
- client
- sku
- type
- insight
- diagnosis
- recommended_action
- reliability
- suggested_deadline

Este modelo é o núcleo do sistema.

---

# ANALYTICS FRAMEWORK

O sistema utiliza o framework **R.I.C.O.**

R → Ruptura  
I → Instabilidade  
C → Contração  
O → Outlier  

Cada evento detectado pertence a uma dessas categorias.

---

# PROJECT STRUCTURE

IPRO
├ analytics
├ services
├ routers
├ core
├ ipro
├ src
└ tests

analytics → cálculo estatístico e geração de insights  
services → ingestão, normalização e validação de dados  
routers → endpoints da API  
core → configuração do sistema  
ipro/pipeline → processamento de datasets  

---

# DATA MODEL EXPECTED

O motor analítico espera transações com os seguintes campos:

client  
sku  
date  
qty  
subtotal  

Qualquer dataset utilizado deve respeitar essa estrutura.

---

# IMPLEMENTED FEATURES

✔ ingestão de datasets  
✔ normalização de dados  
✔ análise estatística  
✔ geração de alertas  
✔ segmentação de clientes  
✔ exportação de relatórios  

---

# FUTURE FEATURES

- motor de recomendação de pedido
- priorização comercial de alertas
- estimativa de oportunidade financeira
- interface visual
- versão SaaS multi-tenant

---

# TECHNOLOGY STACK

Python  
FastAPI  
Pandas  
NumPy  
Docker  
MongoDB  

---

# DESIGN PRINCIPLE

O IPRO não gera dashboards.

Ele gera **eventos comerciais acionáveis**.

---

# MAINTENANCE NOTE

Este repositório representa uma versão experimental do motor analítico.
Mudanças estruturais podem ocorrer nas próximas versões.
