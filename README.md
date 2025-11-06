# IPRO — Inteligência de Pedidos PRO

Sistema focado em **padronização de dados comerciais**, **cálculo de métricas** e **insights acionáveis** para decisão de compra/venda (R.I.C.O., giro, mix, recorrência, etc.).
Este repositório foi preparado para uso seguro em time/produção, com `.gitignore` robusto e `.env.example` documentado.

---

## ✨ O que o IPRO resolve
- **Normalização de produtos (SKU)**: extrai o **código da SKU** do início do campo *Produto* e canoniza o **nome da SKU** (descrição após o hífen).
- **Alias & deduplicação**: mapeia códigos antigos/variantes para um **código canônico**; consolida nomes múltiplos num **nome oficial**.
- **Cliente canônico** (quando houver): remove sufixos (LTDA/ME/EPP…), acentos e variações para agrupar o mesmo CNPJ/cliente.
- **Métricas e insights**: base pronto para GIRO, R.I.C.O., ranking de mix, ciclo de recompra, etc.
- **Saídas prontas**: *Excel* de apoio (base canônica, relatórios de mismatch, templates de alias/nomenclatura).

> **Importante**: nunca faça contas com dados “quebrados”. O IPRO prioriza **validar & padronizar** antes de calcular.

---

## 🧱 Pré‑requisitos
- **Python 3.11+** (recomendado)
- **pip** ou **Poetry**
- (**Opcional**) **MongoDB** e **Redis** se sua instalação usar persistência/filas
- Windows, macOS ou Linux

---

## ⚙️ Setup rápido (Windows / PowerShell)

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
```

> No Linux/macOS, use `source .venv/bin/activate` para ativar o venv.

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

---

## 🧼 Regras de normalização de SKU / Produto

### 1) Extração do **código da SKU**
- O **código da SKU** é o número que **precede o hífen** no campo *Produto*.
- Padrões válidos reconhecidos:
  - `NN.NN.NNN.NNNN` (ex.: `20.07.001.0001`)
  - `NN.NNNN` (ex.: `01.3016`)
  - Somente dígitos longos (ex.: `2007001000`) → convertível para pontuado se bater com os grupos.
- Ex.:  
  `01.1448 - Garfo p/ Churrasco G 45 INOX`  
  → **SKU_CODE_CANON = `01.1448`**  
  → **SKU_NAME_CANON = `Garfo p/ Churrasco G 45 INOX`**

### 2) Alias de código (equivalências)
- Códigos históricos/compactos/variantes (ex.: `2007001000`) devem apontar para **um código canônico** (ex.: `20.07.001.0001`).

### 3) Nome canônico (descrição)
- Várias descrições para o mesmo código → **escolher 1 nome oficial** (curto, claro, com gramatura quando aplicável).
- Um mesmo nome em **vários códigos** → decidir se é:
  - **Mudança cadastral** (antigo/novo) ⇒ manter 1 **ativo** e mapear os demais como **alias** ou **descontinuados**;
  - **SKU distintos** (ex.: gramatura/sabor) ⇒ **diferenciar no nome** (e.g., “300G” vs “200G”).

### 4) Cliente canônico (quando houver coluna de cliente)
- Remover sufixos (`LTDA`, `ME`, `EPP`, `MATRIZ`, `FILIAL`…), acentos e espaços duplicados.
- Sugerir mesclagens com fuzzy‑match (similaridade ≥ **0,92**).

---

## 🗂️ Templates de calibração (para acerto fino)
> **Onde colocar**: crie a pasta `calibration/` na raiz do projeto e salve lá.

- **`calibration/sku_alias.csv`**  
  Mapeia códigos observados → **código canônico**.  
  **Colunas**: `observed_code,canon_code,notes`  
  Ex.:  
  ```csv
  2007001000,20.07.001.0001,formato compacto convertido
  11FAROFACO,11,alias textual antigo
  ```

- **`calibration/sku_name_canon.csv`**  
  Define **o nome oficial** por código.  
  **Colunas**: `canon_code,canon_name`  
  Ex.:  
  ```csv
  20.07.001.0001,FAROFA TRADICIONAL CROCANTE 300G
  20.07.001.0002,FAROFA DE COSTELA CROCANTE 300G
  01.1448,GARFO P/ CHURRASCO G 45 INOX
  ```

- **`calibration/client_canon.csv`** *(opcional)*  
  **Colunas**: `original,canon` (quando quiser forçar merges de clientes).

> Esses arquivos são **lidos antes dos cálculos** para garantir que tudo esteja uniforme.

---

## ▶️ Como rodar (exemplos)

### A) Normalização offline (Excel → Excel)
Supondo um módulo de normalização (ajuste o caminho conforme seu projeto):
```bash
python -m ipro.tools.normalize \
  --input data/raw/IPRO_Export_2025-09-30.xlsx \
  --out outputs/Base_Normalizada.xlsx \
  --alias calibration/sku_alias.csv \
  --names calibration/sku_name_canon.csv \
  --clients calibration/client_canon.csv
```

### B) API (se o projeto expõe FastAPI)
```bash
uvicorn ipro.api:app --host 0.0.0.0 --port 8000 --reload
# GET  /health
# POST /process  (envia arquivo .xlsx e recebe base normalizada/insights)
```

> **Dica**: mantenha `outputs/` e `data/raw/` fora do Git (já coberto pelo `.gitignore`).

---

## 🧪 Qualidade
- Validações: `SKU ↔ Produto`, numéricos em pt‑BR (`,` como decimal), `subtotal≈preço×qtd` (tolerância 1%).
- Testes unitários (sugestão): extração de SKU, canon de nome, canon de cliente, parser numérico.

---

## 🧹 Git & Segurança
- `.env` **nunca** vai para o repositório. Use apenas `.env.example`.
- `.gitignore` já cobre: caches Python, `.venv`, Excel/CSV, builds, node_modules, etc.
- Proteja a branch `main` no GitHub (opcional).

---

## 🆘 Troubleshooting
- **“git não é reconhecido”**: reabra o terminal ou use `C:\Program Files\Git\cmd\git.exe`.  
- **`uvicorn` não encontrado**: `pip install uvicorn fastapi` (ou use Poetry).  
- **Erro de locale/decimal** ao ler Excel: normalize vírgula/ponto antes de converter para número.  
- **CORS** em dev: ajuste `ALLOWED_ORIGINS` no `.env`.  
- **Timezone**: `TZ=America/Recife` no `.env` ou configure no sistema.

---

## 📄 Licença
Uso interno. Defina a licença conforme a política da organização.

---

## ✍️ Créditos
IPRO — pipeline de **Inteligência de Pedidos**.
