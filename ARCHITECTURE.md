# IPRO — Architecture Overview

Este documento descreve a arquitetura técnica do **IPRO V2**.

---

# System Overview

O IPRO é um **motor analítico de priorização comercial por ciclo**.

Ele transforma histórico transacional em **decisão comercial acionável**, ajudando equipes comerciais a identificar:

- quem abordar
- quando abordar
- sobre qual produto ou mix abordar
- com qual prioridade

O IPRO não é CRM, ERP ou BI.

Sua função é ler dados operacionais e devolver **inteligência prática para execução comercial**.

Pipeline geral:

`dataset → extract → normalize → validate → metrics → classification → decision → outputs`

---

# Architectural Principle

O IPRO foi projetado para ser um **motor analítico modular e desacoplado da interface**.

Isso permite:

- reutilização do motor em diferentes contextos
- integração com CRM, painéis ou automações
- evolução gradual sem acoplar regra de negócio ao front
- expansão futura para arquitetura SaaS multi-tenant

Princípio central:

**CRM registra.  
IPRO decide.**

---

# Core Modules

## analytics

Responsável por cálculo analítico, classificação de comportamento e geração de saídas operacionais.

Principais responsabilidades:

- cálculo de métricas por cliente
- cálculo de métricas por cliente x produto
- definição de janelas de recompra
- classificação de risco e prioridade
- geração de diagnóstico e recomendação

Principais arquivos:

- `estatistica.py` → funções estatísticas de apoio
- `metrics.py` → métricas analíticas
- `insights.py` → geração de diagnósticos, ações e alertas
- `segmentador_pdv.py` → classificação de clientes e segmentação operacional

---

## services

Camada responsável por ingestão, estruturação e processamento de dados.

Principais componentes:

- `extractor` → leitura de datasets
- `normalizer` → padronização de dados
- `validator` → validação estrutural e semântica
- `models` → definição de contratos e modelos
- `reports` → construção de relatórios
- `exporter` → exportação de dados processados

Essa camada garante que o motor trabalhe com dados consistentes antes da etapa analítica.

---

## routers

Camada de exposição da API do sistema.

Principais endpoints:

- `/dataset`
- `/analytics`
- `/priorities`
- `/alerts`
- `/export`

Esses endpoints permitem integração com outros sistemas, especialmente CRM e interfaces operacionais.

---

## core

Infraestrutura básica do sistema.

Contém:

- `settings` → configurações globais
- `logger` → sistema de logs
- `utils` → utilidades compartilhadas
- `dependencies` → dependências comuns entre módulos

---

## pipeline

Responsável pelo encadeamento do fluxo completo de transformação analítica.

Função principal:

orquestrar a passagem dos dados pelas etapas de ingestão, normalização, validação, cálculo, classificação e geração de saída operacional.

---

# Data Flow

Fluxo completo do sistema:

1. dataset é carregado
2. dados são extraídos e estruturados
3. dados são normalizados
4. dataset é validado
5. métricas de comportamento são calculadas
6. cliente e cliente x produto são classificados
7. decisões comerciais são geradas
8. saídas operacionais e alertas são produzidos

---

# Analytical Model

A V2 opera em dois níveis complementares.

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

Objetivo:

determinar o momento comercial do cliente e sua janela de recompra.

---

## 2. Customer × Product Layer

Responsável por entender o comportamento do SKU dentro de cada cliente.

Principais métricas:

- última compra do SKU
- dias sem comprar o SKU
- frequência de compra do SKU
- ciclo médio do SKU naquele cliente
- percentual do ciclo consumido do SKU
- atraso do SKU em relação ao padrão esperado

Objetivo:

antecipar reposição com granularidade real, evitando abordagem genérica.

---

# Classification Logic

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

# Decision Engine

Após o cálculo das métricas e classificação dos padrões, o IPRO transforma análise em decisão operacional.

A saída principal do sistema responde:

- quem deve ser abordado
- com qual urgência
- sobre qual item
- com qual racional
- com qual ação sugerida

O sistema não existe apenas para detectar desvios estatísticos, mas para orientar execução comercial com base em comportamento real.

---

# Outputs

A principal saída do IPRO V2 é a geração de itens de prioridade comercial.

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

Além disso, o sistema pode gerar listas operacionais separadas por estágio:

- aquecimento
- ataque
- risco
- histórico insuficiente

---

# Alert Generation

Alertas continuam existindo, mas como camada complementar ao motor de priorização.

Alertas são produzidos a partir de mecanismos como:

### Ruptura

Cliente ou SKU deixa de comprar dentro do ciclo esperado.

### Queda brusca

Redução relevante no faturamento ou no volume dentro de um padrão previamente estabelecido.

### Outlier de volume

Compra muito acima ou abaixo do comportamento histórico.

### Instabilidade

Oscilação excessiva sem padrão confiável.

Esses alertas servem para reforçar a leitura comercial, não para substituir a decisão principal por ciclo.

---

# Alert Structure

Todos os alertas seguem um modelo comum:

- `dataset_id`
- `client`
- `sku`
- `type`
- `insight`
- `diagnosis`
- `recommended_action`
- `reliability`
- `suggested_deadline`

---

# Design Constraints

A V2 segue algumas restrições intencionais:

- não acoplar regra de negócio ao front-end
- não depender de dashboard complexo para gerar valor
- não transformar o motor em CRM
- não sofisticar score antes de consolidar a régua básica
- não usar IA como substituto para lógica operacional confiável

---

# Future Architecture Evolution

Possíveis evoluções futuras:

- recomendação de pedido ou mix
- priorização avançada com múltiplos pesos
- cálculo de valor de oportunidade
- integração nativa com CRM
- automação de abordagem comercial
- painel visual operacional
- arquitetura SaaS multi-tenant

Essas evoluções devem respeitar o princípio de manter o motor enxuto, confiável e orientado à decisão.

---

# Final Principle

O IPRO não foi projetado para apenas analisar o passado.

Ele foi projetado para **antecipar a próxima ação comercial com base em ciclo, comportamento e contexto transacional**.
