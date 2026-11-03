from typing import Annotated

from fastapi import Depends, Request

from costpilot.modules.identity.application.account_service import AccountService
from costpilot.modules.identity.application.auth_service import AuthService
from costpilot.modules.identity.domain.models import CurrentUser
from costpilot.shared.config import Settings


def get_auth(request: Request) -> AuthService:
    return request.app.state.auth


def get_account(request: Request) -> AccountService:
    return request.app.state.account


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


Auth = Annotated[AuthService, Depends(get_auth)]
Account = Annotated[AccountService, Depends(get_account)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]


async def get_current_user(request: Request, auth: Auth, settings: AppSettings) -> CurrentUser:
    return await auth.current_user(request.cookies.get(settings.session_cookie_name))


SignedInUser = Annotated[CurrentUser, Depends(get_current_user)]
