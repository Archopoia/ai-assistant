from authlib.integrations.starlette_client import OAuth
from ..config import settings

oauth = OAuth()

def _is_real_oauth_value(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.strip().lower()
    placeholder_markers = ("your-", "replace-", "example", "changeme", "placeholder")
    return not any(marker in normalized for marker in placeholder_markers)


if _is_real_oauth_value(settings.GOOGLE_CLIENT_ID) and _is_real_oauth_value(settings.GOOGLE_CLIENT_SECRET):
    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

if _is_real_oauth_value(settings.GITHUB_CLIENT_ID) and _is_real_oauth_value(settings.GITHUB_CLIENT_SECRET):
    oauth.register(
        name='github',
        client_id=settings.GITHUB_CLIENT_ID,
        client_secret=settings.GITHUB_CLIENT_SECRET,
        authorize_url='https://github.com/login/oauth/authorize',
        access_token_url='https://github.com/login/oauth/access_token',
        client_kwargs={'scope': 'user:email'}
    )
