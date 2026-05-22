import logging
from functools import lru_cache
from typing import List, Dict, Set, Any

from prometheus_client import Counter
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Metrics
equipment_map_load_counter = Counter(
    "equipment_map_load_total", "Total times the equipment-muscle map was loaded"
)
recommendation_counter = Counter(
    "workout_recommendations_generated_total", "Total workout recommendations generated"
)
recommendation_error_counter = Counter(
    "workout_recommendation_errors_total", "Total errors during recommendation generation"
)

@lru_cache(maxsize=1)
def get_equipment_map() -> Dict[str, str]:
    raw_default: Any = settings.DEFAULT_EQUIPMENT_MUSCLE_MAP
    if not isinstance(raw_default, dict):
        logger.error("DEFAULT_EQUIPMENT_MUSCLE_MAP must be a dict, got %r", raw_default)
        raise TypeError("Invalid DEFAULT_EQUIPMENT_MUSCLE_MAP config")
    raw_overrides: Any = settings.EQUIPMENT_MUSCLE_OVERRIDES or {}
    if not isinstance(raw_overrides, dict):
        logger.error("EQUIPMENT_MUSCLE_OVERRIDES must be a dict, got %r", raw_overrides)
        raise TypeError("Invalid EQUIPMENT_MUSCLE_OVERRIDES config")
    default_map = {k.strip().lower(): v.strip() for k, v in raw_default.items()}
    override_map = {k.strip().lower(): v.strip() for k, v in raw_overrides.items()}
    merged = {**default_map, **override_map}
    equipment_map_load_counter.inc()
    logger.info("Equipment-muscle map loaded with %d entries", len(merged))
    return merged


def map_equipment_to_muscle(equipments: List[str]) -> Dict[str, str]:
    """
    Map each equipment name to its muscle group, defaulting to 'Other'.
    """
    equipment_map = get_equipment_map()
    result: Dict[str, str] = {}
    for eq in equipments:
        if not isinstance(eq, str):
            logger.warning("Non-str equipment entry: %r", eq)
            continue
        key = eq.strip().lower()
        muscle = equipment_map.get(key, "Other")
        if muscle == "Other":
            logger.debug("Unknown equipment '%s', defaulting to 'Other'", eq)
        result[eq] = muscle
    return result


def recommend_workouts(
    user_history: List[str],
    top_n: int = 5
) -> List[str]:
    """
    Recommend workouts for muscle groups not seen in user_history.
    """
    if top_n <= 0:
        logger.error("Invalid top_n value: %d", top_n)
        raise ValueError("top_n must be > 0")
    try:
        equipment_map = get_equipment_map()
        seen_muscles: Set[str] = set(
            equipment_map.get(eq.strip().lower(), "Other")
            for eq in user_history if isinstance(eq, str)
        )
        all_muscles: Set[str] = set(equipment_map.values())
        unseen = sorted(all_muscles - seen_muscles)
        recommendations = [f"Try a {muscle} workout" for muscle in unseen[:top_n]]
        recommendation_counter.inc(len(recommendations))
        logger.info(
            "Generated %d recommendations for unseen muscles: %s",
            len(recommendations), unseen[:top_n]
        )
        return recommendations
    except Exception:
        recommendation_error_counter.inc()
        logger.exception("Error generating workout recommendations")
        return []
