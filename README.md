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
│ Users, Roles, Audits  │  │  - Row-Level Security Ready                 │
└───────────────────────┘  └─────────────────────────────────────────────┘
```

### Key Security Safeguards
1. **HTTP-Only Session Cookies**: Authentication tokens are stored strictly in `HttpOnly`, `SameSite=Lax` cookies to prevent client-side script theft (XSS).
2. **Double-Submit CSRF Protection**: State-changing requests (`POST`, `PUT`, `PATCH`, `DELETE`) require an `X-CSRF-Token` header matching the readable CSRF cookie.
3. **Argon2id Password Hashing**: Passwords hashed with state-of-the-art Argon2id via `pwdlib`.
4. **Backend-Enforced Dashboard Permissions**: Access is verified on the backend before any Superset guest token is requested.
5. **Zero Credential Exposure**: Superset admin service credentials never touch the browser.
6. **Data Warehouse Isolation**: The portal maintains its own dedicated application database (`banking_portal_db`). The live data warehouse (`bank_dwh_real`) is never written to or modified by the portal application.
7. **Branch-Level RLS Ready**: Architecture includes placeholder hooks for verified branch-level Row-Level Security once production branch mappings and warehouse schema are confirmed.

---

## Repository Structure

```
banking-analytics-portal/
├── backend/
│   ├── .venv/                      # Python 3.13 virtual environment
│   ├── app/
│   │   ├── api/                    # API routes & dependency injection
│   │   │   ├── deps.py             # Auth, RBAC & CSRF dependencies
│   │   │   └── v1/
│   │   │       ├── endpoints/      # auth, dashboards, superset, users, roles, health
│   │   │       └── router.py       # V1 router aggregation
│   │   ├── core/                   # config, database, security, exceptions
│   │   ├── models/                 # SQLAlchemy 2.x async models (User, Role, Dashboard, AuditLog)
│   │   ├── schemas/                # Pydantic v2 DTO schemas
│   │   ├── repositories/           # Async repository pattern
│   │   ├── services/               # AuthService, UserService, DashboardService, SupersetService
│   │   └── main.py                 # FastAPI application & startup seed
│   ├── alembic/                    # Database migration configuration
│   ├── tests/                      # Pytest suite (auth, csrf, rbac, dashboards, superset)
│   ├── .env.example                # Backend configuration template
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                    # App Router pages (/login, /dashboard, /dashboard/[id], /admin)
│   │   ├── components/             # Navbar, Sidebar, SupersetDashboard, DashboardCard, Guards
│   │   ├── hooks/                  # useAuth, useDashboards, useSupersetGuestToken
│   │   ├── lib/                    # api.ts (credentials & CSRF), csrf.ts, authContext.tsx
│   │   └── types/                  # TypeScript interfaces
│   ├── public/
│   ├── .env.example
│   ├── Dockerfile
│   ├── package.json
│   └── tsconfig.json
├── docker-compose.yml              # PostgreSQL, Backend, and Frontend orchestration
└── README.md
```

---

## Windows Setup & Execution Guide

### Prerequisites
- Python 3.13 (already configured under `backend/.venv`)
- Node.js 20+ (Node.js 24 installed in `C:\Program Files\nodejs`)
- PostgreSQL 16+ or Docker Desktop

---

### Method A: Running Natively on Windows

#### 1. Backend Setup

Open PowerShell in the project root:

```powershell
cd backend

# Copy environment template
Copy-Item .env.example .env

# Run automated tests to verify environment
.\.venv\Scripts\pytest.exe -v

# Start the FastAPI server
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend starts at `http://127.0.0.1:8000`.
- Swagger API Docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/v1/health/`

On first launch, the backend automatically seeds:
- Base roles: `admin`, `executive`, `branch_manager`, `compliance_officer`, `financial_analyst`
- Default superuser: `admin@bankportal.internal` / `AdminBanking123!`
- Initial dashboard catalog entries with Superset UUID placeholders

#### 2. Frontend Setup

In a new PowerShell window:

```powershell
# Ensure node is in PATH for this session if needed:
$env:Path = "C:\Program Files\nodejs;" + $env:Path

cd frontend

# Copy environment template
Copy-Item .env.example .env.local

# Run production build or development server
npm run dev
```

The frontend portal will be available at `http://localhost:3000`.

---

### Method B: Running via Docker Compose

```powershell
# Start application database, backend, and frontend
docker compose up --build -d

# Check running containers
docker compose ps

# View logs
docker compose logs -f backend
```

---

## Pre-seeded Credentials for Testing

| Role | Email | Password | Scope |
| :--- | :--- | :--- | :--- |
| **System Administrator** | `admin@bankportal.internal` | `AdminBanking123!` | Full admin, user & role management, all dashboards |

*(Additional users with specific branch or risk roles can be registered directly from the `/admin` portal page).*

---

## Apache Superset Configuration Checklist

To connect live Superset dashboards to the portal:

1. **Enable Feature Flags in Superset**:
   In your Superset `superset_config.py`, enable embedding and guest role access:
   ```python
   FEATURE_FLAGS = {
       "EMBEDDED_SUPERSET": True,
   }
   GUEST_ROLE_NAME = "Public"
   GUEST_TOKEN_JWT_SECRET = "your-superset-guest-token-secret"
   GUEST_TOKEN_JWT_ALGO = "HS256"
   SUPERSET_WEBSERVER_DOMAINS = ["http://localhost:3000"]
   ```

2. **Configure Backend Credentials**:
   In `backend/.env`:
   ```ini
   SUPERSET_BASE_URL="http://localhost:8088"
   SUPERSET_ADMIN_USERNAME="admin"
   SUPERSET_ADMIN_PASSWORD="your-real-superset-admin-password"
   ```

3. **Enable Embedded Access in Superset UI**:
   - Open your dashboard in Apache Superset.
   - Click the **...** menu in the top right -> **Embed dashboard**.
   - Copy the generated **Embedded UUID**.
   - Update the corresponding dashboard in the portal (via database or admin endpoint) with the matching `superset_dashboard_id`.

---

## Remaining Operational Considerations
- **Production Secret Rotation**: Replace `SECRET_KEY` and `CSRF_SECRET_KEY` with cryptographically generated random strings (`openssl rand -hex 32`).
- **HTTPS & Cookie Security**: Set `COOKIE_SECURE=true` in `backend/.env` once deploying behind HTTPS/TLS reverse proxy.
- **Verified Branch Schema Mapping**: When branch-level datasets in the warehouse are finalized, link `assigned_branch_id` to the dataset filter clauses in `app/services/superset_service.py`.
