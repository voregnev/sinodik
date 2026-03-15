---
phase: quick-2-add-superuser-with-login-admin-and-passw
plan: 2
type: execute
wave: 1
depends_on: []
files_modified:
  - app/config.py
  - app/main.py
  - app/models/models.py
  - app/api/routes/admin.py
  - app/api/routes/auth.py
  - app/services/auth_service.py
  - requirements.txt
  - alembic/versions/
autonomous: true
requirements: [quick-superuser]
user_setup: []
must_haves:
  truths:
    - "Superuser account exists at startup (email from env)"
    - "Superuser cannot be demoted or disabled via admin PATCH"
    - "Superuser can log in with email + password from .env and receive JWT"
  artifacts:
    - path: app/config.py
      provides: superuser_email, superuser_password settings
    - path: app/main.py
      provides: lifespan bootstrap of superuser user
    - path: app/api/routes/admin.py
      provides: PATCH guard for superuser
    - path: app/api/routes/auth.py
      provides: POST password-login for superuser
  key_links:
    - from: app/main.py lifespan
      to: User table
      via: get-or-create by superuser_email
    - from: app/api/routes/admin.py patch_user
      to: settings.superuser_email
      via: reject if target.email == superuser_email
    - from: app/api/routes/auth.py password login
      to: User.password_hash
      via: verify then issue JWT
---

<objective>
Добавить суперпользователя с логином (email) из .env и паролем из .env: пользователь всегда создаётся при старте, не может быть отключён/понижен через админку, может входить по email+пароль и получать JWT.
</objective>

<context>
@CLAUDE.md
@.planning/STATE.md

Текущее состояние:
- User: id, email, role, is_active, created_at (пароля нет).
- Админка: PATCH /api/v1/admin/users/{id} с guard "last admin"; удаления пользователей нет.
- Auth: request-otp, verify-otp, me; JWT через auth_service.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Config + bootstrap superuser in lifespan</name>
  <files>app/config.py, app/main.py, app/models/models.py</files>
  <action>
    - В config.py: добавить superuser_email: str = "admin@example.com" (SINODIK_SUPERUSER_EMAIL), superuser_password: str | None = None (SINODIK_SUPERUSER_PASSWORD, опционально).
    - В models.py: добавить в User опциональную колонку password_hash: Column(String(255), nullable=True). Создать миграцию Alembic (autogenerate) для новой колонки.
    - В main.py в lifespan после CREATE EXTENSION: использовать async_session из database (async with async_session() as session), выполнить get-or-create пользователя с email=settings.superuser_email, role="admin", is_active=True. Если settings.superuser_password задан — хешировать через passlib (bcrypt) и записать в user.password_hash. await session.commit() перед выходом из контекста.
  </action>
  <verify>
    <automated>grep -q "superuser_email\|superuser_password" app/config.py && echo "config ok"</automated>
  </verify>
  <done>При старте API пользователь с email=superuser_email существует, role=admin; при заданном SINODIK_SUPERUSER_PASSWORD у него заполнен password_hash.</done>
</task>

<task type="auto">
  <name>Task 2: Admin PATCH guard for superuser</name>
  <files>app/api/routes/admin.py, app/config.py</files>
  <action>
    - В admin.py в patch_user после загрузки user и проверки "not found": если user.email.lower() == settings.superuser_email.lower(), вызвать raise HTTPException(400, detail="Cannot modify or disable the superuser account") до любой логики с body.role/body.is_active.
  </action>
  <verify>
    <automated>pytest tests/ -v -k "admin" --tb=short 2>/dev/null || true; grep -n "superuser_email\|superuser" app/api/routes/admin.py app/config.py</automated>
  </verify>
  <done>PATCH /api/v1/admin/users/{id} для пользователя с email=superuser_email возвращает 400 и не меняет role/is_active.</done>
</task>

<task type="auto">
  <name>Task 3: Password login for superuser only</name>
  <files>app/config.py, app/services/auth_service.py, app/api/routes/auth.py, requirements.txt</files>
  <action>
    - В auth_service.py: добавить async def login_superuser(email: str, password: str, db: AsyncSession) -> dict | None. Если email.lower() != settings.superuser_email.lower() или не settings.superuser_password или у пользователя нет password_hash — return None. Иначе загрузить User по email, проверить пароль через passlib.verify(password, user.password_hash); при успехе сгенерировать JWT (как в verify_otp: payload с sub=email, exp), вернуть {"token": token, "user": {"id", "email", "role", "is_active"}}.
    - В auth.py: добавить Pydantic body LoginPasswordBody(email, password), эндпоинт POST /auth/password-login (или /auth/login с телом email+password). Вызвать login_superuser; если None — raise HTTPException(401, "Invalid credentials"). Вернуть token и user. Добавить passlib[bcrypt] в requirements.txt (в проекте его пока нет).
  </action>
  <verify>
    <automated>curl -s -X POST http://localhost:8000/api/v1/auth/password-login -H "Content-Type: application/json" -d '{"email":"admin@example.com","password":"'$SINODIK_SUPERUSER_PASSWORD'"}' | grep -q token 2>/dev/null || echo "Run with API up and SINODIK_SUPERUSER_PASSWORD set"; grep -n "login_superuser\|password_hash\|passlib" app/services/auth_service.py app/api/routes/auth.py</automated>
  </verify>
  <done>Суперпользователь может отправить POST /api/v1/auth/password-login с email и паролем из .env и получить JWT; для остальных возвращается 401.</done>
</task>

</tasks>

<verification>
- После старта API в БД есть пользователь с email=SINODIK_SUPERUSER_EMAIL, role=admin.
- PATCH этого пользователя по id возвращает 400.
- POST /api/v1/auth/password-login с правильными email/паролем возвращает token и user.
</verification>

<success_criteria>
- Суперпользователь создаётся при старте, не может быть отключён/понижен через админку, входит по паролю из .env и получает JWT.
</success_criteria>

<output>
After completion, create .planning/quick/2-add-superuser-with-login-admin-and-passw/2-SUMMARY.md
</output>
