from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session


from app.auth.schemas import ForgotPasswordRequest, LoginRequest, LogoutRequest, RefreshTokenRequest, RegisterRequest, ResetPasswordRequest, TokenResponse, UserResponse, ChangePasswordRequest
from app.auth.service import AuthService
from app.database.session import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.auth.dependencies import require_admin

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):

    service = AuthService(db)

    user = service.register(
        full_name=request.full_name,
        email=request.email,
        password=request.password,
    )

    return UserResponse.model_validate(user)

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):

    service = AuthService(db)

    return service.login(
        email=request.email,
        password=request.password,
    )

@router.get(
    "/me",
    response_model=UserResponse,
)
def me(
    current_user: User = Depends(get_current_user),
):
    return UserResponse.model_validate(current_user)

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    service = AuthService(db)

    return service.refresh(
        refresh_token=request.refresh_token
    )
@router.post("/logout")
def logout(
    request: LogoutRequest,
    db: Session = Depends(get_db),
):
    AuthService(db).logout(refresh_token=request.refresh_token)

    return {"message": "Logged out successfully"}

@router.get(
    "/admin-test",
    response_model=UserResponse,
)
def admin_test(
    current_user: User = Depends(require_admin),
):
    return UserResponse.model_validate(current_user)

@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AuthService(db)

    service.change_password(
        user=current_user,
        current_password=request.current_password,
        new_password=request.new_password,
    )

@router.post("/logout-all")
def logout_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    AuthService(db).logout_all(user=current_user)

    return {"message": "Logged out from all devices"}

@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    AuthService(db).forgot_password(email=request.email)

    return {"message": "If account exists, reset link sent"}


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    AuthService(db).reset_password(
        token=request.token,
        new_password=request.new_password,
    )

    return {"message": "Password reset successful"}