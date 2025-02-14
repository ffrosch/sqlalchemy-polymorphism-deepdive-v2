from __future__ import annotations
import re
from sqlalchemy import (
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

    id: Mapped[int] = mapped_column(init=False, primary_key=True)


class User(Base):
    name: Mapped[str]


class Report(Base):
    species: Mapped[str]

    association: Mapped[list[ReportParticipant]] = relationship(back_populates="report")
    participants: AssociationProxy[list[ReportParticipantAssociation]] = association_proxy(
        "association",
        "participant",
        creator=lambda participant: participant
    )


class RoleEnum(enum.Enum):
    creator = "creator"
    reporter = "reporter"
    observer = "observer"


class ReportParticipantAssociation(Base):
    type: Mapped[str] = mapped_column(String(12), init=False)

    __mapper_args__ = {"polymorphic_on": type}


class ReportParticipant(Base):
    report_id: Mapped[int] = mapped_column(ForeignKey(Report.id), nullable=False)
    participant_id: Mapped[int] = mapped_column(ForeignKey(ReportParticipantAssociation.id), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum), validate_strings=True, nullable=False
    )

    report: Mapped[Report] = relationship(init=False)
    participant: Mapped[ReportParticipantAssociation] = relationship()

    @validates("role")
    def validate_role(self, key, value):
        if isinstance(value, str):
            try:
                return RoleEnum(value)
            except ValueError:
                raise ValueError(f"Invalid role provided: {value}")
        elif isinstance(value, RoleEnum):
            return value
        else:
            raise ValueError(f"Invalid type for role: {type(value)}")


class ReportParticipantUnregistered(ReportParticipantAssociation):
    id: Mapped[int] = mapped_column(
        ForeignKey(ReportParticipantAssociation.id), init=False, primary_key=True
    )
    name: Mapped[str]

    __mapper_args__ = {
        "polymorphic_identity": "unregistered",
        "polymorphic_load": "inline",
    }


class ReportParticipantRegistered(ReportParticipantAssociation):
    id: Mapped[int] = mapped_column(
        ForeignKey(ReportParticipantAssociation.id), init=False, primary_key=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), nullable=False)
    user: Mapped[User] = relationship(User, lazy="selectin")

    __mapper_args__ = {
        "polymorphic_identity": "registered",
        "polymorphic_load": "inline",
    }

    @property
    def name(self) -> str:
        return self.user.name
