import hashlib
import logging
import os
import tempfile
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import uuid4

import pandas as pd
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse
from pymongo.errors import BulkWriteError, DuplicateKeyError

from analytics.metrics import MetricsCalculator
from core.utils import utc_now
from services.database import get_db
from services.extractor import DataExtractor
from services.models import DatasetSummary, UploadResponse
from services.normalizer import DataNormalizer
from services.report_builder import (
    build_report_dataframes,
    convert_transactions_to_records,
    safe_remove,
    write_report_excel,
)
from services.validator import DataValidator

logger = logging.getLogger(__name__)

router = APIRouter()


def get_file_hash(content: bytes) -> str:
    h = hashlib.sha256()
    h.update(content or b"")
    return h.hexdigest()


@router.post("/upload-batch", response_model=UploadResponse)
async def upload_batch(
    request: Request, files: List[UploadFile] = File(...), db=Depends(get_db)
):
    """Upload de múltiplos arquivos .xlsx."""
    try:
        idem = (
            request.headers.get("Idempotency-Key")
            or hashlib.sha256(os.urandom(16)).hexdigest()
        )
        already = db.requests.find_one({"idempotency_key": idem})
        if already:
            return {"dataset_id": str(already["dataset_id"]), "status": "DUPLICATE_OK"}

        # Always use a string for the dataset identifier.  MongoDB stores
        # ObjectIds/strings but comparisons between UUID instances and
        # strings will fail.  Convert here for consistency across the
        # application.
        dataset_id = str(uuid4())
        total_rows = 0
        all_hash_parts = []

        # Criar diretório para o dataset
        dataset_dir = f"data/inbox/{dataset_id}"
        os.makedirs(dataset_dir, exist_ok=True)

        # Processar cada arquivo
        extractor = DataExtractor()
        validator = DataValidator()
        normalizer = DataNormalizer()

        for file in files:
            if not file.filename.lower().endswith(".xlsx"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Arquivo {file.filename} não é um .xlsx válido",
                )

            # Ler conteúdo do arquivo
            content = await file.read()  # ler UMA vez
            file_hash = get_file_hash(content)
            all_hash_parts.append(file_hash)

            # Evitar reprocessar arquivo idêntico já salvo
            if db.datasets.find_one({"hash": file_hash}):
                continue

            file_path = os.path.join(dataset_dir, file.filename)
            with open(file_path, "wb") as f:
                f.write(content)

            # Extrair dados
            if (
                "cadastro" in file.filename.lower()
                or "cliente" in file.filename.lower()
            ):
                # Processar como cadastro de clientes
                customers_data = extractor.extract_customers(file_path)
                if customers_data:
                    # Salvar clientes no banco.  Para permitir normalização posterior,
                    # armazenamos o nome normalizado como chave e preservamos o nome
                    # original em 'original_name'.  Isso evita divergências quando
                    # DataNormalizer procura clientes já cadastrados.
                    for customer in customers_data:
                        original_name = customer["name"]
                        normalized_name = normalizer._normalize_client_name(
                            original_name
                        )
                        customer_to_upsert = customer.copy()
                        customer_to_upsert["name"] = normalized_name
                        customer_to_upsert["original_name"] = original_name
                        db.customers.update_one(
                            {"name": normalized_name},
                            {"$set": customer_to_upsert},
                            upsert=True,
                        )
            else:
                # Processar como relatório de pedidos
                transactions_data = extractor.extract_transactions(file_path)

                if transactions_data:
                    # Validar dados
                    validated_data = validator.validate_transactions(transactions_data)

                    # Normalizar dados
                    normalized_data = normalizer.normalize_transactions(
                        validated_data, dataset_id
                    )

                    # Salvar transações no banco
                    if normalized_data:
                        # Convert Decimal fields to floats to avoid serialization errors in MongoDB
                        tx_docs = []
                        for t in normalized_data:
                            doc = t.dict()
                            # Convert price and subtotal from Decimal to float if needed
                            if isinstance(doc.get("price"), Decimal):
                                doc["price"] = float(doc["price"])
                            if isinstance(doc.get("subtotal"), Decimal):
                                doc["subtotal"] = float(doc["subtotal"])
                            tx_docs.append(doc)
                        if tx_docs:
                            try:
                                # Use ordered=False to continue inserting even if duplicates hit unique indexes
                                result = db.transactions.insert_many(
                                    tx_docs, ordered=False
                                )
                                # Count successfully inserted documents
                                total_rows += len(result.inserted_ids)
                            except BulkWriteError as bwe:
                                # In case of duplicates (duplicate key errors), only count successfully inserted ones
                                details = bwe.details or {}
                                total_rows += details.get("nInserted", 0)

        # Salvar metadados do dataset.
        # Inicialmente definimos status PROCESSING e calculamos o hash do dataset.
        dataset_hash = hashlib.sha256("".join(all_hash_parts).encode()).hexdigest()
        dataset_doc = {
            "_id": dataset_id,
            "name": ", ".join([f.filename for f in files]),
            "status": "PROCESSING",
            "created_at": utc_now(),
            "hash": dataset_hash,
            "files": [f.filename for f in files],
            "stats": {"rows": 0, "errors": 0},
        }
        try:
            db.datasets.update_one(
                {"_id": dataset_id}, {"$set": dataset_doc}, upsert=True
            )
        except DuplicateKeyError:
            # Se já existe um dataset com o mesmo hash, reutilize o dataset existente
            existing = db.datasets.find_one({"hash": dataset_hash})
            if existing:
                # Use o ID existente para todas as referências
                dataset_id = str(existing.get("_id"))
            else:
                # Se não conseguir encontrar, relance o erro
                raise

        # Atualizar status final e estatísticas para o dataset identificado (novo ou existente)
        db.datasets.update_one(
            {"_id": dataset_id},
            {
                "$set": {
                    "status": "READY",
                    "stats.rows": total_rows,
                    "stats.errors": 0,
                    "finished_at": utc_now(),
                }
            },
            upsert=True,
        )

        # Registrar a chave de idempotência para evitar reprocessamento
        try:
            db.requests.insert_one(
                {
                    "idempotency_key": idem,
                    "dataset_id": dataset_id,
                    "created_at": utc_now(),
                }
            )
        except Exception:
            # Se houver conflito de chave idempotência, ignore
            pass

        return UploadResponse(
            dataset_id=dataset_id,
            rows=total_rows,
            started_at=dataset_doc.get("created_at", utc_now()),
            status="READY",
        )

    except Exception as e:
        db.datasets.update_one(
            {"_id": dataset_id},
            {"$set": {"status": "FAILED", "error": str(e), "finished_at": utc_now()}},
        )
        raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")


@router.post("/process")
async def process_single_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db=Depends(get_db),
):
    """Processar um único arquivo Excel e devolver o consolidado com 5 abas."""

    _ = db  # força inicialização da conexão para reutilizar cadastros
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .xlsx válido")

    extractor = DataExtractor()
    validator = DataValidator()
    normalizer = DataNormalizer()
    dataset_id = str(uuid4())
    tmp_input_path: Optional[str] = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_in:
            tmp_input_path = tmp_in.name
            content = await file.read()
            if not content:
                raise HTTPException(
                    status_code=400, detail="Arquivo enviado está vazio"
                )
            tmp_in.write(content)
            tmp_in.flush()

        raw_transactions = extractor.extract_transactions(tmp_input_path)
    finally:
        if tmp_input_path and os.path.exists(tmp_input_path):
            safe_remove(tmp_input_path)

    if not raw_transactions:
        raise HTTPException(
            status_code=400, detail="Nenhuma transação válida foi encontrada no arquivo"
        )

    validated = validator.validate_transactions(raw_transactions)
    normalized = normalizer.normalize_transactions(validated, dataset_id)

    if not normalized:
        raise HTTPException(
            status_code=400, detail="Não foi possível normalizar os dados enviados"
        )

    normalized_records = convert_transactions_to_records(normalized)

    try:
        dataframes = build_report_dataframes(
            normalized_records, dataset_id, calculator=MetricsCalculator()
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Falha ao gerar abas consolidadas", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Erro ao consolidar métricas: {exc}"
        )

    try:
        export_path = write_report_excel(dataframes)
    except Exception as exc:
        logger.error("Falha ao gerar Excel consolidado", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Erro ao gerar arquivo final: {exc}"
        )

    filename = f"IPRO_{dataset_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    background_tasks.add_task(safe_remove, export_path)
    return FileResponse(
        export_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=background_tasks,
    )


@router.post("/extract/base-completa")
async def extract_base_completa(file: UploadFile = File(...)):
    """Retornar planilha Base Completa diretamente do upload."""
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .xlsx válido")

    extractor = DataExtractor()
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_in:
            content = await file.read()
            tmp_in.write(content)
            tmp_in.flush()
            extracted = extractor.extract_transactions(tmp_in.name)
    except Exception as exc:
        logger.error("Falha na extração da Base Completa", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao ler o arquivo: {exc}")

    if not extracted:
        logger.warning("Arquivo %s não possui linhas válidas", file.filename)
        raise HTTPException(
            status_code=400, detail="Nenhuma linha válida encontrada no arquivo"
        )

    df = pd.DataFrame(extracted)
    for col in df.columns:
        if "date" in col or "data" in col:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_out:
        df.to_excel(tmp_out.name, index=False)
        export_path = tmp_out.name

    filename = f"Base_Completa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return FileResponse(
        export_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/dataset/{dataset_id}/summary", response_model=DatasetSummary)
async def get_dataset_summary(dataset_id: str, db=Depends(get_db)):
    """Retornar visão geral consolidada do dataset."""
    try:
        dataset = db.datasets.find_one({"_id": dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset não encontrado")

        transactions = list(db.transactions.find({"dataset_id": dataset_id}))
        if not transactions:
            raise HTTPException(
                status_code=404, detail="Nenhuma transação encontrada para este dataset"
            )

        calculator = MetricsCalculator()
        kpis = calculator.calculate_general_kpis(transactions)

        df = pd.DataFrame(transactions)
        df["subtotal"] = pd.to_numeric(df["subtotal"], errors="coerce").fillna(0.0)
        df["qty"] = pd.to_numeric(df.get("qty"), errors="coerce").fillna(0)
        receita_por_sku = df.groupby("sku")["subtotal"].sum()
        hero_threshold = (
            receita_por_sku.quantile(0.8) if not receita_por_sku.empty else 0.0
        )
        hero_value = (
            float(receita_por_sku[receita_por_sku >= hero_threshold].sum())
            if hero_threshold
            else float(receita_por_sku.sum())
        )
        total_revenue = float(df["subtotal"].sum())
        hero_ratio = (hero_value / total_revenue) if total_revenue else 0.0

        regioes = sorted({t.get("uf") for t in transactions if t.get("uf")})

        top_products = (
            df.groupby(["sku", "product"])[["subtotal", "qty"]]
            .sum()
            .reset_index()
            .sort_values("subtotal", ascending=False)
            .head(5)
        )
        mix = {
            "total_revenue": total_revenue,
            "hero_share_value": hero_value,
            "hero_share_ratio": hero_ratio,
            "top_products": [
                {
                    "sku": row["sku"],
                    "product": row["product"],
                    "revenue": float(row["subtotal"]),
                    "qty": int(row["qty"]),
                }
                for _, row in top_products.iterrows()
            ],
        }

        return DatasetSummary(
            n_clientes=int(kpis.get("total_customers", 0)),
            n_skus=int(kpis.get("total_products", 0)),
            periodo={
                "inicio": kpis.get("period_start"),
                "fim": kpis.get("period_end"),
                "meses": int(kpis.get("period_days", 0) / 30)
                if kpis.get("period_days")
                else 0,
            },
            regioes=regioes,
            mix=mix,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar resumo: {str(e)}")
