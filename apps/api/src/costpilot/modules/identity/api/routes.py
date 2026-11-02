from uuid import UUID

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from costpilot.modules.identity.api.dependencies import AppSettings, Auth, SignedInUser

router = APIRouter()


class MeResponse(BaseModel):
    user_id: UUID
    email: str
    display_name: str
    workspace_id: UUID
    workspace_name: str
    role: str
    account_url: str
    max_upload_mb: int


class LogoutResponse(BaseModel):
    logout_url: str


@router.get("/auth/login")
def login(auth: Auth, settings: AppSettings) -> RedirectResponse:
    url, sealed_challenge = auth.begin_login()
    response = RedirectResponse(url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        settings.login_cookie_name,
        sealed_challenge,
        max_age=settings.login_lifetime_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )
    return response


@router.get("/auth/callback")
async def callback(
    request: Request,
    auth: Auth,
    settings: AppSettings,
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    if code is None or state is None:
        # Keycloak sends no code if the user cancels, so start again from the app.
        return RedirectResponse(settings.app_public_url, status_code=status.HTTP_302_FOUND)
    session_token, _ = await auth.complete_login(
        code, state, request.cookies.get(settings.login_cookie_name)
    )
    response = RedirectResponse(settings.app_public_url, status_code=status.HTTP_302_FOUND)
    response.delete_cookie(settings.login_cookie_name)
    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        max_age=settings.session_lifetime_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )
    return response


@router.post("/auth/logout")
async def logout(
    request: Request, response: Response, auth: Auth, settings: AppSettings
) -> LogoutResponse:
    logout_url = await auth.logout(request.cookies.get(settings.session_cookie_name))
    response.delete_cookie(settings.session_cookie_name)
    return LogoutResponse(logout_url=logout_url)


@router.get("/me")
def me(user: SignedInUser, auth: Auth, settings: AppSettings) -> MeResponse:
    return MeResponse(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        workspace_id=user.workspace_id,
        workspace_name=user.workspace_name,
        role=user.role,
        account_url=auth.account_url(),
        max_upload_mb=settings.max_upload_mb,
    )
