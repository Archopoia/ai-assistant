from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import pyotp
import qrcode
import io
import base64
from ..database import get_db
from ..api import get_current_user
from ..schemas.user import (
    UserCreate,
    UserResponse,
    Token,
    RefreshTokenRequest,
    LoginRequest,
    RequestPasswordResetRequest,
    ResetPasswordRequest,
    TwoFactorVerifyRequest,
    TwoFactorDisableRequest,
    TwoFactorVerifyLoginRequest,
)
from ..models.user import User
from ..services.auth_service import auth_service
from ..utils.oauth import oauth
from ..config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    try:
        user, verification_token = auth_service.create_user(db, user_data.email, user_data.password)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login")
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Login and get access token. Returns 2FA required response if 2FA is enabled."""
    user = auth_service.authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in"
        )
    
    # Check if 2FA is enabled
    if user.two_factor_enabled:
        return {
            "requires_2fa": True,
            "email": credentials.email,
            "message": "2FA verification required"
        }
    
    tokens = auth_service.create_tokens(user)
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token."""
    payload = auth_service.get_user_from_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user = db.query(User).filter(User.email == payload["email"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    tokens = auth_service.create_tokens(user)
    return tokens


@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify email with token."""
    success = auth_service.verify_email(db, token)
    if success:
        return {"message": "Email verified successfully"}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")


@router.post("/request-password-reset")
async def request_password_reset(payload: RequestPasswordResetRequest, db: Session = Depends(get_db)):
    """Request password reset."""
    token = auth_service.request_password_reset(db, payload.email)
    if token:
        return {"message": "Password reset email sent"}
    return {"message": "If email exists, password reset email sent"}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password with token."""
    try:
        success = auth_service.reset_password(db, payload.token, payload.new_password)
        if success:
            return {"message": "Password reset successfully"}
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/oauth/{provider}/login")
async def oauth_login(provider: str, request: Request):
    """Initiate OAuth login. Requires OAuth credentials in .env (GOOGLE_CLIENT_ID/GITHUB_CLIENT_ID and secrets)."""
    if provider not in ["google", "github"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid provider. Supported: google, github")
    
    if provider not in oauth._clients:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail=f"OAuth for {provider} is not configured. To enable OAuth (required feature), set {provider.upper()}_CLIENT_ID and {provider.upper()}_CLIENT_SECRET in your .env file. See README for setup instructions."
        )
    
    redirect_uri = f"{settings.APP_URL}/auth/oauth/{provider}/callback"
    return await oauth._clients[provider].authorize_redirect(request, redirect_uri)


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    """Handle OAuth callback. OAuth is optional - configure credentials in .env to enable."""
    if provider not in ["google", "github"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid provider. Supported: google, github")
    
    if provider not in oauth._clients:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail=f"OAuth for {provider} is not configured. To enable, set {provider.upper()}_CLIENT_ID and {provider.upper()}_CLIENT_SECRET in your .env file."
        )
    
    try:
        token = await oauth._clients[provider].authorize_access_token(request)
        user = await auth_service.oauth_callback(provider, token, db)
        
        if user:
            tokens = auth_service.create_tokens(user)
            # Redirect to frontend with tokens
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/auth/callback?access_token={tokens['access_token']}&refresh_token={tokens['refresh_token']}"
            )
        
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth authentication failed")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/2fa/enable")
async def enable_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable 2FA and return QR code for setup."""
    if current_user.two_factor_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is already enabled")
    
    # Generate secret
    secret = pyotp.random_base32()
    current_user.two_factor_secret = secret
    db.commit()
    
    # Generate QR code
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name="Wellness Platform"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    qr_code_base64 = base64.b64encode(buffer.read()).decode()
    
    return {
        "secret": secret,
        "qr_code": f"data:image/png;base64,{qr_code_base64}",
        "message": "Scan QR code with authenticator app and verify with a code to enable 2FA"
    }


@router.post("/2fa/verify")
async def verify_2fa(
    payload: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify 2FA code and enable 2FA."""
    if not current_user.two_factor_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not set up. Please enable it first.")
    
    if current_user.two_factor_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is already enabled")
    
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")
    
    current_user.two_factor_enabled = True
    db.commit()
    
    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
async def disable_2fa(
    payload: Optional[TwoFactorDisableRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable 2FA."""
    if not current_user.two_factor_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is not enabled")
    
    # Verify code if provided
    code = payload.code if payload else None
    if code and current_user.two_factor_secret:
        totp = pyotp.TOTP(current_user.two_factor_secret)
        if not totp.verify(code, valid_window=1):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification code")
    
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    db.commit()
    
    return {"message": "2FA disabled successfully"}


@router.post("/2fa/verify-login")
async def verify_2fa_login(
    payload: TwoFactorVerifyLoginRequest,
    db: Session = Depends(get_db)
):
    """Verify 2FA code during login."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.two_factor_enabled or not user.two_factor_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not enabled for this user")
    
    totp = pyotp.TOTP(user.two_factor_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA code")
    
    tokens = auth_service.create_tokens(user)
    return tokens
