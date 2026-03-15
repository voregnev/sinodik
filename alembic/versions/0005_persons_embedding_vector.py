"""Switch persons.embedding to pgvector with dynamic dimension.

Берём размерность из окружения SINODIK_EMBEDDING_DIM.

ВНИМАНИЕ: миграция разрушающая для старых эмбеддингов:
  - старая колонка embedding (JSONB/любого типа) удаляется,
  - создаётся новая embedding vector(DIM),
  - создаётся ivfflat‑индекс по новой колонке.
"""

import os

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _get_dim(default: int = 384) -> int:
    raw = os.environ.get("SINODIK_EMBEDDING_DIM")
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


def upgrade() -> None:
    dim = _get_dim()
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Проверяем, что таблица persons существует
    tables = {t for t in inspector.get_table_names()}
    if "persons" not in tables:
        return

    cols = {c["name"]: c for c in inspector.get_columns("persons")}

    # 1) Определяем текущий тип и размерность embedding (если колонка есть).
    current_dim = None
    is_vector = False

    if "embedding" in cols:
        res = bind.execute(
            sa.text(
                """
                SELECT t.typname, a.atttypmod
                FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                JOIN pg_type t ON a.atttypid = t.oid
                WHERE c.relname = 'persons'
                  AND a.attname = 'embedding'
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                """
            )
        ).fetchone()

        if res is not None:
            typname, atttypmod = res
            if typname == "vector" and atttypmod is not None and atttypmod > 0:
                is_vector = True
                # В pgvector размерность кодируется в atttypmod: dim = atttypmod - 4
                current_dim = atttypmod - 4

    # 2) Если embedding уже vector с той же размерностью — колонку не трогаем,
    # просто убеждаемся, что индекс есть/пересоздан.
    if is_vector and current_dim == dim:
        pass
    else:
        # Либо нет колонки, либо она не vector, либо другая размерность —
        # пересоздаём колонку целиком.
        if "embedding" in cols:
            op.drop_column("persons", "embedding")

        op.execute(
            sa.text(f"ALTER TABLE persons ADD COLUMN embedding vector({dim}) NULL")
        )

    # 3) Пересоздаём ivfflat‑индекс по embedding.
    # Сначала пытаемся удалить старый индекс, если он есть.
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
              idx_name text;
            BEGIN
              SELECT indexname
                INTO idx_name
              FROM pg_indexes
              WHERE schemaname = 'public'
                AND tablename = 'persons'
                AND indexname = 'ix_persons_embedding';

              IF idx_name IS NOT NULL THEN
                EXECUTE 'DROP INDEX IF EXISTS ' || quote_ident(idx_name);
              END IF;
            END
            $$;
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE INDEX ix_persons_embedding
              ON persons
              USING ivfflat (embedding vector_l2_ops)
              WITH (lists = 100);
            """
        )
    )


def downgrade() -> None:
    # В даунгрейде возвращаемся к простой JSONB‑колонке без индекса.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = {t for t in inspector.get_table_names()}
    if "persons" not in tables:
        return

    # Удаляем векторный индекс, если он есть.
    op.execute(
        sa.text("DROP INDEX IF EXISTS ix_persons_embedding")
    )

    cols = {c["name"]: c for c in inspector.get_columns("persons")}
    if "embedding" in cols:
        op.drop_column("persons", "embedding")

    # Восстанавливаем embedding как JSONB (как в 0001).
    op.add_column(
        "persons",
        sa.Column(
            "embedding",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

