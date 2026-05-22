import logging
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..db.models import Notification, Device
from ..core.config import get_settings
from ..core.exceptions import BusinessException, NotFoundException
from ..core.metrics import Counter

# Push client placeholder, e.g., FCM
# from pyfcm import FCMNotification

logger = logging.getLogger(__name__)
settings = get_settings()

# Metrics
device_register_counter = Counter("device_register_total", "Total devices registered")
notification_sent_counter = Counter("notifications_sent_total", "Total notifications sent")
notification_error_counter = Counter("notification_errors_total", "Total notification errors")

# fcm_client = FCMNotification(api_key=settings.FCM_SERVER_KEY)


def register_device(
    db: Session,
    user_id: Any,
    device_token: str,
    platform: str
) -> Device:
    """
    Register or update a user's device for push notifications.
    Raises BusinessException on failure.
    """
    if not device_token or not platform:
        raise BusinessException("Device token and platform are required")
    try:
        with db.begin():
            device = (
                db.query(Device)
                .filter_by(user_id=user_id, device_token=device_token)
                .with_for_update()
                .first()
            )
            if device:
                device.platform = platform
            else:
                device = Device(user_id=user_id, device_token=device_token, platform=platform)
                db.add(device)
    except SQLAlchemyError:
        notification_error_counter.inc()
        logger.exception("Failed to register device for user %s", user_id)
        raise BusinessException("Could not register device")
    db.refresh(device)
    device_register_counter.inc()
    logger.info("Registered device %s for user %s", device.id, user_id)
    return device


def send_notification(
    db: Session,
    user_id: Any,
    notif_type: str,
    payload: Dict[str, Any]
) -> Notification:
    """
    Create a notification record and dispatch via push service.
    Raises BusinessException on failure.
    """
    if not notif_type or not payload.get('title'):
        raise BusinessException("Notification type and payload.title are required")
    try:
        with db.begin():
            notif = Notification(
                user_id=user_id,
                type=notif_type,
                payload=payload,
                status="pending"
            )
            db.add(notif)
            db.flush()
            # dispatch
            # devices = db.query(Device).filter_by(user_id=user_id).all()
            # for device in devices:
            #     fcm_client.notify_single_device(
            #         registration_id=device.device_token,
            #         message_title=payload['title'],
            #         message_body=payload.get('body'),
            #         data_message=payload.get('data')
            #     )
            notif.status = "sent"
    except SQLAlchemyError:
        notification_error_counter.inc()
        logger.exception("Failed to send notification to user %s", user_id)
        raise BusinessException("Could not send notification")
    db.refresh(notif)
    notification_sent_counter.inc()
    logger.info("Notification %s sent for user %s", notif.id, user_id)
    return notif


def acknowledge_notification(
    db: Session,
    notification_id: Any
) -> Notification:
    """
    Mark a notification as acknowledged/read.
    Raises NotFoundException if missing.
    """
    notif = db.get(Notification, notification_id)
    if not notif:
        logger.warning("Notification %s not found for acknowledgement", notification_id)
        raise NotFoundException(f"Notification {notification_id} not found")
    try:
        with db.begin():
            notif.status = "acknowledged"
            notif.sent_at = datetime.utcnow()
    except SQLAlchemyError:
        notification_error_counter.inc()
        logger.exception("Failed to acknowledge notification %s", notification_id)
        raise BusinessException("Could not acknowledge notification")
    db.refresh(notif)
    logger.info("Notification %s acknowledged", notification_id)
    return notif
