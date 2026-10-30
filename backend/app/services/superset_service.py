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


class SupersetService:
    """Backend service for Apache Superset integration.
    
    Handles secure backend-to-Superset authentication and guest token issuance
    for embedded dashboards. Credentials never leave the backend.
    """

    _cached_admin_token: Optional[str] = None
    _token_fetched_at: Optional[datetime] = None

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.SUPERSET_BASE_URL).rstrip("/")
        self.admin_username = settings.SUPERSET_ADMIN_USERNAME
        self.admin_password = settings.SUPERSET_ADMIN_PASSWORD

    def is_configured(self) -> bool:
        """Check whether Superset has been configured with real non-placeholder credentials."""
        if not self.base_url or not self.admin_username:
            return False
        if "placeholder" in self.admin_password.lower():
            return False
        return True

    async def get_admin_token(self, force_refresh: bool = False) -> str:
        """Authenticate with Apache Superset using service credentials and return access token."""
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

    async def generate_guest_token(
        self, user: User, dashboard: Dashboard
    ) -> SupersetGuestTokenResponse:
        """Generate a secure guest token for an authorized user to embed a dashboard.
        
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
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    guest_token_url, json=guest_payload, headers=headers
                )

                # If token expired on Superset side, retry once with refreshed token
                if response.status_code == 401:
                    admin_token = await self.get_admin_token(force_refresh=True)
                    headers["Authorization"] = f"Bearer {admin_token}"
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
                f"Failed to generate guest token: {e.response.status_code} - {e.response.text}"
            )
            raise SupersetIntegrationError(
                f"Superset failed to issue guest token ({e.response.status_code}): {e.response.text}"
            )
        except httpx.RequestError as e:
            logger.error(f"Error calling Superset guest token API: {e}")
            raise SupersetIntegrationError(
                f"Network error while requesting Superset guest token: {str(e)}"
            )

    async def check_health(self) -> Dict[str, Any]:
        """Check Superset service reachability and status."""
        configured = self.is_configured()
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
