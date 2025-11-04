from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from typing import List
import hashlib
import os
from uuid import uuid4
from datetime import datetime
from core.utils import utc_now

from services.database import get_db
from services.models import UploadResponse, DatasetSummary
from services.extractor import DataExtractor
from services.validator import DataValidator
from services.normalizer import DataNormalizer
from decimal import Decimal
from pymongo.errors import BulkWriteError, DuplicateKeyError

router = APIRouter()

def get_file_hash(content: bytes) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update(content or b"")
    return h.hexdigest()

@router.post("/upload-batch", response_model=UploadResponse)
async def upload_batch(request: Request, files: List[UploadFile] = File(...), db=Depends(get_db)):
    """Upload de múltiplos arquivos .xlsx"""
    try:
        idem = request.headers.get("Idempotency-Key") or hashlib.sha256(os.urandom(16)).hexdigest()
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
                raise HTTPException(status_code=400, detail=f"Arquivo {file.filename} não é um .xlsx válido")
            
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
            if "cadastro" in file.filename.lower() or "cliente" in file.filename.lower():
                # Processar como cadastro de clientes
                customers_data = extractor.extract_customers(file_path)
                if customers_data:
                    # Salvar clientes no banco.  Para permitir normalização posterior,
                    # armazenamos o nome normalizado como chave e preservamos o nome
                    # original em 'original_name'.  Isso evita divergências quando
                    # DataNormalizer procura clientes já cadastrados.
                    for customer in customers_data:
                        original_name = customer["name"]
                        normalized_name = normalizer._normalize_client_name(original_name)
                        customer_to_upsert = customer.copy()
                        customer_to_upsert["name"] = normalized_name
                        customer_to_upsert["original_name"] = original_name
                        db.customers.update_one(
                            {"name": normalized_name},
                            {"$set": customer_to_upsert},
                            upsert=True
                        )
            else:
                # Processar como relatório de pedidos
                transactions_data = extractor.extract_transactions(file_path)

                if transactions_data:
                    # Validar dados
                    validated_data = validator.validate_transactions(transactions_data)

                    # Normalizar dados
                    normalized_data = normalizer.normalize_transactions(validated_data, dataset_id)

                    # Salvar transações no banco
                    if normalized_data:
                        # Convert Decimal fields to floats to avoid serialization errors in MongoDB
                        tx_docs = []
                        for t in normalized_data:
                            doc = t.dict()
                            # Convert price and subtotal from Decimal to float if needed
                            if isinstance(doc.get('price'), Decimal):
                                doc['price'] = float(doc['price'])
                            if isinstance(doc.get('subtotal'), Decimal):
                                doc['subtotal'] = float(doc['subtotal'])
                            tx_docs.append(doc)
                        if tx_docs:
                            try:
                                # Use ordered=False to continue inserting even if duplicates hit unique indexes
                                result = db.transactions.insert_many(tx_docs, ordered=False)
                                # Count successfully inserted documents
                                total_rows += len(result.inserted_ids)
                            except BulkWriteError as bwe:
                                # In case of duplicates (duplicate key errors), only count successfully inserted ones
                                details = bwe.details or {}
                                total_rows += details.get('nInserted', 0)

        
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
            "stats": {"rows": 0, "errors": 0}
        }
        try:
            db.datasets.update_one({"_id": dataset_id}, {"$set": dataset_doc}, upsert=True)
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
        db.datasets.update_one({"_id": dataset_id}, {
            "$set": {
                "status": "READY",
                "stats.rows": total_rows,
                "stats.errors": 0,
                "finished_at": utc_now()
            }
        }, upsert=True)

        # Registrar a chave de idempotência para evitar reprocessamento
        try:
            db.requests.insert_one({"idempotency_key": idem, "dataset_id": dataset_id, "created_at": utc_now()})
        except Exception:
            # Se houver conflito de chave idempotência, ignore
            pass

        return UploadResponse(
            dataset_id=dataset_id,
            rows=total_rows,
            started_at=dataset_doc.get("created_at", utc_now()),
            status="READY"
        )
        
    except Exception as e:
        db.datasets.update_one({"_id": dataset_id}, {
            "$set": {"status": "FAILED", "error": str(e), "finished_at": utc_now()}
        })
        raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")

@router.get("/dataset/{dataset_id}/summary", response_model=DatasetSummary)
async def get_dataset_summary(dataset_id: str, db=Depends(get_db)):
    """Retornar resumo do dataset"""
    try:
        # Verificar se o dataset existe
        dataset = db.datasets.find_one({"_id": dataset_id})
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset não encontrado")
        
        # Calcular estatísticas
        transactions = list(db.transactions.find({"dataset_id": dataset_id}))
        
        if not transactions:
            raise HTTPException(status_code=404, detail="Nenhuma transação encontrada para este dataset")
        
        # Clientes únicos
        unique_clients = len(set(t["client"] for t in transactions))
        
        # SKUs únicos
        unique_skus = len(set(t["sku"] for t in transactions))
        
        # Período
        dates = [t["date"] for t in transactions]
        period_start = min(dates)
        period_end = max(dates)
        
        # Regiões
        regions = sorted({t.get("uf") for t in transactions if t.get("uf")})

        # Mix básico (top 5 por receita)
        total_revenue = float(sum(t["subtotal"] for t in transactions)) if transactions else 0.0
        top_products = {}
        for t in transactions:
            sku = t.get("sku") or t["product"]
            d = top_products.setdefault(sku, {"revenue": 0.0, "qty": 0, "product": t.get("product", sku)})
            d["revenue"] += float(t["subtotal"])
            d["qty"] += int(t["qty"])

        top5 = dict(sorted(top_products.items(), key=lambda x: x[1]["revenue"], reverse=True)[:5])

        return DatasetSummary(
            n_clientes=unique_clients,
            n_skus=unique_skus,
            periodo={
                "inicio": period_start.isoformat(),
                "fim": period_end.isoformat(),
                "meses": (period_end - period_start).days // 30
            },
            regioes=regions,
            mix={
                "total_revenue": total_revenue,
                "top_products": top5
            }
        )

        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar resumo: {str(e)}")

