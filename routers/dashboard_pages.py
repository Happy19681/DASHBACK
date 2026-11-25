import re
from datetime import date, datetime, timezone
from math import isfinite
from urllib.parse import urlparse

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from dashboard_database import page_records
from page_resource_schemas import PAGE_RESOURCES

router = APIRouter(prefix="/resources", tags=["Dashboard pages"])
SEARCHABLE_TYPES = {"text", "textarea", "email", "url", "select", "date"}


def resource_schema(resource: str) -> dict:
    if resource not in PAGE_RESOURCES:
        raise HTTPException(status_code=404, detail="Dashboard page resource not found")
    return PAGE_RESOURCES[resource]


def validate_values(resource: str, values: dict, partial: bool = False) -> dict:
    schema = resource_schema(resource)
    unknown = set(values) - set(schema)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown fields: {', '.join(sorted(unknown))}")
    if not partial:
        missing = [key for key, rules in schema.items() if rules["required"] and key not in values]
        if missing:
            raise HTTPException(status_code=422, detail=f"Required fields missing: {', '.join(missing)}")

    cleaned = {}
    for key, value in values.items():
        rules = schema[key]
        if value is None:
            raise HTTPException(status_code=422, detail=f"{key} cannot be null")
        kind = rules["type"]
        if kind in {"text", "textarea", "email", "url", "select", "date"}:
            if not isinstance(value, str):
                raise HTTPException(status_code=422, detail=f"{key} must be text")
            value = value.strip()
            if rules["required"] and not value:
                raise HTTPException(status_code=422, detail=f"{key} cannot be blank")
            if len(value) > 10000:
                raise HTTPException(status_code=422, detail=f"{key} is too long")
            if kind == "email" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
                raise HTTPException(status_code=422, detail=f"{key} must be a valid email")
            if kind == "url" and value and urlparse(value).scheme not in {"http", "https"}:
                raise HTTPException(status_code=422, detail=f"{key} must be an http or https URL")
            if kind == "date" and value:
                try:
                    date.fromisoformat(value)
                except ValueError as error:
                    raise HTTPException(status_code=422, detail=f"{key} must use YYYY-MM-DD format") from error
            if kind == "select" and value not in rules["options"]:
                raise HTTPException(status_code=422, detail=f"Invalid value for {key}")
        elif kind in {"number", "integer"}:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise HTTPException(status_code=422, detail=f"{key} must be a number")
            if not isfinite(value) or (kind == "integer" and not isinstance(value, int)):
                raise HTTPException(status_code=422, detail=f"Invalid number for {key}")
            if value < 0:
                raise HTTPException(status_code=422, detail=f"{key} cannot be negative")
        cleaned[key] = value
    return cleaned


def serialize(document: dict) -> dict:
    return {
        "id": str(document["_id"]),
        "resource": document["resource"],
        "createdAt": document["createdAt"].isoformat(),
        "updatedAt": document["updatedAt"].isoformat(),
        **{key: value for key, value in document.items() if key not in {"_id", "resource", "createdAt", "updatedAt"}},
    }


def parse_id(record_id: str) -> ObjectId:
    if not ObjectId.is_valid(record_id):
        raise HTTPException(status_code=400, detail="Invalid record ID")
    return ObjectId(record_id)


@router.get("/{resource}")
def list_page_records(
    resource: str,
    search: str | None = Query(default=None, max_length=200),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    schema = resource_schema(resource)
    query: dict = {"resource": resource}
    if search and search.strip():
        terms = search.strip().split()
        searchable_fields = [key for key, rule in schema.items() if rule["type"] in SEARCHABLE_TYPES]
        query["$and"] = [
            {"$or": [{key: {"$regex": re.escape(term), "$options": "i"}} for key in searchable_fields]}
            for term in terms
        ]
    total = page_records.count_documents(query)
    rows = page_records.find(query).sort("updatedAt", -1).skip(skip).limit(limit)
    return {"resource": resource, "total": total, "skip": skip, "limit": limit, "records": [serialize(row) for row in rows]}


@router.post("/{resource}", status_code=201)
def create_page_record(resource: str, payload: dict):
    values = validate_values(resource, payload)
    now = datetime.now(timezone.utc)
    document = {"resource": resource, "createdAt": now, "updatedAt": now, **values}
    result = page_records.insert_one(document)
    created = page_records.find_one({"_id": result.inserted_id})
    if created is None:
        raise HTTPException(status_code=500, detail="Record was saved but could not be loaded")
    return {"record": serialize(created)}


@router.get("/{resource}/{record_id}")
def get_page_record(resource: str, record_id: str):
    resource_schema(resource)
    row = page_records.find_one({"_id": parse_id(record_id), "resource": resource})
    if row is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"record": serialize(row)}


@router.patch("/{resource}/{record_id}")
def update_page_record(resource: str, record_id: str, payload: dict):
    resource_schema(resource)
    updates = validate_values(resource, payload, partial=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Provide at least one field to update")
    object_id = parse_id(record_id)
    updates["updatedAt"] = datetime.now(timezone.utc)
    result = page_records.update_one({"_id": object_id, "resource": resource}, {"$set": updates})
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"record": serialize(page_records.find_one({"_id": object_id, "resource": resource}))}


@router.delete("/{resource}/{record_id}")
def delete_page_record(resource: str, record_id: str):
    resource_schema(resource)
    result = page_records.delete_one({"_id": parse_id(record_id), "resource": resource})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"deleted": True, "id": record_id}
