import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.models import (
    Base,
    Report,
    Role,
    User,
)
from src.models import (
    ReportParticipant as Participant,
)
from src.models import (
    ReportParticipantRegistered as Registered,
)
from src.models import (
    ReportParticipantUnregistered as Unregistered,
)


class TestRoleEnum:
    def test_create_role(self, participant_factory):
        # One role
        assert participant_factory(roles=[Role.creator]).role == Role.creator

        # Same role on different reports
        p1 = participant_factory(roles=[Role.creator])
        p2 = participant_factory(roles=[Role.creator])
        assert p1.role == Role.creator
        assert p2.role == Role.creator

        # Different roles on same report
        participant_roles = participant_factory(
            roles=[Role.creator, Role.reporter, Role.observer]
        )
        assert len(participant_roles) == 3

    def test_report_role_not_unique_fails(self, participant_factory):
        """"""
        with pytest.raises(IntegrityError):
            participant_factory(roles=[Role.creator, Role.creator])


class TestParticipant:
    @pytest.mark.parametrize("registered", [True, False])
    @pytest.mark.parametrize(
        "roles",
        [
            [Role.creator],
            [Role.creator, Role.observer],
            [Role.creator, Role.reporter, Role.observer],
        ],
    )
    def test_create_participant(self, session, participant_factory, registered, roles):
        participant_factory(roles=roles, registered=registered)
        participants = session.scalars(select(Participant)).all()

        assert len(participants) == len(roles)
        assert all(p.role in roles for p in participants)
        assert all(p.association.registered == registered for p in participants)
        assert all(p.report_id is not None for p in participants)
        assert all(p.participant_id is not None for p in participants)
        assert len(set(p.participant_id for p in participants)) == 1
