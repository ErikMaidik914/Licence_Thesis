import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.security import get_current_active_user
from ..core.metrics import Counter
from ..core.exceptions import BusinessException, NotFoundException
from ..db.session import get_db
from ..services.notifications import register_device, send_notification, acknowledge_notification
from ..db.models import Device as DeviceModel, Notification as NotificationModel

router = APIRouter(tags=["notifications"])
logger = logging.getLogger("app.notifications")

# Metrics
device_register_counter = Counter("devices_registered_total", "Total devices registered")
notifications_sent_counter = Counter("notifications_sent_total", "Total notifications sent")
notifications_ack_counter = Counter("notifications_acknowledged_total", "Total notifications acknowledged")
notifications_error_counter = Counter("notifications_errors_total", "Total notification errors")

class DeviceOut(BaseModel):
    id: str
    user_id: str
    device_token: str
    platform: str

    class Config:
        orm_mode = True

class DeviceRegister(BaseModel):
    device_token: str = Field(..., description="Push device token")
    platform: str = Field(..., description="Device platform (e.g., 'ios' or 'android')")

class NotificationOut(BaseModel):
    id: str = Field(..., description="Notification record ID")
    user_id: str = Field(..., description="User ID")
    type: str = Field(..., description="Notification type")
    payload: Dict[str, Any] = Field(..., description="Notification payload")
    sent_at: str = Field(..., description="Timestamp sent (ISO 8601)")
    status: str = Field(..., description="Notification status")

    class Config:
        orm_mode = True

@router.post("/register-device", response_model=DeviceOut, status_code=status.HTTP_200_OK)
def register_user_device(
    device: DeviceRegister,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> DeviceOut:
    if "notifications" not in getattr(current_user, 'scopes', []):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    try:
        dev = register_device(
            db=db,
            user_id=current_user.id,
            device_token=device.device_token.strip(),
            platform=device.platform.strip().lower()
        )
        device_register_counter.inc()
        logger.info("Registered device %s for user %s", dev.id, current_user.id)
        return dev
    except BusinessException as e:
        notifications_error_counter.inc()
        logger.warning("Device registration failed: %s", e)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        notifications_error_counter.inc()
        logger.exception("Unexpected error registering device for user %s", current_user.id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register device")

@router.post("/send", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
def send_user_notification(
    payload: Dict[str, Any] = Body(..., embed=True),
    notif_type: str = Body(..., embed=True),
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> NotificationModel:
    if "notifications" not in getattr(current_user, 'scopes', []):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    try:
        notif = send_notification(
            db=db,
            user_id=current_user.id,
            notif_type=notif_type.strip(),
            payload=payload
        )
        notifications_sent_counter.inc()
        logger.info("Sent notification %s to user %s", notif.id, current_user.id)
        return notif
    except BusinessException as e:
        notifications_error_counter.inc()
        logger.warning("Notification send failed: %s", e)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        notifications_error_counter.inc()
        logger.exception("Unexpected error sending notification for user %s", current_user.id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send notification")

@router.post("/{notification_id}/ack", response_model=NotificationOut, status_code=status.HTTP_200_OK)
def ack_user_notification(
    notification_id: str,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> NotificationModel:
    if "notifications" not in getattr(current_user, 'scopes', []):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    try:
        notif = acknowledge_notification(db=db, notification_id=notification_id)
    except NotFoundException:
        logger.warning("Acknowledge failed: notification %s not found", notification_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Notification not found")
    except BusinessException as e:
        notifications_error_counter.inc()
        logger.warning("Acknowledge business error: %s", e)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        notifications_error_counter.inc()
        logger.exception("Unexpected error acknowledging notification %s", notification_id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to acknowledge notification")
    if notif.user_id != current_user.id:
        logger.warning("User %s unauthorized to ack notification %s", current_user.id, notification_id)
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not authorized")
    notifications_ack_counter.inc()
    logger.info("Acknowledged notification %s for user %s", notification_id, current_user.id)
    return notif
