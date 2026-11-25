from calendar import monthrange
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from dashboard_database import collection

router = APIRouter(prefix="/dashboard", tags=["Dashboard overview"])


def period_bounds(period: str, selected: date) -> tuple[datetime, datetime, datetime, datetime]:
    if period == "Daily":
        start, end = selected, selected + timedelta(days=1)
        previous_start, previous_end = start - timedelta(days=1), start
    elif period == "Weekly":
        start = selected - timedelta(days=selected.weekday())
        end = start + timedelta(days=7)
        previous_start, previous_end = start - timedelta(days=7), start
    elif period == "Monthly":
        start = selected.replace(day=1)
        end = start.replace(day=monthrange(start.year, start.month)[1]) + timedelta(days=1)
        previous_end = start
        previous_start = (start - timedelta(days=1)).replace(day=1)
    else:
        start = selected.replace(month=1, day=1)
        end = start.replace(year=start.year + 1)
        previous_start, previous_end = start.replace(year=start.year - 1), start

    return tuple(
        datetime.combine(day, time.min, tzinfo=timezone.utc)
        for day in (start, end, previous_start, previous_end)
    )


def summarize(start: datetime, end: datetime) -> dict:
    result = next(collection.aggregate([
        {"$match": {"date": {"$gte": start, "$lt": end}}},
        {"$group": {
            "_id": None,
            "transactions": {"$sum": 1},
            "orders": {"$sum": {"$cond": [{"$eq": ["$status", "Success"]}, 1, 0]}},
            "revenue": {"$sum": {"$cond": [
                {"$eq": ["$status", "Success"]},
                {"$multiply": ["$quantity", "$unit_price"]},
                0,
            ]}},
            "customers": {"$addToSet": {"$toLower": {"$trim": {"input": "$customer"}}}},
        }},
    ]), None)
    if not result:
        return {"revenue": 0, "orders": 0, "customers": 0, "conversion": 0, "transactions": 0}
    transaction_count = result["transactions"]
    return {
        "revenue": round(result["revenue"], 2),
        "orders": result["orders"],
        "customers": len(result["customers"]),
        "conversion": round(result["orders"] / transaction_count * 100, 1) if transaction_count else 0,
        "transactions": transaction_count,
    }


def revenue_by_month(year: int) -> list[dict]:
    start = datetime(year - 1, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    monthly = {
        (row["_id"]["year"], row["_id"]["month"]): row
        for row in collection.aggregate([
            {"$match": {"date": {"$gte": start, "$lt": end}}},
            {"$group": {
                "_id": {"year": {"$year": "$date"}, "month": {"$month": "$date"}},
                "transactions": {"$sum": 1},
                "orders": {"$sum": {"$cond": [{"$eq": ["$status", "Success"]}, 1, 0]}},
                "revenue": {"$sum": {"$cond": [
                    {"$eq": ["$status", "Success"]},
                    {"$multiply": ["$quantity", "$unit_price"]},
                    0,
                ]}},
                "customers": {"$addToSet": {"$toLower": {"$trim": {"input": "$customer"}}}},
            }},
        ])
    }

    def values(target_year: int, month: int) -> dict:
        row = monthly.get((target_year, month), {})
        transactions = row.get("transactions", 0)
        orders = row.get("orders", 0)
        return {
            "revenue": round(row.get("revenue", 0), 2),
            "orders": orders,
            "customers": len(row.get("customers", [])),
            "conversion": round(orders / transactions * 100, 1) if transactions else 0,
        }

    return [{
        "month": month,
        **values(year, month),
        "previousYearRevenue": values(year - 1, month)["revenue"],
        "previousYearOrders": values(year - 1, month)["orders"],
        "previousYearCustomers": values(year - 1, month)["customers"],
        "previousYearConversion": values(year - 1, month)["conversion"],
    } for month in range(1, 13)]


@router.get("/metrics")
def get_dashboard_metrics(
    period: str = Query(default="Daily", pattern="^(Daily|Weekly|Monthly|Yearly)$"),
    selected_date: date = Query(alias="date"),
):
    if selected_date > datetime.now(timezone.utc).date():
        raise HTTPException(status_code=400, detail="Date cannot be in the future")
    start, end, previous_start, previous_end = period_bounds(period, selected_date)
    current, previous = summarize(start, end), summarize(previous_start, previous_end)

    def percent_change(key: str) -> float:
        old_value = previous[key]
        return round((current[key] - old_value) / old_value * 100, 2) if old_value else 0

    def metric(key: str) -> dict:
        return {
            "value": current[key],
            "previousValue": previous[key],
            "changePercent": percent_change(key),
        }

    return {
        "period": period,
        "date": selected_date.isoformat(),
        "range": {"start": start.date().isoformat(), "endExclusive": end.date().isoformat()},
        "metrics": {
            "revenue": metric("revenue"),
            "orders": metric("orders"),
            "customers": metric("customers"),
            "conversion": metric("conversion"),
        },
        "salesTrend": revenue_by_month(selected_date.year),
        "transactionCount": current["transactions"],
    }


@router.get("/revenue-breakdown")
def get_revenue_breakdown(
    start: date,
    end: date,
):
    if start > end:
        raise HTTPException(status_code=400, detail="Start date must be on or before end date")
    if end > datetime.now(timezone.utc).date():
        raise HTTPException(status_code=400, detail="End date cannot be in the future")
    range_start = datetime.combine(start, time.min, tzinfo=timezone.utc)
    range_end = datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc)
    result = list(collection.aggregate([
        {"$match": {"date": {"$gte": range_start, "$lt": range_end}, "status": "Success"}},
        {"$group": {
            "_id": "$product",
            "revenue": {"$sum": {"$multiply": ["$quantity", "$unit_price"]}},
            "quantity": {"$sum": "$quantity"},
        }},
        {"$sort": {"revenue": -1}},
    ]))
    products = [
        {"product": row["_id"], "revenue": round(row["revenue"], 2), "quantity": row["quantity"]}
        for row in result
    ]
    if len(products) > 13:
        remaining = products[12:]
        products = products[:12] + [{
            "product": "Other products",
            "revenue": round(sum(item["revenue"] for item in remaining), 2),
            "quantity": sum(item["quantity"] for item in remaining),
        }]
    return {
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "totalRevenue": round(sum(product["revenue"] for product in products), 2),
        "products": products,
    }
