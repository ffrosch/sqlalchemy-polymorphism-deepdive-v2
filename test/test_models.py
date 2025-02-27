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
        assert participant_factory(roles=[Role.creator]).roles == [Role.creator]

        # Same role on different reports
        p1 = participant_factory(roles=[Role.creator])
        p2 = participant_factory(roles=[Role.creator])
        assert p1.roles == [Role.creator]
        assert p2.roles == [Role.creator]

        # Different roles on same report
        participant_multiple_roles = participant_factory(
            roles=[Role.creator, Role.reporter, Role.observer]
        )
        assert len(participant_multiple_roles.roles) == 3

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
        participant = session.scalar(select(Participant))

        assert participant.roles == roles
        assert participant.participant.registered == registered
        assert participant.report_id is not None
        assert participant.participant_id is not None

    @pytest.mark.xfail
    def test_two_reports_for_unregistered(self, participant_factory):
        participant_factory(registered=False, two_reports=True)

    def test_two_reports_for_registered(self, participant_factory):
        participant_factory(registered=True, two_reports=True)
