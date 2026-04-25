import os


SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]
SQLALCHEMY_EXAMPLES = False
ENABLE_PROXY_FIX = True
PREFERRED_URL_SCHEME = "https" if os.environ.get("TAILSCALE_BASE_URL") else "http"
TAILSCALE_BASE_URL = os.environ.get("TAILSCALE_BASE_URL")
