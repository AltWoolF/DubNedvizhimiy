from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app import app
from extensions import db
from models import (
    Application,
    AuditLog,
    Contract,
    News,
    Payment,
    Property,
    PropertyDocument,
    PropertyImage,
    User,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "instance" / "data.json"


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def parse_date(value: Any) -> date | None:
    if not value:
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def load_json_data() -> dict[str, Any]:
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def seed_database(drop: bool = False) -> None:
    data = load_json_data()

    with app.app_context():
        if drop:
            db.drop_all()

        db.create_all()

        if User.query.first() and not drop:
            print("База уже содержит пользователей. Если нужно перезаписать данные, запустите: python seed_db.py --drop")
            return

        for item in data.get("users", []):
            db.session.add(
                User(
                    id=item["id"],
                    login=item["login"],
                    password_hash=item["password_hash"],
                    full_name=item["full_name"],
                    email=item.get("email"),
                    phone=item.get("phone"),
                    role=item["role"],
                    is_active=item["is_active"],
                    created_at=parse_datetime(item.get("created_at")) or datetime.utcnow(),
                )
            )

        db.session.commit()

        for item in data.get("properties", []):
            coords = item.get("coordinates") or {}

            db.session.add(
                Property(
                    id=item["id"],
                    title=item["title"],
                    type=item["type"],
                    address=item["address"],
                    cadastral_number=item.get("cadastral_number"),
                    area=item.get("area"),
                    description=item.get("description"),
                    communications=item.get("communications"),
                    condition=item.get("condition"),
                    rent_price=item.get("rent_price"),
                    sale_price=item.get("sale_price"),
                    status=item["status"],
                    operation_type=item["operation_type"],
                    responsible_user_id=item.get("responsible_user_id"),
                    owner_name=item.get("owner_name"),
                    ownership_date=parse_date(item.get("ownership_date")),
                    ownership_basis=item.get("ownership_basis"),
                    lat=coords.get("lat"),
                    lng=coords.get("lng"),
                    created_at=parse_datetime(item.get("created_at")) or datetime.utcnow(),
                    updated_at=parse_datetime(item.get("updated_at")) or datetime.utcnow(),
                )
            )

        db.session.commit()

        for item in data.get("propertyImages", []):
            db.session.add(
                PropertyImage(
                    id=item["id"],
                    property_id=item["property_id"],
                    image_url=item["image_url"],
                    sort_order=item.get("sort_order", 1),
                )
            )

        for item in data.get("propertyDocuments", []):
            db.session.add(
                PropertyDocument(
                    id=item["id"],
                    property_id=item["property_id"],
                    doc_name=item["doc_name"],
                    file_url=item["file_url"],
                    uploaded_at=parse_datetime(item.get("uploaded_at")) or datetime.utcnow(),
                )
            )

        db.session.commit()

        for item in data.get("applications", []):
            db.session.add(
                Application(
                    id=item["id"],
                    number=item["number"],
                    application_type=item["application_type"],
                    applicant_id=item["applicant_id"],
                    property_id=item["property_id"],
                    desired_term=item.get("desired_term"),
                    purpose=item.get("purpose"),
                    payment_method=item.get("payment_method"),
                    planned_date=parse_date(item.get("planned_date")),
                    status=item["status"],
                    reviewer_id=item.get("reviewer_id"),
                    review_date=parse_datetime(item.get("review_date")),
                    rejection_reason=item.get("rejection_reason"),
                    created_at=parse_datetime(item.get("created_at")) or datetime.utcnow(),
                )
            )

        db.session.commit()

        for item in data.get("contracts", []):
            db.session.add(
                Contract(
                    id=item["id"],
                    application_id=item["application_id"],
                    property_id=item["property_id"],
                    tenant_id=item["tenant_id"],
                    contract_type=item["contract_type"],
                    start_date=parse_date(item.get("start_date")),
                    end_date=parse_date(item.get("end_date")),
                    monthly_rent=item.get("monthly_rent"),
                    sale_price=item.get("sale_price"),
                    deposit_amount=item.get("deposit_amount"),
                    status=item["status"],
                    signed_at=parse_datetime(item.get("signed_at")),
                )
            )

        db.session.commit()

        for item in data.get("payments", []):
            db.session.add(
                Payment(
                    id=item["id"],
                    contract_id=item["contract_id"],
                    payment_type=item["payment_type"],
                    period_month=parse_date(item.get("period_month")),
                    amount=item["amount"],
                    due_date=parse_date(item.get("due_date")),
                    paid_date=parse_date(item.get("paid_date")),
                    status=item["status"],
                )
            )

        db.session.commit()

        for item in data.get("news", []):
            db.session.add(
                News(
                    id=item["id"],
                    title=item["title"],
                    content=item["content"],
                    author_id=item["author_id"],
                    published_at=parse_datetime(item.get("published_at")) or datetime.utcnow(),
                )
            )

        db.session.commit()

        for item in data.get("auditLog", []):
            db.session.add(
                AuditLog(
                    id=item["id"],
                    user_id=item.get("user_id"),
                    action=item["action"],
                    entity_type=item.get("entity_type"),
                    entity_id=item.get("entity_id"),
                    details_json=item.get("details_json"),
                    created_at=parse_datetime(item.get("created_at")) or datetime.utcnow(),
                )
            )

        db.session.commit()
        print("Данные успешно перенесены из instance/data.json в базу данных.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Заполнение базы данных начальными данными")
    parser.add_argument("--drop", action="store_true", help="Удалить все таблицы и создать заново")
    args = parser.parse_args()

    seed_database(drop=args.drop)


if __name__ == "__main__":
    main()
