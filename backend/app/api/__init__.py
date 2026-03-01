from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading
from ..database import get_db
from ..utils.security import decode_token
from ..models.user import User
from ..config import settings

security = HTTPBearer()
_rate_limit_window = timedelta(minutes=1)
_rate_limit_state: dict[tuple[int, str], deque[datetime]] = defaultdict(deque)
_rate_limit_lock = threading.Lock()
_last_activity: dict[int, datetime] = {}


def _enforce_user_rate_limit(user_id: int, request_method: str) -> None:
    now = datetime.utcnow()
    # Allow a higher read throughput because the dashboard loads several widgets in parallel.
    bucket = "read" if request_method.upper() in {"GET", "HEAD", "OPTIONS"} else "write"
    if bucket == "read":
        allowed_requests = settings.RATE_LIMIT_REQUESTS_PER_MINUTE * 5
    else:
        allowed_requests = settings.RATE_LIMIT_REQUESTS_PER_MINUTE

    with _rate_limit_lock:
        user_requests = _rate_limit_state[(user_id, bucket)]
        while user_requests and (now - user_requests[0]) > _rate_limit_window:
            user_requests.popleft()

        if len(user_requests) >= allowed_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {allowed_requests} {bucket} requests per minute."
            )

        user_requests.append(now)


def _enforce_inactivity_timeout(user_id: int) -> None:
    now = datetime.utcnow()
    timeout = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    with _rate_limit_lock:
        last_seen = _last_activity.get(user_id)
        if last_seen and (now - last_seen) > timeout:
            _last_activity[user_id] = now
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token expired due to inactivity. Please refresh your session."
            )
        _last_activity[user_id] = now


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email: str = payload.get("sub")
    user_id: int = payload.get("user_id")
    
    if email is None or user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _enforce_user_rate_limit(user.id, request.method)
    _enforce_inactivity_timeout(user.id)
    
    return user
