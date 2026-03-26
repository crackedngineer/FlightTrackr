from core.settings import get_settings

settings = get_settings()

class GoogleOAuthService:

    def generate_auth_url(self, user_id):
        return (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={settings.gooogle_client_id}"
            "&response_type=code"
            f"&redirect_uri={settings.google_redirect_uri}"
            "&scope=https://www.googleapis.com/auth/gmail.readonly"
            "&access_type=offline"
            "&prompt=consent"
            f"&state={user_id}"
        )