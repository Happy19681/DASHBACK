from datetime import datetime, timezone
import re
from typing import Literal

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from pymongo import DESCENDING, ASCENDING

from dashboard_database import collection
from transaction_schemas import BulkDeleteRequest, TransactionCreate, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["Transactions"])
money = lambda value: f"${value:,.2f}".rstrip("0").rstrip(".")


def utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def serialize(document: dict) -> dict:
    transaction_id = str(document["_id"])
    return {
        "id": transaction_id,
        "displayId": document.get("display_id", f"#{transaction_id[-5:]}"),
        "customer": document["customer"],
        "product": document["product"],
        "status": document["status"],
        "quantity": document["quantity"],
        "unitPrice": money(document["unit_price"]),
        "totalRevenue": money(document["quantity"] * document["unit_price"]),
        "date": document.get("date", datetime.now(timezone.utc)).isoformat(),
    }


def parse_id(transaction_id: str) -> ObjectId:
    if not ObjectId.is_valid(transaction_id):
        raise HTTPException(status_code=400, detail="Invalid transaction ID")
    return ObjectId(transaction_id)


@router.get("")
def list_transactions(
    search: str | None = Query(default=None, max_length=200),
    status: Literal["Success", "Pending", "Refunded"] | None = None,
    sort_by: Literal["date", "customer", "product", "status", "quantity", "unitPrice", "totalRevenue"] = "date",
    sort_order: Literal["asc", "desc"] = "desc",
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    query: dict = {}
    if status:
        query["status"] = status
    if search and search.strip():
        terms = search.strip().split()
        query["$and"] = [
            {"$or": [{field: {"$regex": re.escape(term), "$options": "i"}} for field in ("customer", "product", "status", "display_id")]}
            for term in terms
        ]

    sort_fields = {
        "date": "date", "customer": "customer", "product": "product",
        "status": "status", "quantity": "quantity", "unitPrice": "unit_price",
        "totalRevenue": "total_revenue",
    }
    direction = ASCENDING if sort_order == "asc" else DESCENDING
    total = collection.count_documents(query)
    rows = collection.find(query).sort(sort_fields[sort_by], direction).skip(skip).limit(limit)
    return {"total": total, "skip": skip, "limit": limit, "transactions": [serialize(row) for row in rows]}


@router.get("/{transaction_id}")
def get_transaction(transaction_id: str):
    row = collection.find_one({"_id": parse_id(transaction_id)})
    if row is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"transaction": serialize(row)}


@router.post("", status_code=201)
def create_transaction(payload: TransactionCreate):
    data = payload.model_dump()
    data["date"] = utc_datetime(data["date"])
    data["unit_price"] = data.pop("unitPrice")
    data["total_revenue"] = data["quantity"] * data["unit_price"]
    result = collection.insert_one(data)
    display_id = f"#{str(result.inserted_id)[-5:]}"
    collection.update_one({"_id": result.inserted_id}, {"$set": {"display_id": display_id}})
    row = collection.find_one({"_id": result.inserted_id})
    return {"transaction": serialize(row)}


@router.patch("/{transaction_id}")
def update_transaction(transaction_id: str, payload: TransactionUpdate):
    object_id = parse_id(transaction_id)
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Provide at least one field to update")
    if "unitPrice" in updates:
        updates["unit_price"] = updates.pop("unitPrice")
    if updates.get("date") is not None:
        updates["date"] = utc_datetime(updates["date"])
    existing = collection.find_one({"_id": object_id})
    if existing is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    merged = {**existing, **updates}
    updates["total_revenue"] = merged["quantity"] * merged["unit_price"]
    collection.update_one({"_id": object_id}, {"$set": updates})
    return {"transaction": serialize(collection.find_one({"_id": object_id}))}


@router.delete("/bulk")
def delete_transactions(payload: BulkDeleteRequest):
    if any(not ObjectId.is_valid(transaction_id) for transaction_id in payload.ids):
        raise HTTPException(status_code=400, detail="One or more transaction IDs are invalid")
    result = collection.delete_many({"_id": {"$in": [ObjectId(value) for value in payload.ids]}})
    return {"deleted": result.deleted_count}


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: str):
    result = collection.delete_one({"_id": parse_id(transaction_id)})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"deleted": True, "id": transaction_id}
