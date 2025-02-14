import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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


def Session(drop_all=False, echo=True):
    from dotenv import load_dotenv

    load_dotenv()
    postgres_url = os.getenv("POSTGRES_URL")
    if not postgres_url:
        raise ValueError("POSTGRES_URL environment variable not set")

    engine = create_engine(postgres_url, echo=echo)

    if drop_all:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    return Session()


def create_user(session: Session, n: int = 1):
    users = [User(name=f"User {i}") for i in range(n)]
    session.add_all(users)
    session.commit()
    return users[0] if n == 1 else users


def create_report(session: Session, n: int = 1):
    reports = [Report(species=f"Animal {i}") for i in range(n)]
    session.add_all(reports)
    session.commit()
    return reports[0] if n == 1 else reports


def create_registered(session: Session, n: int = 1):
    registered = [Registered(user=create_user(session)) for i in range(n)]
    session.add_all(registered)
    session.commit()
    return registered[0] if n == 1 else registered


def create_unregistered(session: Session, n: int = 1):
    unregistered = [Unregistered(name=f"Unregistered {i}") for i in range(n)]
    session.add_all(unregistered)
    session.commit()
    return unregistered[0] if n == 1 else unregistered


def create_participant(
    session: Session,
    roles: Role | list[Role] = Role.creator,
    registered: bool = False,
    two_reports: bool = False,
):
    roles = [roles] if isinstance(roles, Role) else roles
    reports = (
        [create_report(session)]
        if not two_reports
        else [create_report(session) for i in range(2)]
    )
    association = (
        create_registered(session) if registered else create_unregistered(session)
    )

    participants = []
    for report in reports:
        for role in roles:
            participants.append(
                Participant(
                    report=report,
                    association=association,
                    role=role,
                )
            )

    session.add_all(participants)
    session.commit()
    return participants[0] if len(participants) == 1 else participants
