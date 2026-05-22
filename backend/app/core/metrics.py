
from prometheus_client import Counter as PromCounter, CollectorRegistry, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response

# Use default registry to integrate with other exporters (e.g., multiprocess)
REGISTRY = CollectorRegistry(auto_describe=True)
router = APIRouter()

# Factory to create or return a global counter
def Counter(name: str, documentation: str):
    if name in REGISTRY._names_to_collectors:  # reuse if exists
        return REGISTRY._names_to_collectors[name]
    return PromCounter(
        name,
        documentation,
        registry=REGISTRY
    )