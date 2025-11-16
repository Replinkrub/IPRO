from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4
from decimal import Decimal

class Dataset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), alias="_id")
    filename: str
    created_at: datetime = Field(default_factory=datetime.now)
    rows: int
    hash: str
    status: str = "processing"  # processing, completed, failed
    
    class Config:
        populate_by_name = True

class Transaction(BaseModel):
    dataset_id: str
    product: str
    date: datetime
    order_id: str
    client: str
    seller: Optional[str] = None
    price: Decimal
    qty: int
    subtotal: Decimal
    sku: Optional[str] = None
    uf: Optional[str] = None
    # Campos adicionais derivados de dados de cadastro
    segment: Optional[str] = None
    city: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class Customer(BaseModel):
    client_id: Optional[str] = None
    name: str
    segment: Optional[str] = None
    city: Optional[str] = None
    uf: Optional[str] = None
    created_at: Optional[datetime] = None
    source: str = "upload"

class Product(BaseModel):
    sku: str
    name: str
    category: Optional[str] = None
    cost: Optional[float] = None

class CustomerAnalytics(BaseModel):
    dataset_id: str
    client: str
    recency: int        # dias desde a última compra
    frequency: int      # nº de pedidos
    monetary: float     # valor total
    avg_ticket: float
    gm_cliente: float
    tier: str
    segment: Optional[str] = None
    city: Optional[str] = None
    uf: Optional[str] = None
    last_order: Optional[datetime] = None
    rfm_score: float = 0.0
    segment_weight: float = 1.0

class ProductAnalytics(BaseModel):
    dataset_id: str
    sku: str
    product: str
    orders: int
    qty: int
    revenue: Decimal
    avg_ticket: Optional[Decimal] = None
    turnover_median: Optional[float] = None
    hero_mix: Optional[bool] = None
    growth_zscore: Optional[float] = None
    growth_yoy: Optional[float] = None

class Alert(BaseModel):
    dataset_id: str
    client: str
    sku: Optional[str] = None
    type: str  # ruptura, queda_brusca, outlier, etc.
    insight: Optional[str] = None
    action: Optional[str] = None
    diagnosis: Optional[str] = None
    recommended_action: Optional[str] = None
    reliability: str  # 🔵, 🟡, 🔴
    suggested_deadline: Optional[str] = None

    def dict(self, *args, **kwargs):  # type: ignore[override]
        data = super().dict(*args, **kwargs)
        data.setdefault("diagnosis", data.get("insight"))
        data.setdefault("recommended_action", data.get("action"))
        return data

class Cohort(BaseModel):
    dataset_id: str
    cohort_date: datetime
    retention_data: Dict[str, float]  # retention_month_N

class KPIResponse(BaseModel):
    total_clients: int
    avg_recency_days: int
    avg_frequency: float
    avg_value: Decimal

class DatasetSummary(BaseModel):
    n_clientes: int
    n_skus: int
    periodo: Dict[str, Any]  # inicio, fim, meses
    regioes: List[str]
    mix: Dict[str, Any]

class UploadResponse(BaseModel):
    dataset_id: str
    rows: int
    started_at: datetime
    status: str = "processing"

