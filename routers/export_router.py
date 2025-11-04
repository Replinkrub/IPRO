from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
import os
import tempfile
from decimal import Decimal

from services.database import get_db
from services.reports import ProReportBuilder

router = APIRouter()

@router.get("/export/{dataset_id}/excel")
async def export_excel(dataset_id: str, db=Depends(get_db)):
    """Exportar dados para Excel com 5 abas"""
    try:
        # Verificar se o dataset existe
        dataset = db.datasets.find_one({"_id": dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset não encontrado")
        
        # Obter dados necessários
        transactions = list(db.transactions.find({"dataset_id": dataset_id}))
        customer_analytics = list(db.analytics_customer.find({"dataset_id": dataset_id}))
        product_analytics = list(db.analytics_product.find({"dataset_id": dataset_id}))
        alerts = list(db.alerts.find({"dataset_id": dataset_id}))
        
        if not transactions:
            raise HTTPException(status_code=404, detail="Nenhuma transação encontrada")
        
        # Gerar arquivo Excel
        def sanitize(items):
            cleaned = []
            for item in items:
                data = dict(item)
                data.pop('_id', None)
                for key, value in list(data.items()):
                    if isinstance(value, Decimal):
                        data[key] = float(value)
                cleaned.append(data)
            return cleaned

        exporter = ProReportBuilder()
        
        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
            excel_path = tmp_file.name
        
        # Exportar dados
        exporter.build(
            excel_path,
            sanitize(transactions),
            sanitize(customer_analytics),
            sanitize(product_analytics),
            sanitize(alerts)
        )
        
        # Retornar arquivo
        filename = f"IPRO_Export_{dataset_id}_{dataset['created_at'].strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return FileResponse(
            path=excel_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na exportação: {str(e)}")

@router.get("/export/{dataset_id}/csv")
async def export_csv(dataset_id: str, table: str = "transactions", db=Depends(get_db)):
    """Exportar dados específicos para CSV"""
    try:
        # Verificar se o dataset existe
        dataset = db.datasets.find_one({"_id": dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset não encontrado")
        
        # Mapear tabelas
        table_mapping = {
            "transactions": "transactions",
            "customers": "analytics_customer",
            "products": "analytics_product",
            "alerts": "alerts"
        }
        
        if table not in table_mapping:
            raise HTTPException(status_code=400, detail=f"Tabela '{table}' não suportada")
        
        collection_name = table_mapping[table]
        
        # Obter dados
        data = list(db[collection_name].find({"dataset_id": dataset_id}))
        
        if not data:
            raise HTTPException(status_code=404, detail=f"Nenhum dado encontrado para {table}")
        
        # Gerar CSV
        exporter = ExcelExporter()
        
        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
            csv_path = tmp_file.name
        
        # Exportar para CSV
        exporter.export_to_csv(csv_path, data)
        
        # Retornar arquivo
        filename = f"IPRO_{table}_{dataset_id}_{dataset['created_at'].strftime('%Y%m%d_%H%M%S')}.csv"
        
        return FileResponse(
            path=csv_path,
            filename=filename,
            media_type="text/csv"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na exportação CSV: {str(e)}")

