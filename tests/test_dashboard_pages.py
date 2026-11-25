import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from bson import ObjectId
from fastapi import HTTPException

from page_resource_schemas import PAGE_RESOURCES
from routers import dashboard_pages


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, key, direction):
        self.rows.sort(key=lambda row: row.get(key), reverse=direction < 0)
        return self

    def skip(self, count):
        self.rows = self.rows[count:]
        return self

    def limit(self, count):
        self.rows = self.rows[:count]
        return self

    def __iter__(self):
        return iter(self.rows)


class MemoryCollection:
    def __init__(self):
        self.rows = {}

    @staticmethod
    def matches(row, query):
        return all(row.get(key) == value for key, value in query.items())

    def count_documents(self, query):
        return sum(self.matches(row, query) for row in self.rows.values())

    def find(self, query):
        return Cursor([row.copy() for row in self.rows.values() if self.matches(row, query)])

    def find_one(self, query):
        return next((row.copy() for row in self.rows.values() if self.matches(row, query)), None)

    def insert_one(self, document):
        row_id = ObjectId()
        self.rows[row_id] = {"_id": row_id, **document}
        return SimpleNamespace(inserted_id=row_id)

    def update_one(self, query, update):
        row = next((row for row in self.rows.values() if self.matches(row, query)), None)
        if row is None:
            return SimpleNamespace(matched_count=0)
        row.update(update["$set"])
        return SimpleNamespace(matched_count=1)

    def delete_one(self, query):
        row_id = next((row_id for row_id, row in self.rows.items() if self.matches(row, query)), None)
        if row_id is None:
            return SimpleNamespace(deleted_count=0)
        del self.rows[row_id]
        return SimpleNamespace(deleted_count=1)


def valid_values(schema):
    values = {}
    for key, rules in schema.items():
        kind = rules["type"]
        if kind == "select":
            values[key] = rules["options"][0]
        elif kind == "email":
            values[key] = "person@example.com"
        elif kind == "url":
            values[key] = "https://example.com"
        elif kind == "date":
            values[key] = "2026-11-25"
        elif kind in {"number", "integer"}:
            values[key] = 10
        else:
            values[key] = f"Test {key}"
    return values


class DashboardPageCrudTests(unittest.TestCase):
    def test_every_page_resource_supports_create_read_update_list_and_delete(self):
        for resource, schema in PAGE_RESOURCES.items():
            with self.subTest(resource=resource), patch.object(dashboard_pages, "page_records", MemoryCollection()):
                values = valid_values(schema)
                created = dashboard_pages.create_page_record(resource, values)["record"]
                record_id = created["id"]
                self.assertEqual(dashboard_pages.get_page_record(resource, record_id)["record"]["id"], record_id)
                self.assertEqual(dashboard_pages.list_page_records(resource, None, 0, 100)["total"], 1)

                first_key = next(iter(schema))
                replacement = valid_values({first_key: schema[first_key]})[first_key]
                if schema[first_key]["type"] == "text":
                    replacement = "Updated record"
                dashboard_pages.update_page_record(resource, record_id, {first_key: replacement})
                self.assertEqual(dashboard_pages.get_page_record(resource, record_id)["record"][first_key], replacement)

                self.assertTrue(dashboard_pages.delete_page_record(resource, record_id)["deleted"])
                self.assertEqual(dashboard_pages.list_page_records(resource, None, 0, 100)["total"], 0)

    def test_invalid_fields_and_unknown_resources_are_rejected(self):
        with self.assertRaises(HTTPException) as unknown:
            dashboard_pages.create_page_record("unknown", {})
        self.assertEqual(unknown.exception.status_code, 404)

        with self.assertRaises(HTTPException) as extra_field:
            dashboard_pages.validate_values("products", {"unexpected": "value"})
        self.assertEqual(extra_field.exception.status_code, 422)

    def test_invalid_select_and_fractional_integer_are_rejected(self):
        with self.assertRaises(HTTPException):
            dashboard_pages.validate_values("products", {
                "name": "Product", "category": "Home", "price": 10,
                "stock": 2, "status": "Unknown",
            })
        with self.assertRaises(HTTPException):
            dashboard_pages.validate_values("orders", {
                "orderNumber": "A-1", "customer": "Test", "product": "Chair",
                "quantity": 1.5, "amount": 10, "status": "Pending", "date": "2026-11-25",
            })


if __name__ == "__main__":
    unittest.main()
