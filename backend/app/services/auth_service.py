import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..models.user import User
from ..utils.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from ..utils.validators import validate_email, validate_password
from ..utils.oauth import oauth
from ..services.email_service import email_service
from ..config import settings

logger = logging.getLogger(__name__)


class AuthService:
    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash token before storing in DB."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def create_user(db: Session, email: str, password: str) -> tuple[User, str]:
        """Create a new user and return user with verification token."""
        # Validate email
        if not validate_email(email):
            raise ValueError("Invalid email format")
        
        # Validate password
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            raise ValueError(error_msg or "Invalid password")
        
        # Check if user exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError("Email already registered")
        
        # Create user
        password_hash = get_password_hash(password)
        verification_token = secrets.token_urlsafe(32)
        verification_token_hash = AuthService._hash_token(verification_token)
        verification_expires_at = datetime.utcnow() + timedelta(hours=24)
        
        user = User(
            email=email,
            password_hash=password_hash,
            email_verified=False,
            email_verification_token_hash=verification_token_hash,
            email_verification_expires_at=verification_expires_at
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Send verification email (async, don't wait)
        # In production, use background task
        import asyncio
        try:
            asyncio.create_task(email_service.send_verification_email(email, verification_token))
        except RuntimeError as exc:
            logger.warning("Unable to schedule verification email task: %s", exc)
        
        return user, verification_token
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        
        if not user.password_hash:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        return user
    
    @staticmethod
    def create_tokens(user: User) -> dict:
        """Create access and refresh tokens for user."""
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(data={"sub": user.email, "user_id": user.id})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    @staticmethod
    def verify_email(db: Session, token: str) -> bool:
        """Verify user email with token."""
        token_hash = AuthService._hash_token(token)
        now = datetime.utcnow()
        user = db.query(User).filter(
            User.email_verification_token_hash == token_hash,
            User.email_verification_expires_at.isnot(None),
            User.email_verification_expires_at > now
        ).first()
        if user and not user.email_verified:
            user.email_verified = True
            # One-time token semantics
            user.email_verification_token_hash = None
            user.email_verification_expires_at = None
            db.commit()
            return True
        return False
    
    @staticmethod
    def request_password_reset(db: Session, email: str) -> Optional[str]:
        """Request password reset and return reset token."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        
        reset_token = secrets.token_urlsafe(32)
        reset_token_hash = AuthService._hash_token(reset_token)
        user.password_reset_token_hash = reset_token_hash
        user.password_reset_expires_at = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        
        import asyncio
        try:
            asyncio.create_task(email_service.send_password_reset_email(email, reset_token))
        except RuntimeError as exc:
            logger.warning("Unable to schedule password reset email task: %s", exc)
        
        return reset_token
    
    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> bool:
        """Reset password with token."""
        # Validate password
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            raise ValueError(error_msg or "Invalid password")
        
        token_hash = AuthService._hash_token(token)
        now = datetime.utcnow()
        user = db.query(User).filter(
            User.password_reset_token_hash == token_hash,
            User.password_reset_expires_at.isnot(None),
            User.password_reset_expires_at > now
        ).first()
        if user:
            user.password_hash = get_password_hash(new_password)
            # One-time token semantics
            user.password_reset_token_hash = None
            user.password_reset_expires_at = None
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_user_from_token(token: str) -> Optional[dict]:
        """Get user data from JWT token."""
        payload = decode_token(token)
        if payload:
            return {"email": payload.get("sub"), "user_id": payload.get("user_id")}
        return None
    
    @staticmethod
    async def oauth_callback(provider: str, token: dict, db: Session) -> Optional[User]:
        """Handle OAuth callback and create/update user."""
        if provider == "google":
            user_info = token.get("userinfo", {})
            email = user_info.get("email")
            oauth_id = user_info.get("sub")
            
            if not email:
                return None
            
            # Check if user exists by email or OAuth ID
            user = db.query(User).filter(
                or_(User.email == email, User.oauth_google_id == oauth_id)
            ).first()
            
            if user:
                # Update OAuth ID if not set
                if not user.oauth_google_id:
                    user.oauth_google_id = oauth_id
                user.email_verified = True
                db.commit()
                db.refresh(user)
                return user
            else:
                # Create new user
                user = User(
                    email=email,
                    oauth_google_id=oauth_id,
                    email_verified=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                return user
        
        elif provider == "github":
            # GitHub OAuth response structure
            access_token = token.get("access_token")
            if not access_token:
                return None
            
            # Fetch user info from GitHub API
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"token {access_token}"}
                )
                if response.status_code == 200:
                    user_info = response.json()
                    email = user_info.get("email")
                    oauth_id = str(user_info.get("id"))
                    
                    if not email:
                        # GitHub might not return email, try email endpoint
                        email_response = await client.get(
                            "https://api.github.com/user/emails",
                            headers={"Authorization": f"token {access_token}"}
                        )
                        if email_response.status_code == 200:
                            emails = email_response.json()
                            email = next((e["email"] for e in emails if e.get("primary")), None)
                    
                    if not email:
                        return None
                    
                    # Check if user exists
                    user = db.query(User).filter(
                        or_(User.email == email, User.oauth_github_id == oauth_id)
                    ).first()
                    
                    if user:
                        if not user.oauth_github_id:
                            user.oauth_github_id = oauth_id
                        user.email_verified = True
                        db.commit()
                        db.refresh(user)
                        return user
                    else:
                        user = User(
                            email=email,
                            oauth_github_id=oauth_id,
                            email_verified=True
                        )
                        db.add(user)
                        db.commit()
                        db.refresh(user)
                        return user
        
        return None


auth_service = AuthService()
