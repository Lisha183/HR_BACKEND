from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def send_meeting_notification_email(slot, recipient_user, action_type):

    if not recipient_user.email:
        logger.warning(f"No email address found for user {recipient_user.username}. Skipping email notification for {action_type} slot {slot.id}.")
        return

    subject = ""
    html_message = ""
    plain_message = ""

    context = {
        'slot': slot,
        'recipient_username': recipient_user.username,
        'hr_reviewer_username': slot.hr_reviewer.username,
        'employee_username': slot.booked_by_employee.username if slot.booked_by_employee else 'N/A',
        'is_booked_by_current_user': slot.booked_by_employee == recipient_user,
        'action_type': action_type,
        'BASE_URL': settings.BASE_URL, 

    }

    if action_type == 'booked':
        subject = f"Meeting Confirmation: Your slot with {slot.hr_reviewer.username} is booked!"
        html_message = render_to_string('emails/meeting_booked_notification.html', context)
    elif action_type == 'unbooked':
        subject = f"Meeting Cancellation: Your slot with {slot.hr_reviewer.username} has been unbooked."
        html_message = render_to_string('emails/meeting_unbooked_notification.html', context)
    else:
        logger.error(f"Invalid action_type '{action_type}' for meeting notification email.")
        return

    plain_message = strip_tags(html_message) 
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL, 
            [recipient_user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email notification for slot {slot.id} ({action_type}) sent to {recipient_user.email}.")
    except Exception as e:
        logger.error(f"Failed to send email notification for slot {slot.id} ({action_type}) to {recipient_user.email}: {e}")

