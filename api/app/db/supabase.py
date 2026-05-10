from supabase import create_client, Client
from supabase.lib.client_options import SyncClientOptions
from app.core.settings import get_settings


def get_supabase_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError("Supabase URL and/or Key are not set")
    # implicit: Supabase delivers tokens in the URL hash — no PKCE flow-state
    # cookie required, which breaks when the exchange runs server-side.
    return create_client(
        settings.supabase_url,
        settings.supabase_key,
        options=SyncClientOptions(flow_type="implicit"),
    )