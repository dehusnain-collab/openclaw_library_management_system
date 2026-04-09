"""
Email notification service.
Covers: SCRUM-21
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import jinja2
import os

from app.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class EmailService:
    """Service for sending email notifications."""
    
    _smtp_client = None
    _template_env = None
    
    @classmethod
    def _get_template_env(cls):
        """Get Jinja2 template environment."""
        if cls._template_env is None:
            template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'email')
            if not os.path.exists(template_path):
                os.makedirs(template_path, exist_ok=True)
            
            cls._template_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(template_path),
                autoescape=True
            )
        
        return cls._template_env
    
    @classmethod
    def _get_smtp_client(cls):
        """Get SMTP client (singleton)."""
        if cls._smtp_client is None:
            try:
                if settings.SMTP_USE_SSL:
                    cls._smtp_client = smtplib.SMTP_SSL(
                        settings.SMTP_HOST,
                        settings.SMTP_PORT,
                        timeout=10
                    )
                else:
                    cls._smtp_client = smtplib.SMTP(
                        settings.SMTP_HOST,
                        settings.SMTP_PORT,
                        timeout=10
                    )
                
                if settings.SMTP_STARTTLS:
                    cls._smtp_client.starttls()
                
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    cls._smtp_client.login(
                        settings.SMTP_USERNAME,
                        settings.SMTP_PASSWORD
                    )
                
                logger.info("SMTP connection established")
            except Exception as e:
                logger.error(f"Failed to connect to SMTP server: {e}")
                cls._smtp_client = None
                raise
        
        return cls._smtp_client
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if email service is available."""
        try:
            client = cls._get_smtp_client()
            client.noop()
            return True
        except:
            return False
    
    @classmethod
    def send_email(
        cls,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content
            text_content: Plain text content (optional)
            from_email: Sender email address
            cc_emails: CC recipients
            bcc_emails: BCC recipients
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = cls._get_smtp_client()
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email or settings.SMTP_FROM_EMAIL
            msg['To'] = to_email
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Add recipients
            recipients = [to_email]
            if cc_emails:
                recipients.extend(cc_emails)
            if bcc_emails:
                recipients.extend(bcc_emails)
            
            # Add content
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            client.send_message(msg, from_addr=msg['From'], to_addrs=recipients)
            
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    @classmethod
    def send_template_email(
        cls,
        to_email: str,
        template_name: str,
        template_data: Dict[str, Any],
        subject: Optional[str] = None,
        from_email: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None
    ) -> bool:
        """
        Send email using a template.
        
        Args:
            to_email: Recipient email address
            template_name: Name of template file (without extension)
            template_data: Data for template rendering
            subject: Email subject (optional, can be in template)
            from_email: Sender email address
            cc_emails: CC recipients
            bcc_emails: BCC recipients
            
        Returns:
            True if successful, False otherwise
        """
        try:
            env = cls._get_template_env()
            
            # Load templates
            html_template = env.get_template(f"{template_name}.html")
            text_template = env.get_template(f"{template_name}.txt")
            
            # Render templates
            html_content = html_template.render(**template_data)
            text_content = text_template.render(**template_data)
            
            # Use subject from template data if not provided
            if not subject and 'subject' in template_data:
                subject = template_data['subject']
            elif not subject:
                subject = f"Notification from {settings.APP_NAME}"
            
            return cls.send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                from_email=from_email,
                cc_emails=cc_emails,
                bcc_emails=bcc_emails
            )
        except Exception as e:
            logger.error(f"Failed to send template email {template_name} to {to_email}: {e}")
            return False
    
    # Specific email methods for library system
    
    @classmethod
    def send_welcome_email(cls, user_email: str, user_name: str) -> bool:
        """Send welcome email to new user."""
        template_data = {
            'user_name': user_name,
            'app_name': settings.APP_NAME,
            'support_email': settings.SUPPORT_EMAIL,
            'current_year': datetime.now().year,
            'subject': f'Welcome to {settings.APP_NAME}!'
        }
        
        return cls.send_template_email(
            to_email=user_email,
            template_name='welcome',
            template_data=template_data
        )
    
    @classmethod
    def send_borrowing_confirmation(
        cls, 
        user_email: str, 
        user_name: str,
        book_title: str,
        due_date: datetime
    ) -> bool:
        """Send borrowing confirmation email."""
        template_data = {
            'user_name': user_name,
            'book_title': book_title,
            'due_date': due_date.strftime('%Y-%m-%d'),
            'app_name': settings.APP_NAME,
            'support_email': settings.SUPPORT_EMAIL,
            'subject': f'Book Borrowed: {book_title}'
        }
        
        return cls.send_template_email(
            to_email=user_email,
            template_name='borrowing_confirmation',
            template_data=template_data
        )
    
    @classmethod
    def send_return_confirmation(
        cls,
        user_email: str,
        user_name: str,
        book_title: str,
        fine_amount: float = 0.0
    ) -> bool:
        """Send return confirmation email."""
        template_data = {
            'user_name': user_name,
            'book_title': book_title,
            'fine_amount': fine_amount,
            'has_fine': fine_amount > 0,
            'app_name': settings.APP_NAME,
            'support_email': settings.SUPPORT_EMAIL,
            'subject': f'Book Returned: {book_title}'
        }
        
        return cls.send_template_email(
            to_email=user_email,
            template_name='return_confirmation',
            template_data=template_data
        )
    
    @classmethod
    def send_overdue_notification(
        cls,
        user_email: str,
        user_name: str,
        book_title: str,
        due_date: datetime,
        days_overdue: int,
        fine_amount: float
    ) -> bool:
        """Send overdue notification email."""
        template_data = {
            'user_name': user_name,
            'book_title': book_title,
            'due_date': due_date.strftime('%Y-%m-%d'),
            'days_overdue': days_overdue,
            'fine_amount': fine_amount,
            'app_name': settings.APP_NAME,
            'support_email': settings.SUPPORT_EMAIL,
            'subject': f'Overdue Book: {book_title}'
        }
        
        return cls.send_template_email(
            to_email=user_email,
            template_name='overdue_notification',
            template_data=template_data
        )
    
    @classmethod
    def send_password_reset_email(
        cls,
        user_email: str,
        user_name: str,
        reset_token: str,
        reset_url: str
    ) -> bool:
        """Send password reset email."""
        template_data = {
            'user_name': user_name,
            'reset_token': reset_token,
            'reset_url': reset_url,
            'app_name': settings.APP_NAME,
            'support_email': settings.SUPPORT_EMAIL,
            'subject': f'Password Reset Request for {settings.APP_NAME}'
        }
        
        return cls.send_template_email(
            to_email=user_email,
            template_name='password_reset',
            template_data=template_data
        )
    
    @classmethod
    def send_admin_notification(
        cls,
        subject: str,
        message: str,
        notification_type: str = "system"
    ) -> bool:
        """Send notification to admin."""
        if not settings.ADMIN_EMAIL:
            logger.warning("No admin email configured")
            return False
        
        template_data = {
            'subject': subject,
            'message': message,
            'notification_type': notification_type,
            'timestamp': datetime.now().isoformat(),
            'app_name': settings.APP_NAME
        }
        
        return cls.send_template_email(
            to_email=settings.ADMIN_EMAIL,
            template_name='admin_notification',
            template_data=template_data
        )
    
    @classmethod
    def send_bulk_email(
        cls,
        recipients: List[Dict[str, Any]],
        template_name: str,
        template_data_fn: callable,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send bulk emails to multiple recipients.
        
        Args:
            recipients: List of recipient dictionaries with at least 'email' key
            template_name: Name of template file
            template_data_fn: Function to generate template data for each recipient
            subject: Email subject
            
        Returns:
            Statistics about the bulk send
        """
        results = {
            'total': len(recipients),
            'success': 0,
            'failed': 0,
            'failed_emails': []
        }
        
        for recipient in recipients:
            try:
                email = recipient['email']
                template_data = template_data_fn(recipient)
                
                if not subject and 'subject' in template_data:
                    email_subject = template_data['subject']
                else:
                    email_subject = subject
                
                success = cls.send_template_email(
                    to_email=email,
                    template_name=template_name,
                    template_data=template_data,
                    subject=email_subject
                )
                
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['failed_emails'].append(email)
                
                # Small delay to avoid rate limiting
                import time
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to send bulk email to {recipient.get('email', 'unknown')}: {e}")
                results['failed'] += 1
                results['failed_emails'].append(recipient.get('email', 'unknown'))
        
        return results
    
    @classmethod
    def health_check(cls) -> Dict[str, Any]:
        """
        Perform health check on email service.
        
        Returns:
            Health check results
        """
        try:
            available = cls.is_available()
            
            return {
                'status': 'healthy' if available else 'unhealthy',
                'available': available,
                'smtp_host': settings.SMTP_HOST,
                'smtp_port': settings.SMTP_PORT,
                'from_email': settings.SMTP_FROM_EMAIL,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Email service health check failed: {e}")
            return {
                'status': 'unhealthy',
                'available': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }