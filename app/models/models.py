"""
Database models v2.

KEY CHANGE: атомарная единица — одно имя (Commemoration).
Каждая запись = одно конкретное имя с датами и типом.

СТРУКТУРА:
─────────────────────────────────────────────────────────────

  person              order                commemoration
  ────────            ────────             ──────────────────
  Справочник          Метаданные           ГЛАВНАЯ ТАБЛИЦА
  уникальных          заказа               Одно имя = одна запись
  имён                (кто, откуда)

  id                  id                   id
  canonical_name      user_email           person_id → person
  name_variants[]     source_channel       order_id  → order
  embedding           source_raw           order_type (здр/уп)
                      external_id          period_type
                      created_at           prefix
                                           ordered_at
                                           starts_at
                                           expires_at
                                           is_active

─────────────────────────────────────────────────────────────

  person (1) ←── (M) commemoration (M) ──→ (1) order
      ↑                    ↑
  справочник        атомарная единица
  для поиска        одно имя + даты

─────────────────────────────────────────────────────────────
"""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from config import settings
from database import Base


# ═══════════════════════════════════════════════════════════
#  PERSON — справочник уникальных имён
# ═══════════════════════════════════════════════════════════

class Person(Base):
    """
    Словарная запись: одно уникальное каноническое имя.

    Хранит embedding для fuzzy-поиска и варианты написания.
    НЕ хранит бизнес-логику (даты, типы) — это в Commemoration.
    """
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True)
    canonical_name = Column(String(100), nullable=False, unique=True)
    genitive_name = Column(String(100), nullable=True)        # родительный падеж
    gender = Column(String(1), nullable=True)                  # "м" | "ж"
    name_variants = Column(ARRAY(String), default=list)
    embedding = Column(Vector(settings.embedding_dim), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Все поминовения с этим именем
    # passive_deletes=True → при удалении Person каскад делает БД (ON DELETE CASCADE),
    # ORM не пытается выставить person_id = NULL (что ломает NOT NULL).
    commemorations = relationship(
        "models.models.Commemoration",
        back_populates="person",
        passive_deletes=True,
    )

    __table_args__ = (
        Index(
            "ix_persons_name_trgm",
            "canonical_name",
            postgresql_using="gin",
            postgresql_ops={"canonical_name": "gin_trgm_ops"},
        ),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<Person #{self.id} {self.canonical_name}>"


# ═══════════════════════════════════════════════════════════
#  ORDER — метаданные заказа (кто заказал, откуда пришло)
# ═══════════════════════════════════════════════════════════

class Order(Base):
    """
    Метаданные одного заказа (одна строка CSV / одна форма).

    Один заказ может породить N записей Commemoration
    (если в комментарии было несколько имён).

    user_email — идентификатор заказчика.
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)

    # ── Кто заказал ──
    user_email = Column(String(255), nullable=True, index=True)
    need_receipt = Column(Boolean, nullable=False, default=False)

    # ── Откуда пришло ──
    source_channel = Column(String(30), default="csv")      # csv | form | api
    source_raw = Column(Text, nullable=True)                 # исходный текст целиком
    external_id = Column(String(100), unique=True, nullable=True)  # tranid из CSV

    # Редактируемая дата заказа (отличается от created_at)
    ordered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Тип и период по умолчанию (для повторного парсинга source_raw при пустых поминовениях)
    order_type = Column(String(20), nullable=True)   # здравие | упокоение
    period_type = Column(String(30), nullable=True)  # разовое | сорокоуст | полгода | год

    # Все поминовения из этого заказа
    commemorations = relationship("models.models.Commemoration", back_populates="order")

    __table_args__ = ({"extend_existing": True},)

    def __repr__(self):
        return f"<Order #{self.id} from={self.user_email} ch={self.source_channel}>"


# ═══════════════════════════════════════════════════════════
#  COMMEMORATION — главная таблица, атомарная единица
# ═══════════════════════════════════════════════════════════

class Commemoration(Base):
    """
    ОДНА запись поминовения = ОДНО имя.

    Это конечная единица системы:
      «Поминать Николая (воин) о здравии,
       заказано 2026-02-21, начало чтения 2026-02-22,
       окончание 2026-04-02 (сорокоуст)».

    Все даты:
      ordered_at  — когда заказ оформлен (дата из CSV/формы)
      starts_at   — когда начинается чтение (может отличаться)
      expires_at  — когда заканчивается (вычисляется от starts_at + период)
    """
    __tablename__ = "commemorations"

    id = Column(Integer, primary_key=True)

    # ── Связи ──
    person_id = Column(
        Integer,
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # ── Тип поминовения ──
    order_type = Column(String(20), nullable=False)       # здравие | упокоение
    period_type = Column(String(30), nullable=False)       # разовое | сорокоуст | полгода | год
    prefix = Column(String(100), nullable=True)            # иер., в., нпр., мл. и т.д. (может быть 2 подряд)
    suffix = Column(String(100), nullable=True)            # со чадом / со чады

    # ── Три ключевые даты ──
    ordered_at = Column(DateTime(timezone=True), nullable=False)   # когда оформлен заказ
    starts_at = Column(DateTime(timezone=True), nullable=True)     # когда начинается (NULL = ещё не назначено)
    expires_at = Column(DateTime(timezone=True), nullable=True)    # когда заканчивается (NULL = ещё не назначено)

    # ── Позиция в исходной записке (1-based) ──
    position = Column(Integer, nullable=True)

    # ── Статус ──
    is_active = Column(Boolean, default=True, index=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # ── ORM relationships ──
    person = relationship("models.models.Person", back_populates="commemorations")
    order = relationship("models.models.Order", back_populates="commemorations")

    __table_args__ = (
        Index("ix_comm_active", "is_active", "expires_at"),
        Index("ix_comm_type_expires", "order_type", "expires_at"),
        {"extend_existing": True},
    )

    def __repr__(self):
        return (
            f"<Commemoration #{self.id} "
            f"person={self.person_id} "
            f"{self.order_type} {self.period_type} "
            f"until {self.expires_at}>"
        )


# ═══════════════════════════════════════════════════════════
#  USER — учётная запись пользователя
# ═══════════════════════════════════════════════════════════

class User(Base):
    """
    Учётная запись пользователя.
    Создаётся автоматически при первой успешной верификации OTP.
    Роль admin назначается если email присутствует в settings.admin_emails.
    """
    __tablename__ = "users"
    __table_args__ = ({"extend_existing": True},)

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    role = Column(String(20), nullable=False, default="user")   # "user" | "admin"
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<User #{self.id} {self.email} role={self.role}>"


# ═══════════════════════════════════════════════════════════
#  OTP_CODE — одноразовый код подтверждения
# ═══════════════════════════════════════════════════════════

class OtpCode(Base):
    """
    Одноразовый код подтверждения (OTP).
    email хранится без FK на users — код запрашивается до создания аккаунта.
    code_hash: SHA-256 hex (заполняется в Phase 2).
    attempt_count: счётчик неудачных попыток; при >= 5 код инвалидируется (Phase 2).
    """
    __tablename__ = "otp_codes"
    __table_args__ = ({"extend_existing": True},)

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, index=True)
    code_hash = Column(String(64), nullable=True)               # SHA-256 hex; Phase 2
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    attempt_count = Column(Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<OtpCode #{self.id} email={self.email} used={self.used}>"
