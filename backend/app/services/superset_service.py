import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.core.exceptions import SupersetIntegrationError
from app.models.dashboard import Dashboard
from app.models.user import User
from app.schemas.superset import SupersetGuestTokenResponse

logger = logging.getLogger(__name__)

KNOWN_INSECURE_OR_PLACEHOLDER_PASSWORDS = {
    "admin_password_placeholder",
    "placeholder",
    "password",
    "admin",
    "changeme",
    "your-superset-password",
}


class SupersetService:
    """Backend service for Apache Superset integration.
    
    Handles secure backend-to-Superset authentication and guest token issuance
    for embedded dashboards. Credentials never leave the backend.
    """

    _cached_admin_token: Optional[str] = None
    _token_fetched_at: Optional[datetime] = None

    def __init__(
        self,
        base_url: Optional[str] = None,
        admin_username: Optional[str] = None,
        admin_password: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.SUPERSET_BASE_URL or "").rstrip("/")
        self.admin_username = (
            admin_username if admin_username is not None else settings.SUPERSET_ADMIN_USERNAME
        )
        self.admin_password = (
            admin_password if admin_password is not None else settings.SUPERSET_ADMIN_PASSWORD
        )

    def is_configured(self) -> bool:
        """Check whether Superset has been configured with real, non-placeholder credentials."""
        if not self.base_url or not self.admin_username or not self.admin_password:
            return False

        pwd = self.admin_password.strip().lower()
        if pwd in KNOWN_INSECURE_OR_PLACEHOLDER_PASSWORDS or "placeholder" in pwd:
            return False

        if not self.admin_username.strip():
            return False

        return True

    async def get_admin_token(self, force_refresh: bool = False) -> str:
        """Authenticate with Apache Superset using service credentials and return access token."""
        if not self.is_configured():
            raise SupersetIntegrationError(
                "Apache Superset integration is not configured. "
                "Valid service credentials (SUPERSET_ADMIN_USERNAME, SUPERSET_ADMIN_PASSWORD) must be provided in the environment."
            )

        now = datetime.now(timezone.utc)

        # Return cached token if valid (less than 45 minutes old)
        if (
            not force_refresh
            and self._cached_admin_token
            and self._token_fetched_at
            and (now - self._token_fetched_at).total_seconds() < 2700
        ):
            return self._cached_admin_token

        login_url = f"{self.base_url}/api/v1/security/login"
        payload = {
            "username": self.admin_username,
            "password": self.admin_password,
            "provider": "db",
            "refresh": True,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(login_url, json=payload)
                if response.status_code == 401:
                    logger.error("Superset authentication failed: Invalid admin credentials")
                    raise SupersetIntegrationError(
                        "Superset authentication failed: Invalid service credentials configured in backend."
                    )
                response.raise_for_status()
                data = response.json()
                token = data.get("access_token")
                if not token:
                    raise SupersetIntegrationError(
                        "Superset did not return an access token."
                    )

                SupersetService._cached_admin_token = token
                SupersetService._token_fetched_at = now
                return token

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Superset at {self.base_url}: {e}")
            raise SupersetIntegrationError(
                f"Cannot connect to Apache Superset at {self.base_url}. Verify that Superset is running and network is accessible."
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"Superset HTTP error: {e.response.status_code} - {e.response.text}")
            raise SupersetIntegrationError(
                f"Superset API returned error {e.response.status_code}: {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"Superset connection error: {e}")
            raise SupersetIntegrationError(
                f"Failed to communicate with Superset service: {str(e)}"
            )

    async def _fetch_csrf_token(self, client: httpx.AsyncClient, admin_token: str) -> str:
        """Fetch a CSRF token from Superset using an authenticated session.

        The same ``httpx.AsyncClient`` instance must be reused for the subsequent
        guest-token POST so that Superset's session cookie (set during the CSRF
        request) is sent along with the CSRF header — both are required for
        Superset's double-submit CSRF validation.

        Returns the raw CSRF token string.
        Raises :class:`SupersetIntegrationError` on any failure.
        """
        csrf_url = f"{self.base_url}/api/v1/security/csrf_token/"
        try:
            csrf_response = await client.get(
                csrf_url,
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            csrf_response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to obtain Superset CSRF token: HTTP %s", e.response.status_code
            )
            raise SupersetIntegrationError(
                f"Failed to obtain Superset CSRF token ({e.response.status_code})."
            ) from e
        except httpx.RequestError as e:
            logger.error("Network error fetching Superset CSRF token: %s", e)
            raise SupersetIntegrationError(
                f"Network error while fetching Superset CSRF token: {e}"
            ) from e

        csrf_token: Optional[str] = csrf_response.json().get("result")
        if not csrf_token:
            raise SupersetIntegrationError(
                "Superset CSRF token response did not contain a 'result' field."
            )
        return csrf_token

    async def generate_guest_token(
        self, user: User, dashboard: Dashboard
    ) -> SupersetGuestTokenResponse:
        """Generate a secure guest token for an authorized user to embed a dashboard.

        Flow (all within a **single** ``httpx.AsyncClient`` session so that the
        Superset session cookie obtained during the CSRF request is automatically
        included in the subsequent guest-token POST):

        1. Obtain a Superset admin access token (cached up to 45 min).
        2. GET ``/api/v1/security/csrf_token/`` → extract CSRF token from ``result``.
        3. POST ``/api/v1/security/guest_token/`` with ``Authorization: Bearer``
           **and** ``X-CSRFToken`` headers.
        4. If the POST returns 401 (access token expired), refresh the admin token,
           fetch a new CSRF token (still in the same client session), and retry once.

        RLS rules are intentionally left uninvented until verified dataset fields
        and branch mappings are provided.
        """
        admin_token = await self.get_admin_token()

        # Parse user names for Superset guest context
        name_parts = user.full_name.split() if user.full_name else ["Portal", "User"]
        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "User"

        # Construct guest token payload
        resources = [
            {
                "type": "dashboard",
                "id": str(dashboard.superset_dashboard_id),
            }
        ]

        # RLS architecture placeholder:
        # Kept ready for verified branch mappings without inventing synthetic rules
        rls_rules: List[Dict[str, Any]] = []
        if dashboard.requires_branch_scope and user.assigned_branch_id:
            # Future verified hook:
            # rls_rules.append({"clause": f"branch_id = '{user.assigned_branch_id}'"})
            pass

        guest_payload = {
            "user": {
                "username": user.email,
                "first_name": first_name,
                "last_name": last_name,
            },
            "resources": resources,
            "rls": rls_rules,
        }

        guest_token_url = f"{self.base_url}/api/v1/security/guest_token/"

        try:
            # A single client session is required: the CSRF GET sets a Superset
            # session cookie that must accompany the X-CSRFToken header in the POST.
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Step 1: fetch CSRF token
                csrf_token = await self._fetch_csrf_token(client, admin_token)

                headers = {
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrf_token,
                }

                response = await client.post(
                    guest_token_url, json=guest_payload, headers=headers
                )

                # If access token expired on Superset side, refresh once.
                # A fresh CSRF token is also required after re-authentication.
                if response.status_code == 401:
                    admin_token = await self.get_admin_token(force_refresh=True)
                    csrf_token = await self._fetch_csrf_token(client, admin_token)
                    headers["Authorization"] = f"Bearer {admin_token}"
                    headers["X-CSRFToken"] = csrf_token
                    response = await client.post(
                        guest_token_url, json=guest_payload, headers=headers
                    )

                response.raise_for_status()
                data = response.json()
                token = data.get("token")
                if not token:
                    raise SupersetIntegrationError(
                        "Superset guest token response missing 'token' attribute."
                    )

                return SupersetGuestTokenResponse(
                    token=token,
                    superset_dashboard_id=str(dashboard.superset_dashboard_id),
                    superset_domain=self.base_url,
                    expires_in=settings.SUPERSET_GUEST_TOKEN_TIMEOUT_SECS,
                    dashboard_title=dashboard.title,
                    requires_branch_scope=dashboard.requires_branch_scope,
                )

        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to generate guest token: %s - %s",
                e.response.status_code,
                e.response.text,
            )
            raise SupersetIntegrationError(
                f"Superset failed to issue guest token ({e.response.status_code}): {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error("Error calling Superset guest token API: %s", e)
            raise SupersetIntegrationError(
                f"Network error while requesting Superset guest token: {str(e)}"
            )

    async def check_health(self) -> Dict[str, Any]:
        """Check Superset service reachability and status."""
        configured = self.is_configured()
        if not configured:
            return {
                "configured": False,
                "superset_url": self.base_url,
                "connected": False,
                "status_detail": "Unconfigured: SUPERSET_ADMIN_USERNAME and SUPERSET_ADMIN_PASSWORD must be configured with valid service credentials.",
            }

        health_url = f"{self.base_url}/health"

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(health_url)
                connected = res.status_code in (200, 204)
                status_detail = "Superset service reachable" if connected else f"HTTP {res.status_code}"
        except Exception as e:
            connected = False
            status_detail = f"Unreachable: {str(e)}"

        return {
            "configured": configured,
            "superset_url": self.base_url,
            "connected": connected,
            "status_detail": status_detail,
        }
