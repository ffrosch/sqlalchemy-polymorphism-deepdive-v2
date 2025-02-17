from __future__ import annotations

import enum
import re
from typing import Optional

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    and_,
    event,
    exists,
    func,
    select,
)
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    declared_attr,
    mapped_column,
    object_session,
    relationship,
    validates,
    with_polymorphic,
)


class Role(enum.Enum):
    creator = "creator"
    reporter = "reporter"
    observer = "observer"

    def __repr__(self):
        return f'"{self.value}"'


class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str | None:
        """Define table name for all models as the snake case of the model's name."""
        first_pass = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower()


class User(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"


class Report(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    species: Mapped[str]

    participants: Mapped[list[ReportParticipant]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(id={self.id}, "
            f"species={self.species}, "
            f"participants={self.participants})"
        )


class ReportParticipant(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    is_registered: Mapped[bool] = mapped_column(Boolean)
    report_id: Mapped[int] = mapped_column(ForeignKey(Report.id))

    __mapper_args__ = {"polymorphic_on": is_registered}

    # __table_args__ = Index(
    #     "only_one_unregistered_participant_per_report",
    #     id,
    #     unique=True,
    #     postgresql_where=(~is_registered),
    # )

    report: Mapped[Report] = relationship(
        back_populates="participants", lazy="selectin"
    )
    role_associations: Mapped[list[ReportParticipantRole]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
        back_populates="participant",
    )
    roles: AssociationProxy[list[Role]] = association_proxy(
        "role_associations",
        "role",
        creator=lambda role: ReportParticipantRole(role=role),
    )

    def __repr__(self):
        return f"{self.__class__.__name__}(roles={self.roles})"


class ReportParticipantUnregistered(ReportParticipant):
    id: Mapped[int] = mapped_column(ForeignKey(ReportParticipant.id), primary_key=True)
    name: Mapped[str]

    __mapper_args__ = {
        "polymorphic_identity": False,
        "polymorphic_load": "inline",
    }

    def __repr__(self):
        return f'{super().__repr__()[:-1]}, name="{self.name}")'


class ReportParticipantRegistered(ReportParticipant):
    @declared_attr.directive
    def __tablename__(cls) -> Optional[str]:
        """override __tablename__ so that this class is single-inheritance to ReportParticipant"""
        return None

    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), nullable=True)
    user: Mapped[User] = relationship(User, lazy="selectin")

    __mapper_args__ = {
        "polymorphic_identity": True,
        "polymorphic_load": "inline",
    }

    @validates("user_id")
    def validate_user_id(self, key, value):
        if value is None:
            raise ValueError("User ID cannot be None")
        return value

    @property
    def name(self) -> str:
        return self.user.name

    def __repr__(self):
        return f'{super().__repr__()[:-1]}, user_id={self.user_id}, name="{self.name}")'


class ReportParticipantRole(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey(ReportParticipant.id))
    role: Mapped[Role] = mapped_column(Enum(Role, validate_strings=True))

    participant: Mapped[ReportParticipant] = relationship(back_populates="role_associations")

    def __repr__(self):
        return f"{self.__class__.__name__}(role={self.role.value})"
