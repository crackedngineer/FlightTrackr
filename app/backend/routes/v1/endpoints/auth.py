from fastapi import APIRouter
from services.google_oauth import GoogleOAuthService
# from app.core.dependencies import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["core"],
)

router = APIRouter()

@router.get("/gmail/connect")
# def connect_gmail(user=Depends(get_current_user)):
def connect_gmail():
    url = GoogleOAuthService().generate_auth_url("user.id")
    return {"url": url}