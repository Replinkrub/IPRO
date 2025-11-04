# IPRO — Inteligência de Pedidos PRO

O **IPRO** é um motor de **inteligência comercial** para pedidos B2B.

Ele pega as planilhas “tortas” do CRM/ERP (produto escrito de qualquer jeito, cliente duplicado, datas e valores bagunçados), **normaliza a base**, calcula **métricas críticas de giro e comportamento** e devolve **relatórios prontos para decisão** — do representante, da indústria e do cliente final.

> Não é “só um normalizador de planilhas”.  
> A normalização é a 1ª camada. O objetivo final é **decidir melhor o próximo pedido**.

---

## 1. Problema que o IPRO resolve

Na prática, o cenário é este:

- Cada extração do CRM vem com:
  - Produto escrito de mil jeitos diferentes.
  - Códigos antigos misturados com códigos novos.
  - Cliente duplicado (MATRIZ/FILIAL, LTDA/ME/EPP etc.).
  - Datas, quantidades e valores sem padrão.
- Com isso, fica **caro e demorado** responder perguntas simples:
  - Qual é o giro real de cada cliente?
  - Quem está em ruptura, inativo ou crescendo? (R.I.C.O.)
  - Qual mix ideal por cliente?
  - Qual o melhor pedido para fechar **agora**?

O **IPRO** entra como uma pipeline única que:

1. **Limpa e padroniza** o histórico de pedidos.  
2. **Calcula métricas de giro, recorrência e mix.**  
3. **Organiza insights em abas/relatórios prontos para ação.**

---

## 2. O que o IPRO entrega (visão de produto)

### 2.1. Camadas do IPRO

1. **Camada de Base (Normalização)**
   - Normalização de produtos (SKU).
   - Alias & deduplicação de códigos.
   - Cliente canônico.
   - Validação numérica (`subtotal ≈ preço × quantidade`).

2. **Camada de Métricas**
   - GIRO por cliente e por SKU.
   - Ciclo de recompra.
   - Volume médio por pedido.
   - Sazonalidade básica (janelas de tempo).
   - Flags R.I.C.O. (Ruptura, Inatividade, Crescimento, Oportunidade).

3. **Camada de Insights & Saídas**
   - Relatórios em Excel com múltiplas abas.
   - Endpoints de API (FastAPI) para integrar com sistemas externos.
   - Base pronta para agentes de IA/automação (Replink, n8n etc.).

### 2.2. Saída padrão (modelo V2)

O modelo de entrega do IPRO foca em 5 blocos principais (típico arquivo Excel com 5 abas):

1. **Identificação do Cliente**  
   - Dados canônicos do cliente, cluster, perfil de compra.

2. **Histórico Comercial**  
   - Linha do tempo de pedidos, ticket médio, giro, volume por período.

3. **Inteligência de Mix**  
   - Mix atual vs. mix potencial.  
   - Produtos centrais, ocasionais e oportunidades de encaixe.

4. **Relacional e Atendimento**  
   - Ciclos de visita, janelas de pedido, descolamento entre “momento ideal” e “momento real”.

5. **Inteligência Comportamental**  
   - Flags R.I.C.O., padrão de recorrência, variação de volume e sinais de risco.

> A camada de normalização é o “motor”.  
> Essas abas são o **produto final** que o usuário de negócio enxerga.

---

## 3. Estado atual do projeto

Para evitar confusão, o IPRO é organizado em **estado atual** vs. **roadmap**:

### 3.1. Implementado (em desenvolvimento contínuo)

- ✅ Estrutura de projeto em Python (pastas `core/`, `analytics/`, `services/`, `routers/`, `src/`).
- ✅ Normalização de produtos (SKU) a partir da coluna “Produto”.
- ✅ Regras para alias de código e nome canônico via arquivos de calibração.
- ✅ Cliente canônico (limpeza de sufixos, acentos, variações).
- ✅ Validações de consistência numérica básicas.
- ✅ Setup com `.env.example`, `.gitignore`, Dockerfile e docker-compose.

### 3.2. Em construção / planejado

- ⏳ Cálculo consolidado de GIRO por cliente/SKU.  
- ⏳ Flags R.I.C.O. com parâmetros configuráveis.  
- ⏳ Geração automática das 5 abas padrão de saída.  
- ⏳ API `/process` recebendo Excel e devolvendo arquivos processados.  

> O repositório acompanha esse roadmap.  
> À medida que as features são implementadas, esta seção é atualizada.

---

## 4. Arquitetura do projeto

Visão geral das principais pastas:

- `core/`  
  Lógica de base: parsers, normalização de SKU, cliente canônico, leitura de calibrações.

- `analytics/`  
  Cálculo de métricas (giro, ciclos, indicadores de comportamento) e geração de DataFrames prontos para relatórios.

- `services/`  
  Serviços de infraestrutura (banco, cache, filas, etc.), quando usados.

- `routers/`  
  Rotas da API (FastAPI), como `/health`, `/process`, etc.

- `src/`  
  Código de suporte, utilitários, entrypoints específicos.

- `main.py`  
  Ponto de entrada da aplicação (ex.: instancia a API).

- `Dockerfile` / `docker-compose.yml`  
  Arquivos para rodar o IPRO em containers.

---

## 5. Pré-requisitos

- Python **3.11+** (recomendado)  
- `pip` ou **Poetry**  
- (Opcional) **MongoDB** e **Redis**, se sua instalação usar persistência/filas  
- Windows, macOS ou Linux

---

## 6. Setup rápido (Windows / PowerShell)

```powershell
# 1) Clone o repositório
git clone https://github.com/Replinkrub/IPRO.git
cd IPRO

# 2) Crie o ambiente virtual e instale dependências
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Se houver requirements.txt
pip install -r requirements.txt

# OU (se houver pyproject.toml e Poetry)
# pip install poetry
# poetry install

# 3) Configure variáveis de ambiente
Copy-Item .env.example .env
# -> preencha os valores reais no arquivo .env

# 4) (Opcional) rode a API se existir um app FastAPI
# ajuste o módulo conforme o projeto (ex.: ipro.api:app ou ipro.main:app)
uvicorn ipro.api:app --reload --host 0.0.0.0 --port 8000
