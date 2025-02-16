from __future__ import annotations
import re
from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    and_,
    exists,
    func,
    select,
    String,
)
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
import enum
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
    MappedAsDataclass,
)


class Base(MappedAsDataclass, DeclarativeBase, init=False):
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

    participants: Mapped[list[ReportParticipant]] = relationship(
        back_populates="report"
    )


class Role(enum.Enum):
    creator = "creator"
    reporter = "reporter"
    observer = "observer"


class ReportParticipantAssociation(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    registered: Mapped[bool] = mapped_column(Boolean)

    __mapper_args__ = {"polymorphic_on": registered}


class ReportParticipant(Base):
    report_id: Mapped[int] = mapped_column(ForeignKey(Report.id), primary_key=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey(ReportParticipantAssociation.id), primary_key=True
    )

    report: Mapped[Report] = relationship(repr=False)
    participant: Mapped[ReportParticipantAssociation] = relationship()
    _roles_mapper: Mapped[list[ReportParticipantRole]] = relationship(
        repr=False,
    )
    roles: AssociationProxy[ReportParticipantRole] = association_proxy(
        "_roles_mapper", "role", creator=lambda role: ReportParticipantRole(role=role)
    )


class ReportParticipantUnregistered(ReportParticipantAssociation):
    id: Mapped[int] = mapped_column(
        ForeignKey(ReportParticipantAssociation.id), primary_key=True
    )
    name: Mapped[str]

    __mapper_args__ = {
        "polymorphic_identity": False,
        "polymorphic_load": "inline",
    }


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
        return f"{self.__class__.__name__}(role={self.role})"
