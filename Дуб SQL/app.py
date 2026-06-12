from __future__ import annotations

import json
from datetime import date, datetime
from functools import wraps
from typing import Any
from urllib.parse import urlencode

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy import or_

from config import Config
from extensions import db, migrate
from models import (
    Application,
    ApplicationDocument,
    AuditLog,
    Contract,
    News,
    Payment,
    Property,
    PropertyDocument,
    PropertyImage,
    User,
)

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate.init_app(app, db)

STATUS_LABELS = {
    "available": "Свободно",
    "reserved": "Забронировано",
    "rented": "Арендовано",
    "sold": "Продано",
    "private_ownership": "В собственности третьих лиц",
}

STATUS_COLORS = {
    "available": "#4CAF50",
    "reserved": "#FFC107",
    "rented": "#9E9E9E",
    "sold": "#616161",
    "private_ownership": "#455A64",
}

PROPERTY_TYPES = {
    "land": "Земельный участок",
    "building": "Здание",
    "premises": "Помещение",
    "other": "Прочее",
}

CONDITION_LABELS = {
    "excellent": "Отличное",
    "good": "Хорошее",
    "satisfactory": "Удовлетворительное",
    "poor": "Требует ремонта",
}

APPLICATION_STATUS = {
    "pending": "Ожидает рассмотрения",
    "in_review": "На рассмотрении",
    "approved": "Одобрена",
    "rejected": "Отклонена",
}

ROLE_LABELS = {
    "admin": "Администратор",
    "employee": "Сотрудник",
    "user": "Пользователь",
}


def parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_float(value: Any) -> float | None:
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
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


def now_dt() -> datetime:
    return datetime.now()


def current_user() -> User | None:
    user_id = session.get("user_id")

    if not user_id:
        return None

    return User.query.filter_by(id=user_id, is_active=True).first()


def add_audit_log(
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: Any = None,
) -> None:
    log = AuditLog(
        user_id=session.get("user_id"),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=json.dumps(details, ensure_ascii=False) if details is not None else None,
        created_at=now_dt(),
    )

    db.session.add(log)
    db.session.commit()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Для доступа к странице необходимо войти в систему", "warning")
            return redirect(url_for("login", next=request.path))

        return view(*args, **kwargs)

    return wrapped


def staff_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()

        if not user or user.role == "user":
            flash("Доступ разрешён только сотрудникам администрации", "error")
            return redirect(url_for("index"))

        return view(*args, **kwargs)

    return wrapped


def format_price(price: Any) -> str:
    if not price:
        return "—"

    return f"{int(price):,}".replace(",", " ") + " ₽"


def format_area(area: Any) -> str:
    if not area:
        return "—"

    if float(area).is_integer():
        area = int(area)

    return f"{area:,}".replace(",", " ") + " м²"


def format_date(value: Any, with_time: bool = False) -> str:
    if not value:
        return "—"

    try:
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, date):
            dt = datetime.combine(value, datetime.min.time())
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))

        months = [
            "января",
            "февраля",
            "марта",
            "апреля",
            "мая",
            "июня",
            "июля",
            "августа",
            "сентября",
            "октября",
            "ноября",
            "декабря",
        ]

        result = f"{dt.day} {months[dt.month - 1]} {dt.year}"

        if with_time:
            result += f" в {dt.hour:02d}:{dt.minute:02d}"

        return result
    except Exception:
        return str(value)


def truncate(text: str | None, length: int = 120) -> str:
    text = text or ""
    return text if len(text) <= length else text[:length].rstrip() + "..."


def get_property(_data: Any, property_id: int | None) -> Property | None:
    if not property_id:
        return None

    return db.session.get(Property, int(property_id))


def get_user(_data: Any, user_id: int | None) -> User | None:
    if not user_id:
        return None

    return db.session.get(User, int(user_id))


def property_images(data_or_property: Any = None, property_id: int | None = None) -> list[PropertyImage]:
    """Возвращает изображения объекта.

    Функция оставлена совместимой со старыми шаблонами:
    - property_images(data, property.id)
    - property_images(property)
    """

    if isinstance(data_or_property, Property):
        return sorted(data_or_property.images, key=lambda image: image.sort_order)

    if property_id is None:
        return []

    return (
        PropertyImage.query
        .filter_by(property_id=property_id)
        .order_by(PropertyImage.sort_order.asc())
        .all()
    )


def yandex_map_url(properties: list[Property] | Property | None, zoom: int = 13) -> str:
    """Создаёт URL виджета Яндекс.Карт с метками объектов недвижимости."""

    if properties is None:
        properties_list: list[Property] = []
    elif isinstance(properties, list):
        properties_list = properties
    else:
        properties_list = [properties]

    points: list[tuple[float, float]] = []

    for prop in properties_list:
        lat = getattr(prop, "lat", None)
        lng = getattr(prop, "lng", None)

        if lat is not None and lng is not None:
            points.append((float(lat), float(lng)))

    if points:
        center_lat = sum(lat for lat, _ in points) / len(points)
        center_lng = sum(lng for _, lng in points) / len(points)
        pt = "~".join(f"{lng},{lat},pm2rdm" for lat, lng in points)
    else:
        center_lat = 53.1245
        center_lng = 50.5712
        pt = f"{center_lng},{center_lat},pm2rdm"

    params = {
        "ll": f"{center_lng},{center_lat}",
        "z": str(zoom),
        "l": "map",
        "pt": pt,
    }

    return "https://yandex.ru/map-widget/v1/?" + urlencode(params)


def favorite_ids() -> list[int]:
    return session.setdefault("favorites", [])


@app.context_processor
def inject_globals():
    return dict(
        current_user=current_user(),
        favorites=favorite_ids(),
        STATUS_LABELS=STATUS_LABELS,
        STATUS_COLORS=STATUS_COLORS,
        PROPERTY_TYPES=PROPERTY_TYPES,
        CONDITION_LABELS=CONDITION_LABELS,
        APPLICATION_STATUS=APPLICATION_STATUS,
        ROLE_LABELS=ROLE_LABELS,
        format_price=format_price,
        format_area=format_area,
        format_date=format_date,
        truncate=truncate,
        get_user=get_user,
        get_property=get_property,
        property_images=property_images,
        yandex_map_url=yandex_map_url,
        current_year=datetime.now().year,
    )


@app.route("/")
def index():
    featured = (
        Property.query
        .filter_by(status="available")
        .order_by(Property.created_at.desc())
        .limit(3)
        .all()
    )

    stats = {
        "properties": Property.query.count(),
        "available": Property.query.filter_by(status="available").count(),
        "applications": Application.query.count(),
        "contracts": Contract.query.count(),
    }

    return render_template(
        "home.html",
        data=None,
        featured=featured,
        stats=stats,
        title="Главная",
    )


@app.route("/catalog")
def catalog():
    query = Property.query

    q = request.args.get("q", "").strip()
    p_type = request.args.get("type", "")
    status = request.args.get("status", "")
    operation = request.args.get("operation", "")
    sort = request.args.get("sort", "new")

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Property.title.ilike(like),
                Property.address.ilike(like),
                Property.description.ilike(like),
            )
        )

    if p_type:
        query = query.filter(Property.type == p_type)

    if status:
        query = query.filter(Property.status == status)

    if operation:
        query = query.filter(
            or_(
                Property.operation_type == operation,
                Property.operation_type == "both",
            )
        )

    properties = query.all()

    if sort == "price_asc":
        properties.sort(key=lambda p: p.sale_price or p.rent_price or 10**18)
    elif sort == "price_desc":
        properties.sort(key=lambda p: p.sale_price or p.rent_price or 0, reverse=True)
    elif sort == "area_desc":
        properties.sort(key=lambda p: p.area or 0, reverse=True)
    else:
        properties.sort(key=lambda p: p.created_at or datetime.min, reverse=True)

    return render_template(
        "catalog.html",
        data=None,
        properties=properties,
        filters=request.args,
        catalog_map_url=yandex_map_url(properties, zoom=13),
        title="Каталог объектов",
    )


@app.route("/property/<int:property_id>")
def property_detail(property_id: int):
    prop = Property.query.get_or_404(property_id)
    images = sorted(prop.images, key=lambda image: image.sort_order)
    documents = list(prop.documents)
    related = (
        Property.query
        .filter(Property.id != prop.id)
        .filter(Property.type == prop.type)
        .limit(3)
        .all()
    )

    return render_template(
        "property.html",
        data=None,
        property=prop,
        images=images,
        documents=documents,
        property_map_url=yandex_map_url(prop, zoom=16),
        responsible=prop.responsible_user,
        related=related,
        title=prop.title,
    )


@app.post("/favorite/<int:property_id>")
def toggle_favorite(property_id: int):
    ids = favorite_ids()

    if property_id in ids:
        ids.remove(property_id)
        flash("Объект удалён из избранного", "info")
    else:
        ids.append(property_id)
        flash("Объект добавлен в избранное", "success")

    session["favorites"] = ids
    return redirect(request.referrer or url_for("catalog"))


@app.route("/favorites")
def favorites_page():
    ids = favorite_ids()
    properties = Property.query.filter(Property.id.in_(ids)).all() if ids else []

    return render_template(
        "favorites.html",
        data=None,
        properties=properties,
        title="Избранное",
    )


@app.route("/apply/<int:property_id>", methods=["GET", "POST"])
@login_required
def apply(property_id: int):
    prop = Property.query.get_or_404(property_id)

    if request.method == "POST":
        year = datetime.now().year
        count = Application.query.filter(Application.number.startswith(str(year))).count() + 1

        application = Application(
            number=f"{year}-{count:04d}",
            application_type=request.form.get("application_type", "rent"),
            applicant_id=session["user_id"],
            property_id=property_id,
            desired_term=parse_int(request.form.get("desired_term")),
            purpose=request.form.get("purpose") or None,
            payment_method=request.form.get("payment_method") or None,
            planned_date=parse_date(request.form.get("planned_date")),
            status="pending",
            created_at=now_dt(),
        )

        db.session.add(application)
        db.session.commit()

        add_audit_log(
            "Подача заявки",
            "application",
            application.id,
            {"number": application.number, "type": application.application_type},
        )

        flash(f"Заявка №{application.number} успешно подана", "success")
        return redirect(url_for("profile"))

    return render_template(
        "apply.html",
        data=None,
        property=prop,
        title="Подача заявки",
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_value = request.form.get("login", "").strip()
        user = User.query.filter_by(login=login_value, is_active=True).first()

        if user:
            # В исходной демо-версии пароль не проверялся — оставлено для совместимости.
            session["user_id"] = user.id
            add_audit_log("Вход в систему", "user", user.id)
            flash("Вы успешно вошли в систему", "success")
            return redirect(request.args.get("next") or url_for("profile"))

        flash("Пользователь не найден или заблокирован", "error")

    return render_template("login.html", data=None, title="Вход")


@app.route("/logout")
def logout():
    user_id = session.get("user_id")

    if user_id:
        add_audit_log("Выход из системы", "user", user_id)

    session.pop("user_id", None)
    flash("Вы вышли из системы", "info")
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        login_value = request.form.get("login", "").strip()

        if User.query.filter_by(login=login_value).first():
            flash("Пользователь с таким логином уже существует", "error")
        else:
            user = User(
                login=login_value,
                password_hash=f"pbkdf2:sha256:{login_value}",
                full_name=request.form.get("full_name", "").strip(),
                email=request.form.get("email") or None,
                phone=request.form.get("phone") or None,
                role="user",
                is_active=True,
                created_at=now_dt(),
            )

            db.session.add(user)
            db.session.commit()

            session["user_id"] = user.id
            flash("Регистрация успешно завершена", "success")
            return redirect(url_for("profile"))

    return render_template("register.html", data=None, title="Регистрация")


@app.route("/profile")
@login_required
def profile():
    user = current_user()
    applications = (
        Application.query
        .filter_by(applicant_id=user.id)
        .order_by(Application.created_at.desc())
        .all()
    )
    contracts = Contract.query.filter_by(tenant_id=user.id).all()
    contract_ids = [contract.id for contract in contracts]
    payments = Payment.query.filter(Payment.contract_id.in_(contract_ids)).all() if contract_ids else []

    return render_template(
        "profile.html",
        data=None,
        user=user,
        applications=applications,
        contracts=contracts,
        payments=payments,
        title="Личный кабинет",
    )


@app.route("/admin", methods=["GET", "POST"])
@staff_required
def admin():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "add_property":
            prop = Property(
                title=request.form.get("title"),
                type=request.form.get("type"),
                address=request.form.get("address"),
                cadastral_number=request.form.get("cadastral_number") or None,
                area=parse_float(request.form.get("area")),
                description=request.form.get("description") or None,
                communications=request.form.get("communications") or None,
                condition=request.form.get("condition") or None,
                rent_price=parse_int(request.form.get("rent_price")),
                sale_price=parse_int(request.form.get("sale_price")),
                status=request.form.get("status", "available"),
                operation_type=request.form.get("operation_type", "rent"),
                responsible_user_id=session.get("user_id"),
                owner_name=request.form.get("owner_name") or None,
                ownership_date=parse_date(request.form.get("ownership_date")),
                ownership_basis=request.form.get("ownership_basis") or None,
                lat=parse_float(request.form.get("lat")),
                lng=parse_float(request.form.get("lng")),
                created_at=now_dt(),
                updated_at=now_dt(),
            )

            db.session.add(prop)
            db.session.commit()

            add_audit_log("Создание объекта", "property", prop.id, {"title": prop.title})
            flash("Объект добавлен", "success")

        elif action == "update_application":
            app_id = parse_int(request.form.get("application_id"))
            application = db.session.get(Application, app_id) if app_id else None

            if application:
                status = request.form.get("status")
                application.status = status
                application.reviewer_id = session.get("user_id")
                application.review_date = now_dt()
                application.rejection_reason = request.form.get("rejection_reason") or None

                if status == "approved" and application.property:
                    application.property.status = "reserved"
                    application.property.updated_at = now_dt()

                db.session.commit()
                add_audit_log("Обновление заявки", "application", application.id, {"status": status})
                flash("Статус заявки обновлён", "success")

        elif action == "add_news":
            news_item = News(
                title=request.form.get("title"),
                content=request.form.get("content"),
                author_id=session.get("user_id"),
                published_at=now_dt(),
            )

            db.session.add(news_item)
            db.session.commit()

            add_audit_log("Публикация новости", "news", news_item.id, {"title": news_item.title})
            flash("Новость опубликована", "success")

        return redirect(url_for("admin", tab=request.form.get("tab", "dashboard")))

    data = {
        "properties": Property.query.order_by(Property.id.asc()).all(),
        "applications": Application.query.order_by(Application.created_at.desc()).all(),
        "news": News.query.order_by(News.published_at.desc()).all(),
        "auditLog": AuditLog.query.order_by(AuditLog.created_at.desc()).all(),
    }

    stats = {
        "users": User.query.count(),
        "properties": Property.query.count(),
        "applications": Application.query.count(),
        "contracts": Contract.query.count(),
        "payments_pending": Payment.query.filter_by(status="pending").count(),
    }

    return render_template(
        "admin.html",
        data=data,
        stats=stats,
        tab=request.args.get("tab", "dashboard"),
        title="Админ-панель",
    )


@app.route("/news")
def news():
    items = News.query.order_by(News.published_at.desc()).all()

    return render_template(
        "news.html",
        data=None,
        news=items,
        title="Новости",
    )


@app.route("/about")
def about():
    return render_template("about.html", data=None, title="О поселении")


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html", data=None, title="Страница не найдена"), 404


if __name__ == "__main__":
    app.run(debug=True)
