# --- backend/app/services/email_service.py ---
import smtplib
import os
from email.message import EmailMessage
from app.models.contact import ContactForm # Use correct model path
from app.core.config import settings # Use correct settings path
import logging

logger = logging.getLogger(__name__)

async def send_contact_email(form_data: ContactForm):
    """Placeholder/Basic function to send contact form data via SMTP."""
    required_settings = [
        settings.SMTP_HOST, settings.SMTP_PORT, settings.SMTP_USER,
        settings.SMTP_PASSWORD, settings.SMTP_FROM, settings.CONTACT_TO_EMAIL
    ]
    if not all(required_settings):
        logger.warning("SMTP settings not fully configured in .env. Skipping email sending for contact form.")
        # Decide behaviour: raise error or just log and proceed?
        # For now, just log it. In production, might want to ensure critical notifications send.
        # raise RuntimeError("SMTP settings incomplete, cannot send email.")
        print("--- Skipping Email: SMTP settings incomplete ---")
        return # Don't block contact form success if email fails setup

    msg = EmailMessage()
    msg.set_content(
        f"Name: {form_data.name}\n"
        f"Email: {form_data.email}\n"
        f"Company: {form_data.company or 'N/A'}\n"
        f"Phone: {form_data.phone or 'N/A'}\n"
        f"Subject: {form_data.subject}\n\n"
        f"Message:\n{form_data.message}"
    )
    msg["Subject"] = f"New Website Contact Inquiry: {form_data.subject}"
    # Ensure FROM address is valid for the sending server
    msg["From"] = settings.SMTP_FROM
    msg["To"] = settings.CONTACT_TO_EMAIL

    try:
        logger.info(f"Attempting to send contact email to {settings.CONTACT_TO_EMAIL} via {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        # Use timeout for SMTP connection
        smtp_class = smtplib.SMTP_SSL if settings.SMTP_PORT == 465 else smtplib.SMTP
        with smtp_class(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_PORT != 465: # Use STARTTLS for non-SSL ports like 587
                 server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Contact email successfully sent to {settings.CONTACT_TO_EMAIL}")
    except smtplib.SMTPAuthenticationError as e:
         logger.error(f"SMTP Authentication Error: {e}", exc_info=True)
         raise RuntimeError(f"SMTP Authentication Failed. Check credentials in .env.")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP Error sending email: {e}", exc_info=True)
        raise RuntimeError(f"Failed to send email due to SMTP error: {e}")
    except TimeoutError:
         logger.error(f"SMTP Connection Timeout to {settings.SMTP_HOST}:{settings.SMTP_PORT}")
         raise RuntimeError("Failed to send email: Connection timed out.")
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}", exc_info=True)
        raise RuntimeError(f"An unexpected error occurred while sending email: {e}")