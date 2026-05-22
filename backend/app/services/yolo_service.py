import time
import logging
from functools import lru_cache
from typing import List, Union, Optional, Dict

import cv2
import numpy as np
import torch
from ultralytics import YOLO
from pydantic import BaseModel, conlist

from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Select device: use CPU if no CUDA available
YOLO_DEVICE = settings.device if torch.cuda.is_available() else 'cpu'

# Define class names for YOLO model outputs (index -> name)
CLASS_NAMES = [
    "Chest Press machine",
    "Lat Pull Down",
    "Seated Cable Rows",
    "chest fly machine",
    "chinning dipping",
    "lateral raises machine",
    "leg extension",
    "leg press",
    "reg curl machine",
    "seated dip machine",
    "shoulder press machine",
    "smith machine",
    "arm curl machine",
]

class DetectionResult(BaseModel):
    name: str
    score: float
    box: conlist(int, min_length=4, max_length=4)

@lru_cache(maxsize=1)
def get_model() -> YOLO:
    try:
        model = YOLO(settings.yolo_weights)
        # Warm-up with a single dummy image (3D array)
        dummy_img = np.zeros((settings.input_size, settings.input_size, 3), dtype=np.uint8)
        _ = model(
            dummy_img,
            device=YOLO_DEVICE,
            half=settings.half_precision,
            imgsz=settings.input_size,
            stream=False
        )
        logger.info("YOLO model loaded and warmed up on device %s", YOLO_DEVICE)
    except Exception:
        logger.exception("Failed to load YOLO model")
        raise
    return model


def preprocess_image(
    image_data: Union[bytes, np.ndarray],
    max_size: Optional[int] = None
) -> np.ndarray:
    if isinstance(image_data, (bytes, bytearray)):
        arr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    elif isinstance(image_data, np.ndarray):
        img = image_data
    else:
        raise TypeError(f"Unsupported image type: {type(image_data)}")
    if img is None:
        raise ValueError("Image decoding failed")
    if max_size:
        h, w = img.shape[:2]
        scale = min(max_size / max(h, w), 1.0)
        if scale < 1.0:
            img = cv2.resize(img, (int(w*scale), int(h*scale)))
    return img


def detect_equipment(
    image_data: Union[bytes, np.ndarray],
    batch: bool = False
) -> List[DetectionResult]:
    img = preprocess_image(image_data, max_size=settings.input_size)
    model = get_model()
    start = time.perf_counter()
    try:
        # Call model without unsupported args
        results = model(
            img,
            device=YOLO_DEVICE,
            half=settings.half_precision,
            imgsz=settings.input_size,
            stream=False
        )
    except Exception:
        logger.exception("YOLO inference error")
        raise RuntimeError("Detection failed")
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("Inference time: %.1fms", duration_ms)

    detections: List[DetectionResult] = []
    res = results[0] if isinstance(results, list) else results
    boxes = res.boxes
    for xyxy, conf, cls in zip(
        boxes.xyxy.cpu().numpy(),
        boxes.conf.cpu().numpy(),
        boxes.cls.cpu().numpy()
    ):
        idx = int(cls)
        name = CLASS_NAMES[idx] if idx < len(CLASS_NAMES) else str(idx)
        detections.append(
            DetectionResult(
                name=name,
                score=float(conf),
                box=[int(coord) for coord in xyxy]
            )
        )
    return detections
