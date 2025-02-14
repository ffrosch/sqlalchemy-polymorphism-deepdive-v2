from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base

def Session(echo=True):
    engine = create_engine("sqlite:///:memory:", echo=echo)
    def _fk_pragma_on_connect(dbapi_con, con_record):
        """Make SQLite respect FK constraints."""
        dbapi_con.execute("pragma foreign_keys=ON")

    from sqlalchemy import event

    event.listen(engine, "connect", _fk_pragma_on_connect)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
