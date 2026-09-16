"""Partner App Integration Platform - Mock Backend.

FastAPI-only implementation (no database/ORM/containers). All data lives in
in-memory dicts and resets whenever the process restarts. Authentication uses
simple mock bearer tokens - NOT real JWT signing or production-grade password
hashing. This exists purely to exercise the API contract described in api.md.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, model_validator

# ==================================================
# ENUMS
# ==================================================


class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    VIEWER = "VIEWER"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class PartnerStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class PartnerAppStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class ClientStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class IntegrationType(str, Enum):
    WEB = "WEB"
    DEEPLINK = "DEEPLINK"
    NATIVE = "NATIVE"
    SDK = "SDK"
    API = "API"
    HYBRID = "HYBRID"


class DeploymentStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ROLLED_BACK = "ROLLED_BACK"


class TabName(str, Enum):
    SWIGGY = "SWIGGY"
    SWIGGY_INSTAMART = "SWIGGY_INSTAMART"
    BIGBASKET = "BIGBASKET"
    DOMINOS = "DOMINOS"


def favicon(domain: str) -> str:
    return f"https://www.google.com/s2/favicons?domain={domain}&sz=64"


# Predefined external partner links surfaced to the mobile app (static config, not per-client).
THIRD_PARTY_TABS: Dict[TabName, dict] = {
    TabName.SWIGGY: {
        "key": "swiggy",
        "label": "Order Food",
        "url": "https://www.swiggy.com/",
        "icon": favicon("swiggy.com"),
    },
    TabName.SWIGGY_INSTAMART: {
        "key": "swiggyinstamart",
        "label": "Instamart",
        "url": "https://www.swiggy.com/instamart",
        "icon": favicon("swiggy.com"),
    },
    TabName.BIGBASKET: {
        "key": "bigbasket",
        "label": "BigBasket",
        "url": "https://www.bigbasket.com",
        "icon": favicon("bigbasket.com"),
    },
    TabName.DOMINOS: {
        "key": "dominos",
        "label": "Domino's",
        "url": "https://www.dominos.co.in",
        "icon": favicon("dominos.co.in"),
    },
}


# ==================================================
# TEST DASHBOARD (dev only - static page, no external assets)
# ==================================================

TEST_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"UTF-8\">
<title>Mock API - Health Dashboard</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 760px; margin: 2rem auto; padding: 0 1rem; }
  h1 { font-size: 1.4rem; }
  .row { display: flex; gap: .5rem; margin-bottom: 1rem; }
  input { flex: 1; padding: .4rem; }
  button { padding: .5rem 1rem; cursor: pointer; }
  ul { list-style: none; padding: 0; }
  li { padding: .5rem .75rem; border-radius: 4px; margin-bottom: .4rem; font-family: monospace; font-size: .85rem; white-space: pre-wrap; }
  .pass { background: #e6ffed; border: 1px solid #2ea44f; }
  .fail { background: #ffeef0; border: 1px solid #d73a49; }
  .pending { background: #f1f3f5; border: 1px solid #ccc; }
</style>
</head>
<body>
  <h1>Mock API - Health Dashboard</h1>
  <p>Runs a sequence of real requests against this running server and reports pass/fail.</p>
  <div class=\"row\">
    <input id=\"email\" value=\"admin@example.com\" placeholder=\"email\">
    <input id=\"password\" value=\"Admin123!\" type=\"password\" placeholder=\"password\">
    <button onclick=\"runAll()\">Run All Checks</button>
  </div>
  <ul id=\"results\"></ul>

<script>
const resultsEl = document.getElementById('results');

function addResult(name, passed, detail) {
  const li = document.createElement('li');
  li.className = passed ? 'pass' : 'fail';
  li.textContent = (passed ? 'PASS  ' : 'FAIL  ') + name + '\\n' + detail;
  resultsEl.appendChild(li);
}

async function call(method, path, body, token) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = 'Bearer ' + token;
  const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  let data = null;
  try { data = await res.json(); } catch (e) { /* no body */ }
  return { ok: res.ok, status: res.status, data };
}

async function runAll() {
  resultsEl.innerHTML = '';
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;

  const health = await call('GET', '/health');
  addResult('GET /health', health.ok, JSON.stringify(health.data));

  const login = await call('POST', '/api/v1/auth/login', { email, password });
  addResult('POST /api/v1/auth/login', login.ok, JSON.stringify(login.data));
  if (!login.ok) return;
  const token = login.data.data.accessToken;

  const me = await call('GET', '/api/v1/auth/me', null, token);
  addResult('GET /api/v1/auth/me', me.ok, JSON.stringify(me.data));

  const partners = await call('GET', '/api/v1/partners', null, token);
  addResult('GET /api/v1/partners', partners.ok, JSON.stringify(partners.data).slice(0, 300));

  const apps = await call('GET', '/api/v1/partner-apps', null, token);
  addResult('GET /api/v1/partner-apps', apps.ok, JSON.stringify(apps.data).slice(0, 300));

  const clients = await call('GET', '/api/v1/clients', null, token);
  addResult('GET /api/v1/clients', clients.ok, JSON.stringify(clients.data).slice(0, 300));
  if (!clients.ok || !clients.data.data.items.length) return;
  const client = clients.data.data.items[0];

  const integrations = await call('GET', `/api/v1/clients/${client.id}/integrations`, null, token);
  addResult('GET /api/v1/clients/{id}/integrations', integrations.ok, JSON.stringify(integrations.data).slice(0, 300));

  const deployments = await call('GET', `/api/v1/clients/${client.id}/deployments`, null, token);
  addResult('GET /api/v1/clients/{id}/deployments', deployments.ok, JSON.stringify(deployments.data).slice(0, 300));

  if (client.api_key) {
    const mobileRes = await fetch('/api/v1/mobile/integrations', { headers: { 'X-Api-Key': client.api_key } });
    const mobileData = await mobileRes.json();
    addResult('GET /api/v1/mobile/integrations', mobileRes.ok, JSON.stringify(mobileData).slice(0, 300));
  }
}
</script>
</body>
</html>
"""


# ==================================================
# IN-MEMORY STORAGE
# ==================================================

users_db: Dict[str, dict] = {}
partners_db: Dict[str, dict] = {}
partner_apps_db: Dict[str, dict] = {}
clients_db: Dict[str, dict] = {}
client_integrations_db: Dict[str, dict] = {}
deployments_db: Dict[str, dict] = {}
deployment_items_db: Dict[str, dict] = {}
audit_logs_db: Dict[str, dict] = {}

access_tokens: Dict[str, dict] = {}
refresh_tokens: Dict[str, dict] = {}

ACCESS_TOKEN_TTL = timedelta(days=2)
REFRESH_TOKEN_TTL = timedelta(days=7)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid4())


# ==================================================
# ERRORS / RESPONSE ENVELOPE
# ==================================================


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


def ok(data: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"success": True, "data": data})


def paginate(items: List[dict], page: int, page_size: int) -> dict:
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return {
        "items": items[start:end],
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": total_pages,
        },
    }


def record_audit(user_id: Optional[str], action: str, entity_type: str, entity_id: str,
                  old_value: Optional[dict] = None, new_value: Optional[dict] = None) -> None:
    log_id = new_id()
    audit_logs_db[log_id] = {
        "id": log_id,
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "old_value": old_value,
        "new_value": new_value,
        "created_at": now_iso(),
    }


# ==================================================
# APP SETUP
# ==================================================

app = FastAPI(
    title="Partner App Integration Platform (Mock)",
    description="In-memory FastAPI mock implementation of the Partner App Integration Platform API.",
    version="1.0.0",
)


access_log_db: List[dict] = []
MAX_ACCESS_LOG_ENTRIES = 500


def resolve_caller_identity(request: Request) -> str:
    """Best-effort identity for access logging - never raises, never logs the raw token."""
    authorization = request.headers.get("authorization")
    if authorization and authorization.startswith("Bearer "):
        entry = access_tokens.get(authorization.split(" ", 1)[1])
        user = users_db.get(entry["user_id"]) if entry else None
        if user:
            return f"user:{user['email']}"
        return "user:invalid-token"
    api_key = request.headers.get("x-api-key")
    if api_key:
        client = next((c for c in clients_db.values() if c["api_key"] == api_key), None)
        return f"client:{client['name']}" if client else "client:invalid-key"
    return "anonymous"


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    response = await call_next(request)
    entry = {
        "timestamp": now_iso(),
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "client_ip": request.client.host if request.client else None,
        "identity": resolve_caller_identity(request),
    }
    access_log_db.append(entry)
    del access_log_db[:-MAX_ACCESS_LOG_ENTRIES]
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        code, message = detail["code"], detail.get("message", "")
    else:
        code, message = "HTTP_ERROR", str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": code, "message": message}},
    )


# ==================================================
# AUTH HELPERS (mock only - not production-grade)
# ==================================================


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def issue_tokens(user: dict) -> tuple[str, str]:
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(32)
    access_tokens[access_token] = {
        "user_id": user["id"],
        "expires_at": datetime.now(timezone.utc) + ACCESS_TOKEN_TTL,
    }
    refresh_tokens[refresh_token] = {
        "user_id": user["id"],
        "expires_at": datetime.now(timezone.utc) + REFRESH_TOKEN_TTL,
    }
    return access_token, refresh_token


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("UNAUTHORIZED", "Missing or invalid Authorization header", 401)
    token = authorization.split(" ", 1)[1]
    entry = access_tokens.get(token)
    if not entry or entry["expires_at"] < datetime.now(timezone.utc):
        raise AppError("UNAUTHORIZED", "Invalid or expired access token", 401)
    user = users_db.get(entry["user_id"])
    if not user or user["status"] != UserStatus.ACTIVE:
        raise AppError("UNAUTHORIZED", "User not found or disabled", 401)
    return user


def require_roles(*roles: UserRole):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise AppError("FORBIDDEN", "Insufficient permissions", 403)
        return user

    return checker


def get_current_client(x_api_key: Optional[str] = Header(None)) -> dict:
    """Identifies the mobile client via a per-client API key (never a raw client id)."""
    if not x_api_key:
        raise AppError("UNAUTHORIZED", "Missing X-Api-Key header", 401)
    client = next((c for c in clients_db.values() if c["api_key"] == x_api_key), None)
    if not client or client["status"] != ClientStatus.ACTIVE:
        raise AppError("UNAUTHORIZED", "Invalid client API key", 401)
    return client


# ==================================================
# REQUEST SCHEMAS
# ==================================================


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PartnerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    status: PartnerStatus = PartnerStatus.DRAFT


class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    status: Optional[PartnerStatus] = None


class PartnerAppCreate(BaseModel):
    partner_id: str
    name: str
    description: Optional[str] = None
    integration_type: IntegrationType = IntegrationType.WEB
    version: Optional[str] = None
    launch_url: Optional[str] = None
    deep_link: Optional[str] = None
    configuration: dict = Field(default_factory=dict)
    status: PartnerAppStatus = PartnerAppStatus.DRAFT

    @model_validator(mode="after")
    def check_web_launch_url(self):
        if self.integration_type == IntegrationType.WEB and not self.launch_url:
            raise ValueError("launch_url is required for WEB integrations")
        return self


class PartnerAppUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    integration_type: Optional[IntegrationType] = None
    version: Optional[str] = None
    launch_url: Optional[str] = None
    deep_link: Optional[str] = None
    configuration: Optional[dict] = None
    status: Optional[PartnerAppStatus] = None


class ClientCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    status: ClientStatus = ClientStatus.ACTIVE


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ClientStatus] = None


class ClientIntegrationCreate(BaseModel):
    partner_id: str
    partner_app_id: str
    enabled: bool = True
    display_name: Optional[str] = None
    display_order: int = 0
    configuration: dict = Field(default_factory=dict)


class ClientIntegrationUpdate(BaseModel):
    enabled: Optional[bool] = None
    display_name: Optional[str] = None
    display_order: Optional[int] = None
    configuration: Optional[dict] = None


# ==================================================
# LOOKUP HELPERS
# ==================================================


def get_partner_or_404(partner_id: str) -> dict:
    partner = partners_db.get(partner_id)
    if not partner:
        raise AppError("PARTNER_NOT_FOUND", "Partner not found", 404)
    return partner


def get_partner_app_or_404(app_id: str) -> dict:
    partner_app = partner_apps_db.get(app_id)
    if not partner_app:
        raise AppError("PARTNER_APP_NOT_FOUND", "Partner app not found", 404)
    return partner_app


def get_client_or_404(client_id: str) -> dict:
    client = clients_db.get(client_id)
    if not client:
        raise AppError("CLIENT_NOT_FOUND", "Client not found", 404)
    return client


def get_integration_or_404(client_id: str, integration_id: str) -> dict:
    integration = client_integrations_db.get(integration_id)
    if not integration or integration["client_id"] != client_id:
        raise AppError("INTEGRATION_NOT_FOUND", "Client integration not found", 404)
    return integration


def get_deployment_or_404(deployment_id: str) -> dict:
    deployment = deployments_db.get(deployment_id)
    if not deployment:
        raise AppError("DEPLOYMENT_NOT_FOUND", "Deployment not found", 404)
    return deployment


# ==================================================
# HEALTH
# ==================================================


@app.get("/health")
def health():
    return ok({"status": "ok"})


@app.get("/test", response_class=HTMLResponse, include_in_schema=False)
def test_dashboard():
    """Zero-dependency browser page that exercises the main endpoints and reports pass/fail."""
    return TEST_DASHBOARD_HTML


# ==================================================
# AUTH
# ==================================================


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest):
    user = next((u for u in users_db.values() if u["email"] == payload.email), None)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise AppError("UNAUTHORIZED", "Invalid email or password", 401)
    if user["status"] != UserStatus.ACTIVE:
        raise AppError("FORBIDDEN", "User is disabled", 403)
    access_token, refresh_token = issue_tokens(user)
    record_audit(user["id"], "LOGIN", "user", user["id"])
    return ok({
        "accessToken": access_token,
        "accessTokenExpiresAt": access_tokens[access_token]["expires_at"].isoformat(),
        "expiresIn": int(ACCESS_TOKEN_TTL.total_seconds()),
        "refreshToken": refresh_token,
        "refreshTokenExpiresAt": refresh_tokens[refresh_token]["expires_at"].isoformat(),
        "user": public_user(user),
    })


@app.post("/api/v1/auth/refresh")
def refresh(payload: RefreshRequest):
    entry = refresh_tokens.get(payload.refresh_token)
    if not entry or entry["expires_at"] < datetime.now(timezone.utc):
        raise AppError("UNAUTHORIZED", "Invalid or expired refresh token", 401)
    user = users_db.get(entry["user_id"])
    if not user or user["status"] != UserStatus.ACTIVE:
        raise AppError("UNAUTHORIZED", "User not found or disabled", 401)
    access_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + ACCESS_TOKEN_TTL
    access_tokens[access_token] = {
        "user_id": user["id"],
        "expires_at": expires_at,
    }
    return ok({
        "accessToken": access_token,
        "accessTokenExpiresAt": expires_at.isoformat(),
        "expiresIn": int(ACCESS_TOKEN_TTL.total_seconds()),
    })


@app.post("/api/v1/auth/logout")
def logout(authorization: Optional[str] = Header(None), user: dict = Depends(get_current_user)):
    token = authorization.split(" ", 1)[1]
    access_tokens.pop(token, None)
    record_audit(user["id"], "LOGOUT", "user", user["id"])
    return ok({"loggedOut": True})


@app.get("/api/v1/auth/me")
def me(authorization: Optional[str] = Header(None), user: dict = Depends(get_current_user)):
    token = authorization.split(" ", 1)[1]
    expires_at = access_tokens[token]["expires_at"]
    return ok({**public_user(user), "accessTokenExpiresAt": expires_at.isoformat()})


def public_user(user: dict) -> dict:
    return {k: v for k, v in user.items() if k != "password_hash"}


# ==================================================
# PARTNERS
# ==================================================


@app.get("/api/v1/partners")
def list_partners(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    items = list(partners_db.values())
    if search:
        needle = search.lower()
        items = [p for p in items if needle in p["name"].lower()]
    items = sorted(items, key=lambda p: p["created_at"])
    return ok(paginate(items, page, pageSize))


@app.get("/api/v1/partners/{partner_id}")
def get_partner(partner_id: str, user: dict = Depends(get_current_user)):
    return ok(get_partner_or_404(partner_id))


@app.get("/api/v1/partners/{partner_id}/apps")
def get_partner_apps_for_partner(partner_id: str, user: dict = Depends(get_current_user)):
    get_partner_or_404(partner_id)
    items = [a for a in partner_apps_db.values() if a["partner_id"] == partner_id]
    return ok(items)


@app.post("/api/v1/partners")
def create_partner(payload: PartnerCreate, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    partner_id = new_id()
    partner = {
        "id": partner_id,
        "name": payload.name,
        "description": payload.description,
        "logo_url": payload.logo_url,
        "website_url": payload.website_url,
        "status": payload.status,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    partners_db[partner_id] = partner
    record_audit(user["id"], "PARTNER_CREATED", "partner", partner_id, new_value=partner)
    return ok(partner, status_code=201)


@app.patch("/api/v1/partners/{partner_id}")
def update_partner(partner_id: str, payload: PartnerUpdate, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    partner = get_partner_or_404(partner_id)
    old_value = dict(partner)
    updates = payload.model_dump(exclude_unset=True)
    partner.update(updates)
    partner["updated_at"] = now_iso()
    record_audit(user["id"], "PARTNER_UPDATED", "partner", partner_id, old_value=old_value, new_value=partner)
    return ok(partner)


@app.delete("/api/v1/partners/{partner_id}")
def delete_partner(partner_id: str, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    partner = get_partner_or_404(partner_id)
    del partners_db[partner_id]
    record_audit(user["id"], "PARTNER_DELETED", "partner", partner_id, old_value=partner)
    return ok({"deleted": True})


# ==================================================
# PARTNER APPS
# ==================================================


@app.get("/api/v1/partner-apps")
def list_partner_apps(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    partnerId: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    items = list(partner_apps_db.values())
    if partnerId:
        items = [a for a in items if a["partner_id"] == partnerId]
    items = sorted(items, key=lambda a: a["created_at"])
    return ok(paginate(items, page, pageSize))


@app.get("/api/v1/partner-apps/{app_id}")
def get_partner_app(app_id: str, user: dict = Depends(get_current_user)):
    return ok(get_partner_app_or_404(app_id))


@app.post("/api/v1/partner-apps")
def create_partner_app(payload: PartnerAppCreate, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    get_partner_or_404(payload.partner_id)
    app_id = new_id()
    partner_app = {
        "id": app_id,
        "partner_id": payload.partner_id,
        "name": payload.name,
        "description": payload.description,
        "integration_type": payload.integration_type,
        "version": payload.version,
        "launch_url": payload.launch_url,
        "deep_link": payload.deep_link,
        "configuration": payload.configuration,
        "status": payload.status,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    partner_apps_db[app_id] = partner_app
    record_audit(user["id"], "PARTNER_APP_CREATED", "partner_app", app_id, new_value=partner_app)
    return ok(partner_app, status_code=201)


@app.patch("/api/v1/partner-apps/{app_id}")
def update_partner_app(app_id: str, payload: PartnerAppUpdate, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    partner_app = get_partner_app_or_404(app_id)
    old_value = dict(partner_app)
    updates = payload.model_dump(exclude_unset=True)
    partner_app.update(updates)
    integration_type = partner_app["integration_type"]
    if integration_type == IntegrationType.WEB and not partner_app.get("launch_url"):
        raise AppError("INVALID_PARTNER_APP", "launch_url is required for WEB integrations", 422)
    partner_app["updated_at"] = now_iso()
    record_audit(user["id"], "PARTNER_APP_UPDATED", "partner_app", app_id, old_value=old_value, new_value=partner_app)
    return ok(partner_app)


@app.delete("/api/v1/partner-apps/{app_id}")
def delete_partner_app(app_id: str, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    partner_app = get_partner_app_or_404(app_id)
    del partner_apps_db[app_id]
    record_audit(user["id"], "PARTNER_APP_DELETED", "partner_app", app_id, old_value=partner_app)
    return ok({"deleted": True})


# ==================================================
# CLIENTS
# ==================================================


@app.get("/api/v1/clients")
def list_clients(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    items = sorted(clients_db.values(), key=lambda c: c["created_at"])
    return ok(paginate(items, page, pageSize))


@app.get("/api/v1/clients/{client_id}")
def get_client(client_id: str, user: dict = Depends(get_current_user)):
    return ok(get_client_or_404(client_id))


@app.post("/api/v1/clients")
def create_client(payload: ClientCreate, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    if any(c["code"] == payload.code for c in clients_db.values()):
        raise AppError("INVALID_CLIENT", "Client code must be unique", 409)
    client_id = new_id()
    client = {
        "id": client_id,
        "name": payload.name,
        "code": payload.code,
        "description": payload.description,
        "status": payload.status,
        "api_key": secrets.token_urlsafe(24),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    clients_db[client_id] = client
    record_audit(user["id"], "CLIENT_CREATED", "client", client_id, new_value=client)
    return ok(client, status_code=201)


@app.patch("/api/v1/clients/{client_id}")
def update_client(client_id: str, payload: ClientUpdate, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    client = get_client_or_404(client_id)
    old_value = dict(client)
    updates = payload.model_dump(exclude_unset=True)
    client.update(updates)
    client["updated_at"] = now_iso()
    record_audit(user["id"], "CLIENT_UPDATED", "client", client_id, old_value=old_value, new_value=client)
    return ok(client)


@app.delete("/api/v1/clients/{client_id}")
def delete_client(client_id: str, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    client = get_client_or_404(client_id)
    del clients_db[client_id]
    record_audit(user["id"], "CLIENT_DELETED", "client", client_id, old_value=client)
    return ok({"deleted": True})


# ==================================================
# CLIENT INTEGRATIONS
# ==================================================


@app.get("/api/v1/clients/{client_id}/integrations")
def list_client_integrations(client_id: str, user: dict = Depends(get_current_user)):
    get_client_or_404(client_id)
    items = [i for i in client_integrations_db.values() if i["client_id"] == client_id]
    items = sorted(items, key=lambda i: i["display_order"])
    return ok(items)


@app.post("/api/v1/clients/{client_id}/integrations")
def create_client_integration(client_id: str, payload: ClientIntegrationCreate, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    get_client_or_404(client_id)
    partner = get_partner_or_404(payload.partner_id)
    partner_app = get_partner_app_or_404(payload.partner_app_id)
    if partner_app["partner_id"] != partner["id"]:
        raise AppError("INVALID_PARTNER_APP", "Partner app does not belong to the specified partner", 422)
    duplicate = any(
        i["client_id"] == client_id and i["partner_app_id"] == payload.partner_app_id
        for i in client_integrations_db.values()
    )
    if duplicate:
        raise AppError("DUPLICATE_INTEGRATION", "This client is already integrated with this partner app", 409)
    integration_id = new_id()
    integration = {
        "id": integration_id,
        "client_id": client_id,
        "partner_id": payload.partner_id,
        "partner_app_id": payload.partner_app_id,
        "enabled": payload.enabled,
        "display_name": payload.display_name or partner_app["name"],
        "display_order": payload.display_order,
        "configuration": payload.configuration,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    client_integrations_db[integration_id] = integration
    record_audit(user["id"], "INTEGRATION_CREATED", "client_integration", integration_id, new_value=integration)
    return ok(integration, status_code=201)


@app.patch("/api/v1/clients/{client_id}/integrations/{integration_id}")
def update_client_integration(client_id: str, integration_id: str, payload: ClientIntegrationUpdate, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    integration = get_integration_or_404(client_id, integration_id)
    old_value = dict(integration)
    updates = payload.model_dump(exclude_unset=True)
    integration.update(updates)
    integration["updated_at"] = now_iso()
    action = "INTEGRATION_UPDATED"
    if "enabled" in updates:
        action = "INTEGRATION_ENABLED" if updates["enabled"] else "INTEGRATION_DISABLED"
    record_audit(user["id"], action, "client_integration", integration_id, old_value=old_value, new_value=integration)
    return ok(integration)


@app.delete("/api/v1/clients/{client_id}/integrations/{integration_id}")
def delete_client_integration(client_id: str, integration_id: str, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    integration = get_integration_or_404(client_id, integration_id)
    del client_integrations_db[integration_id]
    record_audit(user["id"], "INTEGRATION_DELETED", "client_integration", integration_id, old_value=integration)
    return ok({"deleted": True})


# ==================================================
# DEPLOYMENTS
# ==================================================


def build_deployment_items(client_id: str, deployment_id: str) -> List[dict]:
    """Snapshot the client's current integrations into immutable deployment items."""
    items = []
    for integration in client_integrations_db.values():
        if integration["client_id"] != client_id:
            continue
        partner = partners_db.get(integration["partner_id"])
        partner_app = partner_apps_db.get(integration["partner_app_id"])
        item_id = new_id()
        item = {
            "id": item_id,
            "deployment_id": deployment_id,
            "client_integration_id": integration["id"],
            "partner_id": integration["partner_id"],
            "partner_app_id": integration["partner_app_id"],
            "partner_name": partner["name"] if partner else None,
            "app_name": partner_app["name"] if partner_app else None,
            "display_name": integration["display_name"],
            "logo_url": partner["logo_url"] if partner else None,
            "integration_type": partner_app["integration_type"] if partner_app else None,
            "launch_url": partner_app["launch_url"] if partner_app else None,
            "enabled": integration["enabled"],
            "display_order": integration["display_order"],
            "configuration": integration["configuration"],
        }
        deployment_items_db[item_id] = item
        items.append(item)
    return items


def deployment_with_items(deployment: dict) -> dict:
    items = [i for i in deployment_items_db.values() if i["deployment_id"] == deployment["id"]]
    items = sorted(items, key=lambda i: i["display_order"])
    return {**deployment, "items": items}


@app.post("/api/v1/clients/{client_id}/deployments")
def create_deployment(client_id: str, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    get_client_or_404(client_id)
    existing_versions = [d["version"] for d in deployments_db.values() if d["client_id"] == client_id]
    next_version = (max(existing_versions) + 1) if existing_versions else 1
    deployment_id = new_id()
    deployment = {
        "id": deployment_id,
        "client_id": client_id,
        "version": next_version,
        "status": DeploymentStatus.DRAFT,
        "created_by": user["id"],
        "created_at": now_iso(),
        "published_at": None,
    }
    deployments_db[deployment_id] = deployment
    build_deployment_items(client_id, deployment_id)
    record_audit(user["id"], "DEPLOYMENT_CREATED", "deployment", deployment_id, new_value=deployment)
    return ok(deployment_with_items(deployment), status_code=201)


@app.get("/api/v1/clients/{client_id}/deployments")
def list_deployments(
    client_id: str,
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    get_client_or_404(client_id)
    items = [d for d in deployments_db.values() if d["client_id"] == client_id]
    items = sorted(items, key=lambda d: d["version"], reverse=True)
    return ok(paginate(items, page, pageSize))


@app.get("/api/v1/deployments/{deployment_id}")
def get_deployment(deployment_id: str, user: dict = Depends(get_current_user)):
    deployment = get_deployment_or_404(deployment_id)
    return ok(deployment_with_items(deployment))


@app.post("/api/v1/deployments/{deployment_id}/publish")
def publish_deployment(deployment_id: str, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    deployment = get_deployment_or_404(deployment_id)
    if deployment["status"] == DeploymentStatus.PUBLISHED:
        raise AppError("DEPLOYMENT_ALREADY_PUBLISHED", "Deployment is already published", 409)
    old_value = dict(deployment)

    # Only one deployment may be the current published version per client.
    for other in deployments_db.values():
        if other["client_id"] == deployment["client_id"] and other["status"] == DeploymentStatus.PUBLISHED:
            other["status"] = DeploymentStatus.ROLLED_BACK

    deployment["status"] = DeploymentStatus.PUBLISHED
    deployment["published_at"] = now_iso()
    record_audit(user["id"], "DEPLOYMENT_PUBLISHED", "deployment", deployment_id, old_value=old_value, new_value=deployment)
    return ok(deployment_with_items(deployment))


@app.post("/api/v1/deployments/{deployment_id}/rollback")
def rollback_deployment(deployment_id: str, user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))):
    target = get_deployment_or_404(deployment_id)
    if target["status"] != DeploymentStatus.PUBLISHED:
        raise AppError("INVALID_DEPLOYMENT", "Only the currently published deployment can be rolled back", 422)

    client_id = target["client_id"]
    previous_candidates = [
        d for d in deployments_db.values()
        if d["client_id"] == client_id and d["version"] < target["version"]
    ]
    if not previous_candidates:
        raise AppError("INVALID_DEPLOYMENT", "No previous deployment available to roll back to", 422)
    source = max(previous_candidates, key=lambda d: d["version"])

    # Preserve the target deployment; create a new version copying the source's items.
    next_version = max(d["version"] for d in deployments_db.values() if d["client_id"] == client_id) + 1
    new_deployment_id = new_id()
    new_deployment = {
        "id": new_deployment_id,
        "client_id": client_id,
        "version": next_version,
        "status": DeploymentStatus.PUBLISHED,
        "created_by": user["id"],
        "created_at": now_iso(),
        "published_at": now_iso(),
    }
    deployments_db[new_deployment_id] = new_deployment

    for item in [i for i in deployment_items_db.values() if i["deployment_id"] == source["id"]]:
        new_item_id = new_id()
        deployment_items_db[new_item_id] = {**item, "id": new_item_id, "deployment_id": new_deployment_id}

    target["status"] = DeploymentStatus.ROLLED_BACK
    record_audit(user["id"], "DEPLOYMENT_ROLLED_BACK", "deployment", deployment_id, new_value=new_deployment)
    return ok(deployment_with_items(new_deployment), status_code=201)


# ==================================================
# MOBILE API
# ==================================================


@app.get("/api/v1/mobile/integrations")
def get_mobile_integrations(client: dict = Depends(get_current_client)):
    deployment = next(
        (d for d in deployments_db.values() if d["client_id"] == client["id"] and d["status"] == DeploymentStatus.PUBLISHED),
        None,
    )
    if not deployment:
        raise AppError("DEPLOYMENT_NOT_FOUND", "No published deployment for this client", 404)

    items = [i for i in deployment_items_db.values() if i["deployment_id"] == deployment["id"] and i["enabled"]]
    items = sorted(items, key=lambda i: i["display_order"])
    integrations = [
        {
            "id": i["client_integration_id"],
            "partnerId": i["partner_id"],
            "partnerAppId": i["partner_app_id"],
            "partnerName": i["partner_name"],
            "appName": i["app_name"],
            "displayName": i["display_name"],
            "logoUrl": i["logo_url"],
            "integrationType": i["integration_type"],
            "launchUrl": i["launch_url"],
            "enabled": i["enabled"],
            "displayOrder": i["display_order"],
        }
        for i in items
    ]
    return ok({
        "client": {"id": client["id"], "name": client["name"]},
        "deployment": {"version": deployment["version"]},
        "integrations": integrations,
    })


@app.get("/api/v1/mobile/third-party-tabs")
def get_third_party_tabs(client: dict = Depends(get_current_client)):
    """Static predefined external links (Swiggy, BigBasket, Domino's, etc.), same for every client."""
    tabs = [{"tab": name.value, **data} for name, data in THIRD_PARTY_TABS.items()]
    return ok({"tabs": tabs})


# ==================================================
# AUDIT LOGS (read-only, admin)
# ==================================================


@app.get("/api/v1/audit-logs")
def list_audit_logs(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    items = sorted(audit_logs_db.values(), key=lambda a: a["created_at"], reverse=True)
    return ok(paginate(items, page, pageSize))


@app.get("/api/v1/access-logs")
def list_access_logs(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
):
    """Who has been calling the API - every request, not just mutations."""
    items = list(reversed(access_log_db))
    return ok(paginate(items, page, pageSize))


# ==================================================
# SEED DATA (development only)
# ==================================================


def seed() -> None:
    admin_id = new_id()
    users_db[admin_id] = {
        "id": admin_id,
        "email": "admin@example.com",
        "password_hash": hash_password("Admin123!"),
        "role": UserRole.SUPER_ADMIN,
        "status": UserStatus.ACTIVE,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    viewer_id = new_id()
    users_db[viewer_id] = {
        "id": viewer_id,
        "email": "viewer@example.com",
        "password_hash": hash_password("Viewer123!"),
        "role": UserRole.VIEWER,
        "status": UserStatus.ACTIVE,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    demo_id = new_id()
    users_db[demo_id] = {
        "id": demo_id,
        "email": "demo@gamail.com",
        "password_hash": hash_password("123"),
        "role": UserRole.ADMIN,
        "status": UserStatus.ACTIVE,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }

    partner_names = ["ABC Travel", "ABC Food", "ABC Hotel"]
    partner_ids = {}
    for name in partner_names:
        pid = new_id()
        partner_ids[name] = pid
        partners_db[pid] = {
            "id": pid,
            "name": name,
            "description": f"{name} partner",
            "logo_url": f"https://example.com/{name.lower().replace(' ', '-')}.png",
            "website_url": "https://example.com",
            "status": PartnerStatus.ACTIVE,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }

    app_ids = {}
    for name in partner_names:
        aid = new_id()
        app_ids[name] = aid
        partner_apps_db[aid] = {
            "id": aid,
            "partner_id": partner_ids[name],
            "name": f"{name} Web",
            "description": f"{name} web integration",
            "integration_type": IntegrationType.WEB,
            "version": "1.0.0",
            "launch_url": f"https://{name.lower().replace(' ', '')}.example.com",
            "deep_link": None,
            "configuration": {},
            "status": PartnerAppStatus.ACTIVE,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }

    client_a_id = new_id()
    clients_db[client_a_id] = {
        "id": client_a_id,
        "name": "Client A",
        "code": "CLIENT_A",
        "description": "Seed client A",
        "status": ClientStatus.ACTIVE,
        "api_key": secrets.token_urlsafe(24),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    client_b_id = new_id()
    clients_db[client_b_id] = {
        "id": client_b_id,
        "name": "Client B",
        "code": "CLIENT_B",
        "description": "Seed client B",
        "status": ClientStatus.ACTIVE,
        "api_key": secrets.token_urlsafe(24),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }

    for order, name in enumerate(partner_names, start=1):
        integration_id = new_id()
        client_integrations_db[integration_id] = {
            "id": integration_id,
            "client_id": client_a_id,
            "partner_id": partner_ids[name],
            "partner_app_id": app_ids[name],
            "enabled": True,
            "display_name": name,
            "display_order": order,
            "configuration": {"theme": {"primaryColor": "#123456"}},
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }

    deployment_id = new_id()
    deployments_db[deployment_id] = {
        "id": deployment_id,
        "client_id": client_a_id,
        "version": 1,
        "status": DeploymentStatus.PUBLISHED,
        "created_by": admin_id,
        "created_at": now_iso(),
        "published_at": now_iso(),
    }
    build_deployment_items(client_a_id, deployment_id)

    print("Seed data loaded. Client A API key:", clients_db[client_a_id]["api_key"])


seed()
