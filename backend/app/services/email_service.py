import aiosmtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from ..config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_from = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        self.use_tls = settings.SMTP_USE_TLS
    
    async def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """Send an email."""
        missing_config = not all([self.smtp_host, self.smtp_user, self.smtp_password])
        placeholder_config = any(
            marker in (value or "").strip().lower()
            for value in [self.smtp_user, self.smtp_password]
            for marker in ("your-", "replace-", "example", "changeme", "placeholder")
        )
        if missing_config or placeholder_config:
            logger.warning(
                "SMTP not configured with real credentials; skipping email send. "
                "Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL."
            )
            return False
        
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.smtp_from
            message["To"] = to_email
            
            if text_content:
                part1 = MIMEText(text_content, "plain")
                message.attach(part1)
            
            part2 = MIMEText(html_content, "html")
            message.attach(part2)

            # Gmail and many providers expect STARTTLS on 587, implicit TLS on 465.
            use_tls = self.use_tls
            start_tls = None
            if self.smtp_port == 587:
                use_tls = False
                start_tls = True
            elif self.smtp_port == 465:
                use_tls = True
                start_tls = False
            
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=use_tls,
                start_tls=start_tls,
            )
            
            return True
        except Exception as exc:
            logger.exception("Failed to send email to %s: %s", to_email, exc)
            return False
    
    async def send_verification_email(self, to_email: str, verification_token: str) -> bool:
        """Send email verification email."""
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        
        html_content = f"""
        <html>
            <body>
                <h2>Verify Your Email</h2>
                <p>Please click the link below to verify your email address:</p>
                <p><a href="{verification_url}">Verify Email</a></p>
                <p>Or copy and paste this URL into your browser:</p>
                <p>{verification_url}</p>
            </body>
        </html>
        """
        
        text_content = f"Please verify your email by visiting: {verification_url}"
        
        return await self.send_email(to_email, "Verify Your Email", html_content, text_content)
    
    async def send_password_reset_email(self, to_email: str, reset_token: str) -> bool:
        """Send password reset email."""
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        html_content = f"""
        <html>
            <body>
                <h2>Reset Your Password</h2>
                <p>Click the link below to reset your password:</p>
                <p><a href="{reset_url}">Reset Password</a></p>
                <p>Or copy and paste this URL into your browser:</p>
                <p>{reset_url}</p>
                <p>This link will expire in 1 hour.</p>
            </body>
        </html>
        """
        
        text_content = f"Reset your password by visiting: {reset_url}"
        
        return await self.send_email(to_email, "Reset Your Password", html_content, text_content)


email_service = EmailService()
