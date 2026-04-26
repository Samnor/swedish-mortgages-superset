import os


SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]
if os.environ.get("SUPERSET_DATABASE_URI"):
    SQLALCHEMY_DATABASE_URI = os.environ["SUPERSET_DATABASE_URI"]
SQLALCHEMY_EXAMPLES = False
ENABLE_PROXY_FIX = True
PREFERRED_URL_SCHEME = "https" if os.environ.get("TAILSCALE_BASE_URL") else "http"
TAILSCALE_BASE_URL = os.environ.get("TAILSCALE_BASE_URL")

# Give anonymous users the same base UI read permissions as Gamma. Dataset access
# is still granted explicitly by scripts/grant_public_dashboard_access.py.
PUBLIC_ROLE_LIKE = "Gamma"
