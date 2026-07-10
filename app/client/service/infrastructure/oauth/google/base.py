from authlib.integrations.starlette_client import OAuth
from app.core.config.base import get_settings
from app.core.config.client.oauth.google_client_kwargs import GOOGLE_CLIENT_KWARGS_CONF

settings = get_settings()
oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.oauth_google.client_id,
    client_secret=settings.oauth_google.client_secret,
    server_metadata_url=settings.oauth_google.server_metadata,
    client_kwargs=GOOGLE_CLIENT_KWARGS_CONF,
)