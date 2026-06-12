from __future__ import annotations

from datetime import datetime

from extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    role = db.Column(db.Enum("admin", "employee", "user", name="user_role"), nullable=False, default="user")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    applications = db.relationship(
        "Application",
        back_populates="applicant",
        foreign_keys="Application.applicant_id",
    )
    reviewed_applications = db.relationship(
        "Application",
        foreign_keys="Application.reviewer_id",
    )
    news = db.relationship("News", back_populates="author")


class Property(db.Model):
    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    type = db.Column(
        db.Enum("land", "building", "premises", "other", name="property_type"),
        nullable=False,
    )
    address = db.Column(db.String(500), nullable=False)
    cadastral_number = db.Column(db.String(100), nullable=True)
    area = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)
    communications = db.Column(db.Text, nullable=True)
    condition = db.Column(
        db.Enum("excellent", "good", "satisfactory", "poor", name="property_condition"),
        nullable=True,
    )
    rent_price = db.Column(db.Integer, nullable=True)
    sale_price = db.Column(db.Integer, nullable=True)
    status = db.Column(
        db.Enum(
            "available",
            "reserved",
            "rented",
            "sold",
            "private_ownership",
            name="property_status",
        ),
        nullable=False,
        default="available",
        index=True,
    )
    operation_type = db.Column(
        db.Enum("rent", "sale", "both", name="operation_type"),
        nullable=False,
        default="rent",
        index=True,
    )
    responsible_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    owner_name = db.Column(db.String(255), nullable=True)
    ownership_date = db.Column(db.Date, nullable=True)
    ownership_basis = db.Column(db.Text, nullable=True)

    # Координаты объекта для Яндекс.Карт.
    # В Яндекс.Карты передаётся порядок lng,lat, но в базе храним отдельно lat и lng.
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    responsible_user = db.relationship("User")
    images = db.relationship(
        "PropertyImage",
        back_populates="property",
        cascade="all, delete-orphan",
        order_by="PropertyImage.sort_order",
    )
    documents = db.relationship(
        "PropertyDocument",
        back_populates="property",
        cascade="all, delete-orphan",
        order_by="PropertyDocument.uploaded_at.desc()",
    )
    applications = db.relationship("Application", back_populates="property")


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    application_type = db.Column(db.Enum("rent", "purchase", name="application_type"), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False)
    desired_term = db.Column(db.Integer, nullable=True)
    purpose = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.Enum("full", "installment", name="payment_method"), nullable=True)
    planned_date = db.Column(db.Date, nullable=True)
    status = db.Column(
        db.Enum("pending", "approved", "rejected", "in_review", name="application_status"),
        nullable=False,
        default="pending",
        index=True,
    )
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    review_date = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    applicant = db.relationship(
        "User",
        foreign_keys=[applicant_id],
        back_populates="applications",
    )
    reviewer = db.relationship("User", foreign_keys=[reviewer_id], overlaps="reviewed_applications")
    property = db.relationship("Property", back_populates="applications")


class PropertyImage(db.Model):
    __tablename__ = "property_images"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False, index=True)
    image_url = db.Column(db.String(1000), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=1)

    property = db.relationship("Property", back_populates="images")


class PropertyDocument(db.Model):
    __tablename__ = "property_documents"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False, index=True)
    doc_name = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(1000), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    property = db.relationship("Property", back_populates="documents")


class ApplicationDocument(db.Model):
    __tablename__ = "application_documents"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True)
    doc_name = db.Column(db.String(255), nullable=False)
    file_url = db.Column(db.String(1000), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    application = db.relationship("Application")


class Contract(db.Model):
    __tablename__ = "contracts"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    contract_type = db.Column(db.Enum("rent", "sale", name="contract_type"), nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    monthly_rent = db.Column(db.Integer, nullable=True)
    sale_price = db.Column(db.Integer, nullable=True)
    deposit_amount = db.Column(db.Integer, nullable=True)
    status = db.Column(
        db.Enum("draft", "active", "completed", "terminated", name="contract_status"),
        nullable=False,
        default="draft",
        index=True,
    )
    signed_at = db.Column(db.DateTime, nullable=True)

    application = db.relationship("Application")
    property = db.relationship("Property")
    tenant = db.relationship("User")
    payments = db.relationship(
        "Payment",
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="Payment.due_date.desc()",
    )


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey("contracts.id"), nullable=False, index=True)
    payment_type = db.Column(db.Enum("rent", "deposit", "purchase", "other", name="payment_type"), nullable=False)
    period_month = db.Column(db.Date, nullable=True)
    amount = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    paid_date = db.Column(db.Date, nullable=True)
    status = db.Column(
        db.Enum("pending", "paid", "overdue", "cancelled", name="payment_status"),
        nullable=False,
        default="pending",
        index=True,
    )

    contract = db.relationship("Contract", back_populates="payments")


class News(db.Model):
    __tablename__ = "news"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    published_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow, index=True)

    author = db.relationship("User", back_populates="news")


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    entity_type = db.Column(db.String(100), nullable=True)
    entity_id = db.Column(db.Integer, nullable=True)
    details_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    user = db.relationship("User")
