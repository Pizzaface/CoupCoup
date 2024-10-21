from sqlmodel import create_engine, SQLModel
from models.deal import Deal # noqa: F401
from models.store import Store # noqa: F401

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=False)

SQLModel.metadata.create_all(engine)
