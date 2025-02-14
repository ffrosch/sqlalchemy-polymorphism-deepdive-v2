import os
from functools import partial

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base
from src.utils import (
    create_participant,
    create_registered,
    create_report,
    create_unregistered,
    create_user,
)

load_dotenv()


@pytest.fixture(scope="session")
def engine():
    """
    Creates an in-memory SQLite engine and sets up the schema.
    The same engine is used for the duration of the test session.
    """
    postgres_url = os.getenv("POSTGRES_URL")
    if not postgres_url:
        raise ValueError("POSTGRES_URL environment variable not set")

    engine = create_engine(postgres_url)

    # Create all tables defined in the Base's metadata.
    Base.metadata.create_all(engine)

    yield engine

    # Teardown: drop all tables after the tests complete.
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def session(engine):
    """
    Creates a new database session for a test with a nested transaction.
    The transaction is rolled back at the end of the test to ensure isolation.
    """
    # Establish a connection and begin a non-ORM transaction.
    connection = engine.connect()
    transaction = connection.begin()

    # Bind a session to this connection.
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    # Cleanup: close the session, roll back the transaction, and close the connection.
    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


###############################################################################
# Factory Fixtures for Models
###############################################################################


@pytest.fixture
def user_factory(session):
    return partial(create_user, session)


@pytest.fixture
def report_factory(session):
    return partial(create_report, session)


@pytest.fixture
def registered_factory(session):
    return partial(create_registered, session)


@pytest.fixture
def unregistered_factory(session):
    return partial(create_unregistered, session)


@pytest.fixture
def participant_factory(session):
    return partial(create_participant, session)
