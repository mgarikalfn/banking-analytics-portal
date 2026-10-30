# Banking Analytics Portal

Enterprise Banking Analytics Portal featuring a **Next.js (App Router) + TypeScript** frontend, a **FastAPI + SQLAlchemy 2.x async** backend, a **dedicated PostgreSQL application database**, and **Apache Superset Embedded SDK** integration for secure, role-governed dashboard delivery.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend (Port 3000)                    │
│  - App Router, Tailwind CSS, TypeScript                                │
│  - @superset-ui/embedded-sdk                                           │
│  - HTTP-Only session cookies & Double-Submit CSRF header               │
└───────────────────▲─────────────────────────────────▲──────────────────┘
                    │ REST (Cookie Auth + CSRF)       │ Scoped Guest Token
                    ▼                                 │ Embedded Iframe
┌───────────────────────────────────────┐             │
│       FastAPI Backend (Port 8000)     │             │
│  - Argon2 Password Hashing (pwdlib)   │             │
│  - Role-Based Access Control (RBAC)   │             │
│  - Dashboard Access Pre-Validation    │             │
│  - Superset Guest Token Generator     │             │
└───────▲───────────────────────┬───────┘             │
        │                       │ Service Auth        │
        │                       ▼ (Admin Credentials) │
┌───────┴───────────────┐  ┌──────────────────────────┴──────────────────┐
│ Dedicated Postgres DB │  │        Apache Superset (Port 8088)          │
│ (banking_portal_db)   │  │  - Isolated Analytical DWH Read Connection  │
│ Host Port: 5433       │  │  - Row-Level Security Ready                 │
│ Container Port: 5432  │  │                                             │
└───────────────────────┘  └─────────────────────────────────────────────┘
```

### Key Security & Operational Principles
1. **Schema Management via Alembic**: `Base.metadata.create_all()` is removed from startup. All table creation, constraints, and indexes are managed exclusively through tracked Alembic migrations (`alembic upgrade head`).
2. **Dedicated Application Database**: The portal uses its own database (`banking_portal_db`). It **never** connects to or modifies the live data warehouse (`bank_dwh_real`).
3. **Host Port 5433 Mapping**: In Docker Compose, the PostgreSQL container port `5432` maps to host port `5433` to prevent port collisions with any local PostgreSQL instance running on port `5432`.
4. **No Insecure Admin Fallbacks**: Fresh database initialization requires explicit `FIRST_SUPERUSER_EMAIL` and `FIRST_SUPERUSER_PASSWORD`. Known placeholders and default passwords are automatically rejected.
5. **Idempotent Data Seeding**: Subsequent backend restarts preserve existing administrator credentials and user modifications without overwriting passwords.
6. **HTTP-Only Session Cookies**: Authentication tokens are stored strictly in `HttpOnly`, `SameSite=Lax` cookies.
7. **Double-Submit CSRF Protection**: State-changing requests (`POST`, `PUT`, `PATCH`, `DELETE`) require an `X-CSRF-Token` header.
8. **Argon2id Password Hashing**: Passwords are saved with Argon2id using `pwdlib`.
9. **Optional Superset Configuration**: The Superset integration is inactive by default and does not attempt invalid network calls or report fake success until real service credentials are provided.

---

## Repository Structure

```
banking-analytics-portal/
├── .env.example                    # Root environment template for Docker Compose
├── .gitignore                      # Git ignore rules (.env, .venv, node_modules, .next)
├── docker-compose.yml              # PostgreSQL (port 5433), Backend (port 8000), Frontend (port 3000)
├── README.md
├── backend/
│   ├── .env.example                # Backend environment template
│   ├── alembic.ini                 # Alembic migration configuration
│   ├── alembic/
│   │   ├── env.py                  # Async migration runner
│   │   └── versions/
│   │       └── 386fe2a53b3e_initial_schema.py # Initial schema revision
│   ├── app/
│   │   ├── api/                    # API routes & dependency injection
│   │   │   ├── deps.py             # Auth, RBAC & CSRF dependencies
│   │   │   └── v1/                 # Endpoints: auth, dashboards, superset, users, roles, health
│   │   ├── core/                   # config, database, security, exceptions
│   │   ├── models/                 # SQLAlchemy 2.x models: User, Role, Dashboard, AuditLog
│   │   ├── repositories/           # Async repository data access layer
│   │   ├── schemas/                # Pydantic v2 DTO schemas
│   │   ├── services/               # AuthService, UserService, DashboardService, SupersetService
│   │   └── main.py                 # FastAPI application, startup lifespan & idempotent seed
│   ├── tests/                      # Pytest suite (22 automated tests)
│   ├── Dockerfile
│   └── requirements.txt
└── frontend/
    ├── .env.example
    ├── package.json
    ├── Dockerfile
    └── src/
        ├── app/                    # App Router pages (/login, /dashboard, /dashboard/[id], /admin)
        ├── components/             # SupersetDashboard, Navbar, Sidebar, DashboardCard, Guards
        ├── hooks/                  # useAuth, useDashboards, useSupersetGuestToken
        └── lib/                    # api.ts (cookie credentials & CSRF header), authContext.tsx
```

---

## Execution Guide

### Option 1: Running with Docker Compose (Recommended)

#### Step 1: Create `.env` from template
In the project root, copy the environment template:
```powershell
Copy-Item .env.example .env
```

Open `.env` and configure your secure credentials:
```ini
POSTGRES_PASSWORD=YourStrongDatabasePassword123!
SECRET_KEY=at_least_32_characters_random_hex_string_here
CSRF_SECRET_KEY=at_least_32_characters_random_csrf_secret_here

FIRST_SUPERUSER_EMAIL=admin@bankportal.internal
FIRST_SUPERUSER_PASSWORD=YourStrongAdminPassword123!
```

#### Step 2: Build and start the services
```powershell
docker compose up --build -d
```

#### Step 3: Run database migrations
Run the initial Alembic migration inside the backend container against `banking_portal_db`:
```powershell
docker compose exec backend alembic upgrade head
```

#### Step 4: Access the portal
- **Frontend Portal**: `http://localhost:3000`
- **FastAPI Documentation**: `http://localhost:8000/docs`
- **Application Database**: Accessible on host port `5433` (service internal: `app-db:5432`)

---

### Option 2: Running Natively on Windows (PowerShell)

#### Step 1: Database Setup
Ensure a PostgreSQL database named `banking_portal_db` is running (e.g. via Docker Compose `docker compose up -d app-db` or a dedicated local server on port 5433).

#### Step 2: Backend Setup
```powershell
cd backend

# Create backend .env
Copy-Item .env.example .env

# Configure .env with your database URL and required initial administrator password:
# DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5433/banking_portal_db
# FIRST_SUPERUSER_EMAIL=admin@bankportal.internal
# FIRST_SUPERUSER_PASSWORD=YourCustomStrongPassword123!

# Apply Alembic database migrations
.\.venv\Scripts\alembic.exe upgrade head

# Run automated tests to verify schema and security constraints
.\.venv\Scripts\pytest.exe -v

# Start FastAPI development server
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Step 3: Frontend Setup
In a second PowerShell window:
```powershell
# Prepend Node.js to PATH if required
$env:Path = "C:\Program Files\nodejs;" + $env:Path

cd frontend
Copy-Item .env.example .env.local
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## Initial Administrator Credentials

When the database is migrated and the backend boots for the first time, `init_default_data()` seeds:
1. Standard banking RBAC roles (`admin`, `executive`, `branch_manager`, `compliance_officer`, `financial_analyst`).
2. An initial administrator using `FIRST_SUPERUSER_EMAIL` and `FIRST_SUPERUSER_PASSWORD` configured in your `.env`.
3. Representative dashboard metadata with Superset UUID placeholders.

> [!IMPORTANT]
> The backend verifies that `FIRST_SUPERUSER_PASSWORD` is at least 8 characters and **not** a known default or placeholder.
> If an administrator already exists in the database, subsequent startups preserve the existing password without overwriting it.

---

## Apache Superset Configuration Checklist

When you are ready to connect a live Apache Superset instance:

1. **Enable Feature Flags in Superset** (`superset_config.py`):
   ```python
   FEATURE_FLAGS = {
       "EMBEDDED_SUPERSET": True,
   }
   GUEST_ROLE_NAME = "Public"
   SUPERSET_WEBSERVER_DOMAINS = ["http://localhost:3000"]
   ```

2. **Set Credentials in `.env`**:
   ```ini
   SUPERSET_BASE_URL="http://localhost:8088"
   SUPERSET_ADMIN_USERNAME="your-superset-admin"
   SUPERSET_ADMIN_PASSWORD="your-superset-password"
   ```

3. **Map Dashboard Embedded UUID**:
   In Apache Superset, click **...** -> **Embed dashboard** -> copy the **Embedded UUID**. Update the corresponding dashboard's `superset_dashboard_id` via the portal Admin API.
