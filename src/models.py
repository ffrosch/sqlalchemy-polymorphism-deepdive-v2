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
    PrimaryKeyConstraint,
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
    _report_id: Mapped[int] = mapped_column("report_id", ForeignKey(Report.id))
    is_registered: Mapped[bool] = mapped_column(Boolean)

    __mapper_args__ = {"polymorphic_on": is_registered}
    __table_args__ = (
        UniqueConstraint(
            id, _report_id, name="uq_id_report_required_by_foreignkey_composite_on_role"
        ),
    )

    report: Mapped[Report] = relationship(
        back_populates="participants",
        lazy="selectin",
    )
    role_associations: Mapped[list[ReportParticipantRole]] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    roles: AssociationProxy[list[Role]] = association_proxy(
        "role_associations",
        "role",
        creator=lambda role: ReportParticipantRole(role=role),
    )

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, report_id={self.report_id}, roles={self.roles})"

    def __init__(self, *args, report_id: int, **kwargs):
        self.report_id = report_id
        super().__init__(*args, **kwargs)

    @property
    def report_id(self):
        return self._report_id

    @report_id.setter
    def report_id(self, value):
        if self._report_id is not None:
            raise AttributeError(
                "The report_id associated with a participant cannot be changed once set."
            )
        self._report_id = value


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
    def validate_user_id(self, key, value: int):
        if value is None:
            raise ValueError("User ID cannot be None")
        return value

    @property
    def name(self) -> str:
        return self.user.name

    def __repr__(self):
        return f'{super().__repr__()[:-1]}, user_id={self.user_id}, name="{self.name}")'


class ReportParticipantRole(Base):
    role: Mapped[Role] = mapped_column(Enum(Role, validate_strings=True))
    report_id: Mapped[int] = mapped_column()
    participant_id: Mapped[int] = mapped_column()

    __table_args__ = (
        PrimaryKeyConstraint(role, report_id, name="pk_unique_report_role_combination"),
        ForeignKeyConstraint(
            [report_id, participant_id],
            [ReportParticipant._report_id, ReportParticipant.id],
            name="fk_report_participant_composite_reference",
        ),
    )

    participant: Mapped[ReportParticipant] = relationship(
        back_populates="role_associations"
    )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(report_id={self.report_id}, "
            f"participant_id={self.participant_id}, "
            f"role={self.role.value})"
        )
