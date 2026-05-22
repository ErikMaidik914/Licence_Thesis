import os
import ast
import codecs
from dotenv import load_dotenv

load_dotenv()

# Database
_raw_db = os.getenv("DATABASE_URL", "")
DATABASE_URL = codecs.decode(_raw_db, "unicode_escape")

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
DEBUG = os.getenv("DEBUG", "false").lower() in ("true","1","yes")

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", None)

# Hosts & CORS
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]
CORS_ORIGINS = [u.strip() for u in os.getenv("CORS_ORIGINS", "").split(",") if u.strip()]

# Logging & Sentry
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# Time & Tasks
TIMEZONE = os.getenv("TIMEZONE", "UTC")
BADGE_EVAL_CRON = os.getenv("BADGE_EVAL_CRON", "0 * * * *")
DAILY_REMINDER_CRON = os.getenv("DAILY_REMINDER_CRON", "0 8 * * *")

# YOLO
YOLO_WEIGHTS = os.getenv("YOLO_WEIGHTS", "")
INPUT_SIZE = int(os.getenv("INPUT_SIZE", "640"))
HALF_PRECISION = os.getenv("HALF_PRECISION", "false").lower() in ("true","1","yes")
DEVICE = int(os.getenv("DEVICE", "0"))

# Equipment-muscle map
_raw_map = os.getenv("DEFAULT_EQUIPMENT_MUSCLE_MAP", "{}").strip()
try:
    DEFAULT_EQUIPMENT_MUSCLE_MAP = ast.literal_eval(_raw_map)
except Exception:
    DEFAULT_EQUIPMENT_MUSCLE_MAP = {}

# Badge criteria configuration
_raw_criteria = os.getenv("BADGE_CRITERIA", "[]").strip()
try:
    BADGE_CRITERIA = ast.literal_eval(_raw_criteria)
    if not isinstance(BADGE_CRITERIA, list):
        BADGE_CRITERIA = []
except Exception:
    BADGE_CRITERIA = []

# Database pool
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_ISOLATION_LEVEL = os.getenv("DB_ISOLATION_LEVEL", "READ COMMITTED")

# App info
APP_NAME = os.getenv("APP_NAME", "Gym Equipment Detection API")
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "Detect gym equipment via AI")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")


class Settings:
    def __init__(self):
        self.environment = ENVIRONMENT
        self.debug = DEBUG
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM
        self.access_token_expire_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
        self.jwt_audience = JWT_AUDIENCE

        self.database_url = DATABASE_URL
        self.allowed_hosts = ALLOWED_HOSTS
        self.cors_origins = CORS_ORIGINS

        self.log_level = LOG_LEVEL
        self.sentry_dsn = SENTRY_DSN

        self.timezone = TIMEZONE
        self.badge_eval_cron = BADGE_EVAL_CRON
        self.daily_reminder_cron = DAILY_REMINDER_CRON

        self.yolo_weights = YOLO_WEIGHTS
        self.input_size = INPUT_SIZE
        self.half_precision = HALF_PRECISION
        self.device = DEVICE

        self.default_equipment_muscle_map = DEFAULT_EQUIPMENT_MUSCLE_MAP
        self.badge_criteria = BADGE_CRITERIA

        self.db_pool_size = DB_POOL_SIZE
        self.db_max_overflow = DB_MAX_OVERFLOW
        self.db_pool_recycle = DB_POOL_RECYCLE
        self.db_pool_timeout = DB_POOL_TIMEOUT
        self.db_isolation_level = DB_ISOLATION_LEVEL

        self.app_name = APP_NAME
        self.app_description = APP_DESCRIPTION
        self.app_version = APP_VERSION


_settings = Settings()

def get_settings():
    return _settings
