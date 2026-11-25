from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


TransactionStatus = Literal["Success", "Pending", "Refunded"]


class TransactionCreate(BaseModel):
    customer: str = Field(min_length=1, max_length=120)
    product: str = Field(min_length=1, max_length=160)
    status: TransactionStatus = "Success"
    quantity: int = Field(ge=1, le=100000)
    unitPrice: float = Field(ge=0, le=100000000)
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("customer", "product")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class TransactionUpdate(BaseModel):
    customer: str | None = Field(default=None, min_length=1, max_length=120)
    product: str | None = Field(default=None, min_length=1, max_length=160)
    status: TransactionStatus | None = None
    quantity: int | None = Field(default=None, ge=1, le=100000)
    unitPrice: float | None = Field(default=None, ge=0, le=100000000)
    date: datetime | None = None

    @field_validator("customer", "product")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class BulkDeleteRequest(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=100)


