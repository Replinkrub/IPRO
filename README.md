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
7. Variáveis de ambiente (.env)

Um .env.example está no repositório. Copie para .env e edite os valores.

---

## 🗝️ Variáveis (.env)
O arquivo `.env.example` agora é mínimo e traz somente as chaves usadas no código. Copie para `.env` e preencha os valores reais:

| Variável      | Onde é usada                                                        | Como preencher |
|---------------|---------------------------------------------------------------------|----------------|
| `MONGO_URL`   | `services/database.py` → cria o `MongoClient`                       | String de conexão padrão do MongoDB (`mongodb://user:pass@host:port/db`). |
| `DB_NAME`     | `services/database.py` e `core/settings.py` → seleciona o database  | Nome do banco que armazenará datasets do IPRO. |
| `IPRO_API_KEY`| `main.py` (/app-config.js) → entregue ao frontend para autenticação | Gere uma chave segura (GUID ou string randômica) e compartilhe com o time. |
| `APP_PORT`    | `main.py` → porta que o Uvicorn expõe                               | Use `8000` em desenvolvimento ou outro valor conforme sua infraestrutura. |

Opcionalmente você pode definir `HOST`, `ALLOWED_ORIGINS`, `JWT_SECRET` etc. diretamente no ambiente/CI conforme a necessidade, mas eles não são obrigatórios para subir o projeto localmente.

> **Nunca** versione `.env`. Apenas `.env.example` permanece no Git para guiar a configuração.

## 🌐 Endpoints principais

| Método & rota | Descrição |
|---------------|-----------|
| `POST /api/upload-batch` | Recebe múltiplos `.xlsx`, normaliza e persiste o dataset. |
| `GET /api/dataset/{datasetId}/summary` | Retorna visão executiva (clientes, SKUs, período, mix herói). |
| `GET /api/alerts/rico/{datasetId}` | Fornece alertas de ruptura projetada, queda brusca e outliers. |
| `POST /api/extract/base-completa` | Upload rápido para gerar apenas a aba **Base Completa** em `.xlsx`. |
| `GET /app-config.js` | Config dinâmico consumido pelo frontend (baseUrl, API key, JWT curto). |
APP_NAME=ipro
ENVIRONMENT=development   # development|staging|production
DEBUG=false
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Banco / cache (opcionais conforme sua stack)
MONGO_URI=mongodb+srv://<user>:<pass>@<cluster>/<db>?retryWrites=true&w=majority
MONGO_DB=ipro
REDIS_URL=redis://localhost:6379/0

# Segurança
SECRET_KEY=<generate_a_long_random_secret>
JWT_SECRET=<generate_a_long_random_secret>
JWT_EXPIRE_MINUTES=60

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Fuso
TZ=America/Recife


Nunca commitar .env. Use apenas o .env.example no Git.

8. Motor de normalização (Base do IPRO)
8.1. Extração do código da SKU

O código da SKU é o número que precede o hífen no campo Produto.

Padrões válidos reconhecidos:

NN.NN.NNN.NNNN (ex.: 20.07.001.0001)

NN.NNNN (ex.: 01.3016)

Somente dígitos longos (ex.: 2007001000) → convertível para pontuado se bater com os grupos.

Exemplo:

01.1448 - Garfo p/ Churrasco G 45 INOX
→ SKU_CODE_CANON = 01.1448
→ SKU_NAME_CANON = Garfo p/ Churrasco G 45 INOX

8.2. Alias de código (equivalências)

Códigos históricos/compactos/variantes (ex.: 2007001000) apontam para um código canônico (ex.: 20.07.001.0001).

8.3. Nome canônico (descrição)

Várias descrições para o mesmo código → escolher 1 nome oficial (curto, claro, com gramatura quando aplicável).

Um mesmo nome em vários códigos → decidir se é:

Mudança cadastral (antigo/novo) ⇒ manter 1 ativo e mapear os demais como alias/descontinuados.

SKUs distintos (ex.: gramatura/sabor) ⇒ diferenciar no nome (ex.: “300G” vs “200G”).

8.4. Cliente canônico (quando houver coluna de cliente)

Remover sufixos (LTDA, ME, EPP, MATRIZ, FILIAL…), acentos e espaços duplicados.

Sugerir mesclagens com fuzzy-match (similaridade ≥ 0,92), quando implementado.

9. Templates de calibração (acerto fino)

Onde colocar: crie a pasta calibration/ na raiz do projeto.

9.1. calibration/sku_alias.csv

Mapeia códigos observados → código canônico.

Colunas: observed_code,canon_code,notes

2007001000,20.07.001.0001,formato compacto convertido
11FAROFACO,11,alias textual antigo

9.2. calibration/sku_name_canon.csv

Define o nome oficial por código.

Colunas: canon_code,canon_name

20.07.001.0001,FAROFA TRADICIONAL CROCANTE 300G
20.07.001.0002,FAROFA DE COSTELA CROCANTE 300G
01.1448,GARFO P/ CHURRASCO G 45 INOX

9.3. calibration/client_canon.csv (opcional)

Colunas: original,canon
Quando quiser forçar merges de clientes específicos.

Esses arquivos são lidos antes dos cálculos para garantir que tudo esteja uniforme.

10. Como rodar (exemplos)
10.1. Normalização offline (Excel → Excel)

Supondo um módulo de normalização (ajuste o caminho conforme seu projeto):

python -m ipro.tools.normalize \
  --input data/raw/IPRO_Export_2025-09-30.xlsx \
  --out outputs/Base_Normalizada.xlsx \
  --alias calibration/sku_alias.csv \
  --names calibration/sku_name_canon.csv \
  --clients calibration/client_canon.csv

10.2. API (se o projeto expõe FastAPI)
uvicorn ipro.api:app --host 0.0.0.0 --port 8000 --reload
# GET  /health
# POST /process   (envia arquivo .xlsx e recebe base normalizada/insights)


Dica: mantenha outputs/ e data/raw/ fora do Git (já coberto pelo .gitignore).

11. Qualidade

Validações: SKU ↔ Produto, numéricos em pt-BR (, como decimal), subtotal ≈ preço × qtd (tolerância ~1%).

Testes unitários recomendados:

Extração de SKU.

Nome canônico.

Cliente canônico.

Parser numérico de valores em pt-BR.

12. Git & Segurança

.env nunca vai para o repositório. Use apenas .env.example.

.gitignore cobre:

caches do Python, .venv, Excel/CSV, builds, node_modules etc.

Recomenda-se proteger a branch main no GitHub.

13. Troubleshooting

"git" não é reconhecido

Reabra o terminal ou use C:\Program Files\Git\cmd\git.exe.

uvicorn não encontrado

pip install uvicorn fastapi (ou use Poetry).

Erro de locale/decimal ao ler Excel

Normalize vírgula/ponto antes de converter para número.

CORS em dev

Ajuste ALLOWED_ORIGINS no .env.

Timezone

TZ=America/Recife no .env ou configure no sistema.

14. Licença

Uso interno.
Defina a licença conforme a política da organização antes de tornar o repositório público.

15. Créditos

IPRO — Inteligência de Pedidos PRO.
Pipeline de dados criado para dar visão de giro, mix e comportamento de compra em operações B2B.
