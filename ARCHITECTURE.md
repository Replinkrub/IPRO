
# IPRO — Architecture Overview

Este documento descreve a arquitetura técnica do motor analítico IPRO.

---

# System Overview

O IPRO é um **pipeline analítico para detecção de eventos comerciais**.

Ele transforma transações de vendas em **alertas acionáveis** para equipes comerciais.

Pipeline geral:

dataset → extract → normalize → validate → analytics → insights → alerts

---

# Core Modules

## analytics

Responsável por cálculo estatístico e geração de insights.

Principais arquivos:

- estatistica.py → funções estatísticas
- insights.py → geração de alertas
- metrics.py → métricas analíticas
- segmentador_pdv.py → classificação de clientes

---

## services

Camada responsável por ingestão e processamento de dados.

Principais componentes:

- extractor → leitura de datasets
- normalizer → padronização de dados
- validator → validação estrutural
- models → definição de modelos
- reports → construção de relatórios
- exporter → exportação de dados

---

## routers

Exposição da API do sistema.

Principais endpoints:

/dataset  
/analytics  
/alerts  
/export  

Esses endpoints permitem integração com outros sistemas.

---

## core

Infraestrutura básica do sistema.

Contém:

- settings → configurações globais
- logger → sistema de logs
- utils → utilidades
- dependencies → dependências compartilhadas

---

## pipeline

Responsável pelo fluxo de transformação de datasets.

Função principal:

normalizar dados antes da análise estatística.

---

# Data Flow

Fluxo completo do sistema:

1. dataset é carregado
2. dados são normalizados
3. dataset é validado
4. métricas estatísticas são calculadas
5. eventos são detectados
6. alertas são gerados

---

# Alert Generation

Alertas são produzidos a partir de três mecanismos principais:

### Ruptura

Cliente deixa de comprar dentro do ciclo esperado.

### Queda brusca

Redução estatisticamente significativa no faturamento.

### Outlier de volume

Compra fora do padrão histórico.

---

# Alert Structure

Todos os alertas seguem o modelo:

dataset_id  
client  
sku  
type  
insight  
diagnosis  
recommended_action  
reliability  
suggested_deadline  

---

# Future Architecture Evolution

Possíveis evoluções:

- camada de recomendação de pedido
- sistema de priorização de alertas
- cálculo de valor de oportunidade
- painel visual
- arquitetura SaaS multi-tenant

---

# Architectural Principle

O IPRO foi projetado para ser um **motor analítico modular**.

Isso permite:

- reutilização do motor analítico
- integração com múltiplas interfaces
- evolução para SaaS no futuro
