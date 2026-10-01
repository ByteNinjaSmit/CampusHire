from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.db import DB
from app.core.deps import Client, CurrentUser
from app.core.errors import AppError, app_error_response, forbidden
from app.core.ratelimit import check_rate_limit, register_rate_limit
from app.modules.auth import schemas as s
from app.modules.auth import service
from app.modules.users import schemas as user_schemas
from app.modules.users.service import build_me

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "ch_refresh"
ROLE_COOKIE = "ch_role"
CSRF_HEADER = "x-requested-with"
CSRF_VALUE = "campushire"


# ---- cookies / CSRF ---------------------------------------------------------------------------------------
def set_auth_cookies(response: Response, raw_refresh: str, role: str) -> None:
    max_age = settings.REFRESH_TTL_DAYS * 86400
    response.set_cookie(
        REFRESH_COOKIE,
        raw_refresh,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/api/v1/auth",
    )
    # Not HttpOnly: only used by the frontend proxy for routing; authorisation is always enforced by the API.
    response.set_cookie(
        ROLE_COOKIE, role, max_age=max_age, httponly=False, samesite="lax", secure=settings.COOKIE_SECURE, path="/"
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth", httponly=True, samesite="lax", secure=settings.COOKIE_SECURE)
    response.delete_cookie(ROLE_COOKIE, path="/", samesite="lax", secure=settings.COOKIE_SECURE)


async def csrf_guard(request: Request) -> None:
    """Cookie-authenticated endpoints need ``X-Requested-With: campushire`` and an allowed Origin (if sent)."""
    if request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        raise forbidden("Missing or invalid X-Requested-With header", "FORBIDDEN")
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origins_list:
        raise forbidden("Origin not allowed", "FORBIDDEN")


CsrfGuard = Depends(csrf_guard)


# ---- registration -----------------------------------------------------------------------------------------
@router.post(
    "/register/student",
    response_model=s.MessageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_rate_limit)],
)
async def register_student(db: DB, body: s.StudentRegisterRequest):
    await service.register_student(db, body)
    return s.MessageResponse(message="Registration successful. Check your email to verify your account.")


@router.post(
    "/register/company",
    response_model=s.MessageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_rate_limit)],
)
async def register_company(db: DB, body: s.CompanyRegisterRequest):
    await service.register_company(db, body)
    return s.MessageResponse(
        message="Registration successful. Verify your email; an administrator must approve your company before you can post."
    )


# ---- session ----------------------------------------------------------------------------------------------
@router.post("/login", response_model=s.TokenResponse)
async def login(db: DB, body: s.LoginRequest, response: Response, client: Client):
    await check_rate_limit(f"login:{client.ip}:{body.email}", 5, 60)
    result = await service.login(db, body, client)
    set_auth_cookies(response, result.refresh_token, result.role)
    return result.token


@router.post("/refresh", response_model=s.TokenResponse, dependencies=[CsrfGuard])
async def refresh(db: DB, request: Request, client: Client):
    raw = request.cookies.get(REFRESH_COOKIE)
    try:
        result = await service.refresh(db, raw, client)
    except AppError as exc:
        err = app_error_response(request, exc)
        clear_auth_cookies(err)
        return err
    resp = JSONResponse(result.token.model_dump(mode="json"))
    set_auth_cookies(resp, result.refresh_token, result.role)
    return resp


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[CsrfGuard])
async def logout(db: DB, request: Request):
    await service.logout(db, request.cookies.get(REFRESH_COOKIE))
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_auth_cookies(resp)
    return resp


# ---- email verification / password reset ----------------------------------------------------------------------
@router.post("/verify-email", response_model=s.MessageResponse)
async def verify_email(db: DB, body: s.VerifyEmailRequest):
    return s.MessageResponse(message=await service.verify_email(db, body.token))


@router.post("/resend-verification", response_model=s.MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def resend_verification(db: DB, body: s.EmailRequest):
    await check_rate_limit(f"resend:{body.email}", 3, 3600)
    await service.resend_verification(db, body.email)
    return s.MessageResponse(message="If the account exists and is unverified, a verification email has been sent.")


@router.post("/forgot-password", response_model=s.MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(db: DB, body: s.EmailRequest):
    await check_rate_limit(f"forgot:{body.email}", 3, 3600)
    await service.forgot_password(db, body.email)
    return s.MessageResponse(message="If the account exists, a password reset email has been sent.")


@router.post("/reset-password", response_model=s.MessageResponse)
async def reset_password(db: DB, body: s.ResetPasswordRequest):
    await service.reset_password(db, body.token, body.new_password)
    return s.MessageResponse(message="Password updated. Please sign in with your new password.")


# ---- current user -----------------------------------------------------------------------------------------------
@router.get("/me", response_model=user_schemas.Me)
async def me(db: DB, user: CurrentUser):
    return await build_me(db, user)


@router.post("/change-password", response_model=s.MessageResponse)
async def change_password(db: DB, user: CurrentUser, body: s.ChangePasswordRequest, request: Request):
    await service.change_password(db, user, body, request.cookies.get(REFRESH_COOKIE))
    return s.MessageResponse(message="Password changed.")

