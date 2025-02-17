from __future__ import annotations

import enum
import re

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
    @declared_attr
    def __tablename__(cls) -> str:
        """Define table name for all models as the snake case of the model's name."""
        first_pass = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first_pass).lower()


class User(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]


class Report(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    species: Mapped[str]

    report_participant_associations: Mapped[list[ReportParticipant]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    participants: AssociationProxy[list[ReportParticipantAssociation]] = (
        association_proxy(
            "report_participant_associations",
            "participant",
            creator=lambda participant: ReportParticipant(
                participant=participant,
                # `roles` is a custom `__init__` argument on `ReportParticipantAssociation`
                roles=participant.roles,
            ),
        )
    )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(id={self.id}, "
            f"species={self.species}, "
            f"participants={self.report_participant_associations})"
        )


class ReportParticipantAssociation(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    registered: Mapped[bool] = mapped_column(Boolean)

    report_participant_associations: Mapped[ReportParticipant] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
    )

    __mapper_args__ = {"polymorphic_on": registered}

    def __init__(self, *args, roles: list[Role] | None = None, **kwargs):
        """Provided `roles` are used by the `Report.participants` association proxy."""
        self.roles = roles
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return f"{self.__class__.__name__}()"


class ReportParticipant(Base):
    report_id: Mapped[int] = mapped_column(ForeignKey(Report.id), primary_key=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey(ReportParticipantAssociation.id), primary_key=True
    )

    report: Mapped[Report] = relationship(
        back_populates="report_participant_associations", lazy="selectin"
    )
    participant: Mapped[ReportParticipantAssociation] = relationship(
        back_populates="report_participant_associations",
        lazy="selectin",
    )
    role_associations: Mapped[list[ReportParticipantRole]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    roles: AssociationProxy[list[Role]] = association_proxy(
        "role_associations",
        "role",
        creator=lambda role: ReportParticipantRole(role=role),
    )

    def __repr__(self):
        return f"{repr(self.participant)[:-1]}, roles={self.roles})"


class ReportParticipantUnregistered(ReportParticipantAssociation):
    id: Mapped[int] = mapped_column(
        ForeignKey(ReportParticipantAssociation.id), primary_key=True
    )
    name: Mapped[str]

    __mapper_args__ = {
        "polymorphic_identity": False,
        "polymorphic_load": "inline",
    }

    def __repr__(self):
        return f"{super().__repr__()[:-1]}name={self.name})"


class ReportParticipantRegistered(ReportParticipantAssociation):
    id: Mapped[int] = mapped_column(
        ForeignKey(ReportParticipantAssociation.id), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), nullable=False)
    user: Mapped[User] = relationship(User, lazy="selectin", single_parent=True)

    __mapper_args__ = {
        "polymorphic_identity": True,
        "polymorphic_load": "inline",
    }

    @property
    def name(self) -> str:
        return self.user.name

    def __repr__(self):
        return f"{super().__repr__()[:-1]}user_id={self.user_id}, name={self.name})"


class ReportParticipantRole(Base):
    __table_args__ = (
        ForeignKeyConstraint(
            ["report_id", "participant_id"],
            [ReportParticipant.report_id, ReportParticipant.participant_id],
        ),
    )

    role: Mapped[Role] = mapped_column(
        Enum(Role, validate_strings=True), primary_key=True
    )
    report_id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column()

    def __repr__(self):
        return f"{self.__class__.__name__}(role={self.role.value})"
