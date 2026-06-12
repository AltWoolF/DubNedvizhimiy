from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Настройки приложения.

    Если в .env задан DATABASE_URL — используется он.
    Если задан MYSQL_DATABASE — собирается подключение к MySQL.
    Если MySQL-настройки не заданы — используется SQLite для локального запуска/проверки.
    """

    SECRET_KEY = os.environ.get("SECRET_KEY", "dub-nedvizhimy-dev-secret")

    DATABASE_URL = os.environ.get("DATABASE_URL")

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE")

    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    elif MYSQL_DATABASE:
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
            f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
        )
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'dub_nedvizhimy.db'}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
