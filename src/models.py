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

    id: Mapped[int] = mapped_column(init=False, primary_key=True)


class User(Base):
    name: Mapped[str]


class Report(Base):
    species: Mapped[str]

    participants: Mapped[list[ReportParticipant]] = relationship(back_populates="report")


class Role(enum.Enum):
    creator = "creator"
    reporter = "reporter"
    observer = "observer"


class ReportParticipantAssociation(Base):
    registered: Mapped[bool] = mapped_column(Boolean, init=False)

    __mapper_args__ = {"polymorphic_on": registered}


class ReportParticipant(Base):
    __table_args__ = (UniqueConstraint("report_id", "role"),)

    report_id: Mapped[int] = mapped_column(ForeignKey(Report.id), init=False, nullable=False)
    participant_id: Mapped[int] = mapped_column(ForeignKey(ReportParticipantAssociation.id), init=False, nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, validate_strings=True), nullable=False
    )

    report: Mapped[Report] = relationship(repr=False)
    association: Mapped[ReportParticipantAssociation] = relationship()


class ReportParticipantUnregistered(ReportParticipantAssociation):
    id: Mapped[int] = mapped_column(
        ForeignKey(ReportParticipantAssociation.id), init=False, primary_key=True
    )
    name: Mapped[str]

    __mapper_args__ = {
        "polymorphic_identity": False,
        "polymorphic_load": "inline",
    }


class ReportParticipantRegistered(ReportParticipantAssociation):
    id: Mapped[int] = mapped_column(
        ForeignKey(ReportParticipantAssociation.id), init=False, primary_key=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), init=False, nullable=False)
    user: Mapped[User] = relationship(User, lazy="selectin", single_parent=True)

    __mapper_args__ = {
        "polymorphic_identity": True,
        "polymorphic_load": "inline",
    }

    @property
    def name(self) -> str:
        return self.user.name
