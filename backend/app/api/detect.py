import logging
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi import Security
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import numpy as np
import cv2

from ..core.security import get_current_user
from ..db.session import get_db
from ..services.yolo_service import detect_equipment
from ..core.metrics import Counter
from ..core.exceptions import BusinessException

router = APIRouter(tags=["detect"])
logger = logging.getLogger("app.detect")

# Metrics
metrics = {
    "detection_counter": Counter("detections_total", "Total detection requests"),
    "detection_error_counter": Counter("detection_errors_total", "Total detection errors"),
}

# Configurable limits
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/bmp"}

class Box(BaseModel):
    x1: int = Field(..., ge=0)
    y1: int = Field(..., ge=0)
    x2: int = Field(..., ge=0)
    y2: int = Field(..., ge=0)

class DetectionResult(BaseModel):
    name: str
    score: float = Field(..., ge=0.0, le=1.0)
    box: Box

@router.post(
    "/",
    response_model=List[DetectionResult],
    status_code=status.HTTP_200_OK,
)
async def detect(
    file: UploadFile = File(..., description="Image file for equipment detection"),
    current_user=Security(get_current_user, scopes=["detect"]),
    db: Session = Depends(get_db)
) -> List[DetectionResult]:
    # Validate content type
    if (ct := file.content_type) not in ALLOWED_TYPES:
        logger.warning("Unsupported media type: %s", ct)
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported media type"
        )

    # Read and size-check
    data = await file.read(MAX_UPLOAD_SIZE + 1)
    if len(data) > MAX_UPLOAD_SIZE:
        logger.warning("Upload too large: %d bytes", len(data))
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large"
        )

    # Decode image
    try:
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Decoding returned None")
    except Exception as e:
        metrics['detection_error_counter'].inc()
        logger.error("Failed to decode image: %s", e)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file"
        )

    # Perform detection
    metrics['detection_counter'].inc()
    start = time.monotonic()
    try:
        results = await run_in_threadpool(detect_equipment, img)
    except BusinessException as e:
        metrics['detection_error_counter'].inc()
        logger.error("Detection business error: %s", e)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        metrics['detection_error_counter'].inc()
        logger.exception("Detection failed for user %s", current_user.id)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Detection failed"
        )
    duration = time.monotonic() - start
    logger.info(
        "User %s detection took %.3fms, found %d items",
        current_user.id, duration * 1000, len(results)
    )

    return [
        DetectionResult(
            name=r.name,
            score=r.score,
            box=Box(x1=r.box[0], y1=r.box[1], x2=r.box[2], y2=r.box[3])
        ) for r in results
    ]
