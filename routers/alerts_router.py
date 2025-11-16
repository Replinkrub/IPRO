from fastapi import APIRouter, HTTPException, Depends
from fastapi import APIRouter, Depends, HTTPException

from analytics.insights import InsightsGenerator
from services.database import get_db

router = APIRouter()


@router.get("/alerts/rico/{dataset_id}")
async def fetch_rico_alerts(
    dataset_id: str, regenerate: bool = False, db=Depends(get_db)
):
    """Retornar alertas R.I.C.O. calculados pelo motor."""
    try:
        dataset = db.datasets.find_one({"_id": dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset não encontrado")

        filtro_base = {
            "dataset_id": dataset_id,
            "type": {"$in": ["ruptura", "queda_brusca", "outlier_volume"]},
        }
        if not regenerate:
            existentes = list(db.alerts.find(filtro_base))
            if existentes:
                for alert in existentes:
                    alert.pop("_id", None)
                return existentes

        transactions = list(db.transactions.find({"dataset_id": dataset_id}))
        if not transactions:
            raise HTTPException(status_code=404, detail="Nenhuma transação encontrada")

        generator = InsightsGenerator()
        alerts = generator.generate_rico_insights(transactions, dataset_id)

        db.alerts.delete_many(filtro_base)
        if alerts:
            db.alerts.insert_many([alert.dict() for alert in alerts])

        return [alert.dict() for alert in alerts]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro na geração de alertas: {str(e)}"
        )


@router.get("/alerts/{dataset_id}")
async def get_alerts(
    dataset_id: str, alert_type: str = None, reliability: str = None, db=Depends(get_db)
):
    """Obter alertas com filtros opcionais."""
    try:
        # Verificar se o dataset existe
        dataset = db.datasets.find_one({"_id": dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset não encontrado")

        # Construir filtro
        filter_query = {"dataset_id": dataset_id}
        if alert_type:
            filter_query["type"] = alert_type
        if reliability:
            filter_query["reliability"] = reliability

        # Obter alertas
        alerts = list(db.alerts.find(filter_query))

        # Remover _id do MongoDB para serialização
        for alert in alerts:
            if "_id" in alert:
                del alert["_id"]

        return alerts

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter alertas: {str(e)}")


@router.get("/alerts/{dataset_id}/summary")
async def get_alerts_summary(dataset_id: str, db=Depends(get_db)):
    """Obter resumo dos alertas por tipo e confiabilidade."""
    try:
        # Verificar se o dataset existe
        dataset = db.datasets.find_one({"_id": dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset não encontrado")

        # Obter alertas
        alerts = list(db.alerts.find({"dataset_id": dataset_id}))

        # Calcular resumo
        summary = {"total": len(alerts), "by_type": {}, "by_reliability": {}}

        for alert in alerts:
            # Por tipo
            alert_type = alert.get("type", "unknown")
            if alert_type not in summary["by_type"]:
                summary["by_type"][alert_type] = 0
            summary["by_type"][alert_type] += 1

            # Por confiabilidade
            reliability = alert.get("reliability", "unknown")
            if reliability not in summary["by_reliability"]:
                summary["by_reliability"][reliability] = 0
            summary["by_reliability"][reliability] += 1

        return summary

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Erro no resumo de alertas: {str(e)}"
        )
