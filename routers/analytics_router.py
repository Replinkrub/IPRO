from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
fastapi import APIRouter, Depends, HTTPException

import numpy as np
import pandas as pd

from services.database import get_db
from analytics.metrics import MetricsCalculator

router = APIRouter()


def _safe_mean(series):
    s = pd.to_numeric(series, errors="coerce")
    return float(np.nanmean(s)) if len(s) else 0.0


def _compute_kpis_from_payload(payload: dict) -> dict:
    arr = payload.get("customer_analytics") or payload.get("customer_metrics") or []
    cm = pd.DataFrame(arr)
    if cm.empty:
        return {
            "total_clients": 0,
            "avg_recency_days": 0,
            "avg_frequency": 0.0,
            "avg_value": 0.0,
        }
    total = int(cm.shape[0])

    # Recency
    rec_col = next(
        (c for c in ["recency", "R_recency_days", "R_days"] if c in cm.columns), None
    )
    avgR = int(round(_safe_mean(cm[rec_col]))) if rec_col else 0

    # Frequency
    freq_col = next(
        (
            c
            for c in ["order_count", "orders", "F_count", "freq", "frequency"]
            if c in cm.columns
        ),
        None,
    )
    avgF = round(_safe_mean(cm[freq_col]), 1) if freq_col else 0.0

    # Avg Ticket: tenta coluna direta; senão, monetary / orders
    tick_col = next(
        (c for c in ["avg_ticket", "ticket_medio"] if c in cm.columns), None
    )
    if tick_col:
        avgM = float(round(_safe_mean(cm[tick_col]), 2))
    else:
        mon_col = next(
            (c for c in ["monetary", "total_value"] if c in cm.columns), None
        )
        if mon_col and freq_col:
            sum_mon = float(np.nansum(pd.to_numeric(cm[mon_col], errors="coerce")))
            sum_ord = float(np.nansum(pd.to_numeric(cm[freq_col], errors="coerce")))
            avgM = float(round(sum_mon / max(1.0, sum_ord), 2))
        else:
            avgM = 0.0

    return {
        "total_clients": max(0, total),
        "avg_recency_days": max(0, avgR),
        "avg_frequency": max(0.0, avgF),
        "avg_value": max(0.0, avgM),
    }


@router.post("/analyze-customers/{dataset_id}")
async def analyze_customers(dataset_id: str, db=Depends(get_db)):
    """Analisar clientes para KPIs e RFM."""
    try:
        # Verificar se o dataset existe
        dataset = db.datasets.find_one({"_id": dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset não encontrado")

        # Obter transações
        transactions = list(db.transactions.find({"dataset_id": dataset_id}))
        if not transactions:
            raise HTTPException(status_code=404, detail="Nenhuma transação encontrada")

        # Calcular métricas
        calculator = MetricsCalculator()
        customer_analytics = calculator.calculate_customer_rfm(transactions, dataset_id)

        # Salvar analytics no banco
        if customer_analytics:
            # Limpar analytics anteriores
            db.analytics_customer.delete_many({"dataset_id": dataset_id})

            # Inserir novos analytics
            db.analytics_customer.insert_many([ca.dict() for ca in customer_analytics])

        res = {"customer_analytics": [ca.dict() for ca in customer_analytics]}
        res["kpis"] = _compute_kpis_from_payload(res)
        return res

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro na análise de clientes: {str(e)}"
        )


@router.get("/metrics/{dataset_id}/kpis")
async def get_kpis(dataset_id: str, db=Depends(get_db)):
    """Retornar KPIs gerais e de giro."""
    try:
        # Verificar se o dataset existe
        dataset = db.datasets.find_one({"_id": dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset não encontrado")

        # Obter transações
        transactions = list(db.transactions.find({"dataset_id": dataset_id}))
        if not transactions:
            raise HTTPException(status_code=404, detail="Nenhuma transação encontrada")

        # Calcular KPIs
        calculator = MetricsCalculator()
        kpis = calculator.calculate_general_kpis(transactions)

        return kpis

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro no cálculo de KPIs: {str(e)}"
        )


@router.get("/products/{dataset_id}/top")
async def get_top_products(dataset_id: str, by: str = "receita", db=Depends(get_db)):
    """Retornar ranking de SKUs."""
    try:
        # Verificar se o dataset existe
        dataset = db.datasets.find_one({"_id": dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset não encontrado")

        # Obter transações
        transactions = list(db.transactions.find({"dataset_id": dataset_id}))
        if not transactions:
            raise HTTPException(status_code=404, detail="Nenhuma transação encontrada")

        # Calcular ranking
        calculator = MetricsCalculator()
        ranking = calculator.calculate_product_ranking(transactions, by)

        return ranking

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro no ranking de produtos: {str(e)}"
        )


@router.get("/customers/{dataset_id}/segments")
async def get_customer_segments(dataset_id: str, db=Depends(get_db)):
    """Retornar clientes por cluster."""
    try:
        # Verificar se o dataset existe
        dataset = db.datasets.find_one({"_id": dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset não encontrado")

        # Obter transações
        transactions = list(db.transactions.find({"dataset_id": dataset_id}))
        if not transactions:
            raise HTTPException(status_code=404, detail="Nenhuma transação encontrada")

        # Agrupar por segmento
        segments = {}
        for t in transactions:
            segment = t.get("segment", "Não classificado")
            if segment not in segments:
                segments[segment] = {"clients": set(), "revenue": 0, "orders": 0}
            segments[segment]["clients"].add(t["client"])
            segments[segment]["revenue"] += t["subtotal"]
            segments[segment]["orders"] += 1

        # Converter sets para listas e calcular estatísticas
        result = {}
        for segment, data in segments.items():
            result[segment] = {
                "total_clients": len(data["clients"]),
                "total_revenue": data["revenue"],
                "total_orders": data["orders"],
                "avg_ticket": data["revenue"] / data["orders"]
                if data["orders"] > 0
                else 0,
            }

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na segmentação: {str(e)}")


@router.post("/analyze-products/{dataset_id}")
async def analyze_products(dataset_id: str, db=Depends(get_db)):
    """Analisar produtos para métricas e insights"""
    try:
        # Verificar se o dataset existe
        dataset = db.datasets.find_one({"_id": dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset não encontrado")

        # Obter transações
        transactions = list(db.transactions.find({"dataset_id": dataset_id}))
        if not transactions:
            raise HTTPException(status_code=404, detail="Nenhuma transação encontrada")

        # Calcular métricas de produtos
        calculator = MetricsCalculator()
        product_analytics = calculator.calculate_product_analytics(
            transactions, dataset_id
        )

        # Salvar analytics no banco
        if product_analytics:
            # Limpar analytics anteriores
            db.analytics_product.delete_many({"dataset_id": dataset_id})

            # Inserir novos analytics
            db.analytics_product.insert_many([pa.dict() for pa in product_analytics])

        return {
            "total_products": len(product_analytics),
            "product_analytics": [pa.dict() for pa in product_analytics],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro na análise de produtos: {str(e)}"
        )


def _coerce_num(s):
    return pd.to_numeric(s, errors="coerce")


def _load_transactions_df(dataset_id: str) -> pd.DataFrame:
    """
    Carregar transações do dataset como DataFrame
    """
    try:
        from services.database import get_db_connection

        db = get_db_connection()
        transactions = list(db.transactions.find({"dataset_id": dataset_id}))
        if not transactions:
            return pd.DataFrame(
                columns=[
                    "data_emissao",
                    "pedido",
                    "cliente",
                    "criador",
                    "preco_liquido",
                    "quantidade",
                    "subtotal",
                    "produto",
                ]
            )
        return pd.DataFrame(transactions)
    except Exception:
        return pd.DataFrame(
            columns=[
                "data_emissao",
                "pedido",
                "cliente",
                "criador",
                "preco_liquido",
                "quantidade",
                "subtotal",
                "produto",
            ]
        )


@router.get("/dataset/{datasetId}/summary")
def get_dataset_summary(datasetId: str):
    df = _load_transactions_df(datasetId)
    if df.empty:
        return JSONResponse(
            {
                "n_clientes": 0,
                "n_cnpjs": 0,
                "ufs": [],
                "cidades_top": [],
                "periodo": {"inicio": None, "fim": None, "meses": 0},
                "mix": {"n_produtos": 0, "categorias_top": []},
            }
        )

    # Normalizações mínimas
    cols = [str(c).lower().strip() for c in df.columns]
    df.columns = cols

    # Datas
    if "data_emissao" in df.columns:
        dts = pd.to_datetime(df["data_emissao"], errors="coerce")
        dt_min = pd.NaT if dts.isna().all() else dts.min()
        dt_max = pd.NaT if dts.isna().all() else dts.max()
    else:
        dt_min = dt_max = pd.NaT

    # Clientes
    n_clientes = df["cliente"].nunique() if "cliente" in df.columns else 0

    # CNPJs (se houver coluna cnpj)
    n_cnpjs = df["cnpj"].nunique() if "cnpj" in df.columns else 0

    # UF/Cidades (se houver)
    ufs = []
    if "uf" in df.columns:
        ufs = sorted([u for u in df["uf"].dropna().astype(str).unique()[:10]])

    cidades_top = []
    if "cidade" in df.columns:
        cidades_top = (
            df["cidade"].dropna().astype(str).value_counts().head(10).index.tolist()
        )

    # Mix
    n_produtos = df["produto"].nunique() if "produto" in df.columns else 0
    categorias_top = []
    if "categoria" in df.columns:
        categorias_top = (
            df["categoria"].dropna().astype(str).value_counts().head(10).index.tolist()
        )

    meses = 0
    if pd.notna(dt_min) and pd.notna(dt_max):
        meses = max(1, (dt_max.to_period("M") - dt_min.to_period("M")).n + 1)

    return JSONResponse(
        {
            "n_clientes": int(n_clientes),
            "n_cnpjs": int(n_cnpjs),
            "ufs": ufs,
            "cidades_top": cidades_top,
            "periodo": {
                "inicio": None if pd.isna(dt_min) else dt_min.strftime("%Y-%m-%d"),
                "fim": None if pd.isna(dt_max) else dt_max.strftime("%Y-%m-%d"),
                "meses": int(meses),
            },
            "mix": {"n_produtos": int(n_produtos), "categorias_top": categorias_top},
        }
    )


DEFAULT_DELAY_LOGISTICO = 20  # dias


def _compute_rico_alerts(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Regra mínima para MVP:
    - Ruptura: último pedido + giro mediano + delay < hoje  → ALERTA
    - Inatividade: cliente sem pedido > 90 dias
    - Crescimento: variação positiva trimestre vs anterior
    - Oportunidade: SKU comprado 1x e não voltou em >120 dias
    """
    alerts = []
    if df.empty:
        return alerts

    # Normalizar colunas
    cols = [str(c).lower().strip() for c in df.columns]
    df.columns = cols

    # Datas
    if "data_emissao" not in df.columns:
        return alerts
    df["data_emissao"] = pd.to_datetime(df["data_emissao"], errors="coerce")
    df = df.dropna(subset=["data_emissao"])

    today = pd.Timestamp.today().normalize()

    # Ruptura: por cliente+produto
    for (cli, prod), g in df.groupby(["cliente", "produto"], dropna=True):
        g = g.sort_values("data_emissao")
        if g.shape[0] == 0:
            continue

        # dias entre compras
        dts = g["data_emissao"].sort_values().values
        deltas = (
            pd.Series(dts[1:] - dts[:-1]).dt.days
            if len(dts) > 1
            else pd.Series([np.nan])
        )

        giro_mediano = int(np.nanmedian(deltas)) if not deltas.dropna().empty else 45
        ultimo = g["data_emissao"].max()
        limite = ultimo + pd.Timedelta(days=giro_mediano + DEFAULT_DELAY_LOGISTICO)

        status = "OK"
        if (
            today
            >= ultimo
            + pd.Timedelta(days=int(0.75 * (giro_mediano + DEFAULT_DELAY_LOGISTICO)))
            and today < limite
        ):
            status = "ALERTA"
        if today > limite:
            status = "CRITICO"

        if status != "OK":
            alerts.append(
                {
                    "cliente": cli,
                    "produto": prod,
                    "tipo": "Ruptura",
                    "giro_mediano_dias": giro_mediano,
                    "ultimo_pedido": ultimo.strftime("%Y-%m-%d"),
                    "limite": limite.strftime("%Y-%m-%d"),
                    "status": status,
                }
            )

    # Inatividade: por cliente
    ultimos = df.groupby("cliente")["data_emissao"].max()
    inativos = ultimos[(today - ultimos) > pd.Timedelta(days=90)]
    for cli, dt in inativos.items():
        alerts.append(
            {
                "cliente": cli,
                "tipo": "Inatividade",
                "dias_sem_compra": int((today - dt).days),
                "ultimo_pedido": dt.strftime("%Y-%m-%d"),
                "status": "ALERTA",
            }
        )

    # Crescimento (mínimo): comparar soma dos últimos 90 dias vs 90 anteriores (por cliente)
    if "subtotal" in df.columns:
        df["subtotal"] = pd.to_numeric(df["subtotal"], errors="coerce")
    else:
        df["subtotal"] = 0.0

    win = 90
    for cli, g in df.groupby("cliente"):
        g = g.sort_values("data_emissao")
        c_atual = g[g["data_emissao"] >= (today - pd.Timedelta(days=win))][
            "subtotal"
        ].sum()
        c_ant = g[
            (g["data_emissao"] < (today - pd.Timedelta(days=win)))
            & (g["data_emissao"] >= (today - pd.Timedelta(days=2 * win)))
        ]["subtotal"].sum()
        if c_ant > 0 and c_atual > c_ant * 1.2:  # +20% crescimento
            alerts.append(
                {
                    "cliente": cli,
                    "tipo": "Crescimento",
                    "periodo": f"ultimos_{win}_dias",
                    "comparacao": "vs_periodo_anterior",
                    "variacao_perc": round(100 * (c_atual - c_ant) / c_ant, 2),
                    "status": "POSITIVO",
                }
            )

    # Oportunidade: SKU comprado 1x e sem recompra em >120 dias
    freq = df.groupby(["cliente", "produto"]).size().rename("freq").reset_index()
    once = freq[freq["freq"] == 1][["cliente", "produto"]]
    if not once.empty:
        last_buy = df.sort_values("data_emissao").drop_duplicates(
            subset=["cliente", "produto"], keep="last"
        )[["cliente", "produto", "data_emissao"]]
        once = once.merge(last_buy, on=["cliente", "produto"], how="left")
        mask = (today - once["data_emissao"]) > pd.Timedelta(days=120)
        for _, row in once[mask].iterrows():
            alerts.append(
                {
                    "cliente": row["cliente"],
                    "produto": row["produto"],
                    "tipo": "Oportunidade",
                    "motivo": "SKU com 1 compra e sem retorno >120d",
                    "status": "SUGESTAO",
                }
            )

    return alerts


@router.get("/alerts/rico/{datasetId}")
def get_rico_alerts(datasetId: str):
    df = _load_transactions_df(datasetId)
    alerts = _compute_rico_alerts(df)
    return JSONResponse({"datasetId": datasetId, "alerts": alerts})
