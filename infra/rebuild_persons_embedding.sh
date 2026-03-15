#!/usr/bin/env bash
set -euo pipefail

# Создаёт альтернативную vector‑колонку для эмбеддингов в persons
# и пересобирает индекс с учётом новой размерности.
#
# Использует:
#   - SINODIK_EMBEDDING_DIM — желаемая размерность вектора
#   - docker compose exec db ... (см. docker-compose.yml)
#
# Пример:
#   SINODIK_EMBEDDING_DIM=256 ./infra/rebuild_persons_embedding.sh
#
# После запуска:
#   - появляется колонка persons.embedding_vec_new vector(DIM)
#   - создаётся ivfflat‑индекс ix_persons_embedding_vec_new

DIM="${SINODIK_EMBEDDING_DIM:-384}"

echo "Using SINODIK_EMBEDDING_DIM=${DIM}"

# Проверяем, что dim — положительное число
if ! [[ "${DIM}" =~ ^[0-9]+$ ]] || [ "${DIM}" -le 0 ]; then
  echo "ERROR: SINODIK_EMBEDDING_DIM must be a positive integer, got: '${DIM}'" >&2
  exit 1
fi

echo "Running migrations for persons.embedding_vec_new in database 'sinodik' (container: sinodik-db)..."

docker compose exec -T db psql -U sinodik -d sinodik <<SQL
-- Создаём новую колонку с типом vector(DIM), если её ещё нет
ALTER TABLE persons
  ADD COLUMN IF NOT EXISTS embedding_vec_new vector(${DIM});

-- Удаляем старый индекс по embedding_vec_new, если он есть
DO \$\$
DECLARE
  idx_name text;
BEGIN
  SELECT indexname
    INTO idx_name
  FROM pg_indexes
  WHERE schemaname = 'public'
    AND tablename = 'persons'
    AND indexname = 'ix_persons_embedding_vec_new';

  IF idx_name IS NOT NULL THEN
    EXECUTE 'DROP INDEX IF EXISTS ' || quote_ident(idx_name);
  END IF;
END
\$\$;

-- Создаём новый ivfflat‑индекс по новой колонке
CREATE INDEX ix_persons_embedding_vec_new
  ON persons
  USING ivfflat (embedding_vec_new vector_l2_ops)
  WITH (lists = 100);
SQL

echo "Done. Column 'embedding_vec_new' and index 'ix_persons_embedding_vec_new' are in place."

