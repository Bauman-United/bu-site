from alembic import context
from bu_core.db import make_engine
from bu_core.models import Base

target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = make_engine()
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
