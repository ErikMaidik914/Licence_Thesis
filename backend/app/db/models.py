import uuid
from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Index,
    Boolean, MetaData, UniqueConstraint, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

# Naming convention for constraints
naming_convention = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
metadata = MetaData(naming_convention=naming_convention)
Base = declarative_base(metadata=metadata)

class TimestampMixin:
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False
    )
    is_deleted = Column(
        Boolean,
        server_default=text('false'),
        nullable=False
    )

class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("char_length(username) >= 3", name="ck_users_username_len"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, server_default=text('true'), nullable=False)

    scans = relationship(
        "Scan", lazy="selectin", back_populates="user"
    )
    workout_plans = relationship(
        "WorkoutPlan", lazy="selectin", back_populates="user"
    )
    progress_entries = relationship(
        "ProgressEntry", lazy="selectin", back_populates="user"
    )
    devices = relationship(
        "Device", lazy="selectin", back_populates="user"
    )
    notifications = relationship(
        "Notification", lazy="selectin", back_populates="user"
    )
    user_badges = relationship(
        "UserBadge", lazy="selectin", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username!r})>"

class Scan(Base, TimestampMixin):
    __tablename__ = "scans"
    __table_args__ = (
        Index("ix_scans_user_equipment", "user_id", "equipment"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    equipment = Column(String(100), nullable=False)

    user = relationship("User", lazy="selectin", back_populates="scans")

    def __repr__(self) -> str:
        return f"<Scan(id={self.id}, user_id={self.user_id}, equipment={self.equipment!r})>"

class WorkoutPlan(Base, TimestampMixin):
    __tablename__ = "workout_plans"
    __table_args__ = (
        Index("ix_workout_plans_user", "user_id"),
        UniqueConstraint("user_id", "name", name="uq_plans_user_name"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(String(100), nullable=False)
    goal = Column(String(50), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    config = Column(JSONB, server_default=text("'{}'"), nullable=False)

    user = relationship("User", lazy="selectin", back_populates="workout_plans")
    phases = relationship(
        "PlanPhase", lazy="selectin", back_populates="plan"
    )

    def __repr__(self) -> str:
        return f"<WorkoutPlan(id={self.id}, name={self.name!r})>"

class PlanPhase(Base, TimestampMixin):
    __tablename__ = "plan_phases"
    __table_args__ = (
        Index("ix_plan_phases_plan", "plan_id"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("workout_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    phase_name = Column(String(100), nullable=False)
    week_number = Column(Integer, nullable=False)
    details = Column(JSONB, server_default=text("'{}'"), nullable=False)

    plan = relationship("WorkoutPlan", lazy="selectin", back_populates="phases")

    def __repr__(self) -> str:
        return f"<PlanPhase(id={self.id}, week={self.week_number})>"

class ProgressEntry(Base, TimestampMixin):
    __tablename__ = "progress_entries"
    __table_args__ = (
        Index("ix_progress_user_date", "user_id", "date"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    date = Column(DateTime(timezone=True), nullable=False)
    muscle_group = Column(String(50), nullable=False, index=True)
    metric = Column(String(50), nullable=False)
    value = Column(String(100), nullable=False)
    metadata_json = Column(
        "metadata",
        JSONB,
        server_default=text("'{}'"),
        nullable=False
    )

    user = relationship("User", lazy="selectin", back_populates="progress_entries")

    def __repr__(self) -> str:
        return f"<ProgressEntry(id={self.id}, muscle={self.muscle_group!r})>"

class Badge(Base, TimestampMixin):
    __tablename__ = "badges"
    __table_args__ = (
        Index("ix_badges_name", "name"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    criteria = Column(JSONB, server_default=text("'[]'"), nullable=False)

    user_badges = relationship(
        "UserBadge", lazy="selectin", back_populates="badge"
    )

    def __repr__(self) -> str:
        return f"<Badge(name={self.name!r})>"

class UserBadge(Base, TimestampMixin):
    __tablename__ = "user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_user_badges_user_badge"),
        Index("ix_user_badges_user_badge", "user_id", "badge_id"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    badge_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("badges.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    awarded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    user = relationship("User", lazy="selectin", back_populates="user_badges")
    badge = relationship("Badge", lazy="selectin", back_populates="user_badges")

    def __repr__(self) -> str:
        return f"<UserBadge(user_id={self.user_id}, badge_id={self.badge_id})>" 

class Device(Base, TimestampMixin):
    __tablename__ = "devices"
    __table_args__ = (
        Index("ix_devices_user", "user_id"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    device_token = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False)

    user = relationship("User", lazy="selectin", back_populates="devices")

    def __repr__(self) -> str:
        return f"<Device(platform={self.platform!r})>"

class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_status", "user_id", "status"),
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    type = Column(String(50), nullable=False)
    payload = Column(JSONB, server_default=text("'{}'"), nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(50), nullable=False)

    user = relationship("User", lazy="selectin", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification(type={self.type!r})>"

class AdminLog(Base, TimestampMixin):
    __tablename__ = "admin_logs"

    id = Column(Integer, primary_key=True)
    admin_user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    action = Column(String(100), nullable=False)
    target_table = Column(String(50), nullable=False)
    target_id = Column(PG_UUID(as_uuid=True), nullable=True)
    details = Column(JSONB, server_default=text("'{}'"), nullable=False)

    def __repr__(self) -> str:
        return f"<AdminLog(admin={self.admin_user_id}, action={self.action!r})>"
    

class RevokedToken(Base, TimestampMixin):
    __tablename__ = "revoked_tokens"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jti = Column(String(255), unique=True, nullable=False, index=True)
    revoked_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )