from logging.config import fileConfig

from alembic import context

import app.models  # noqa: F401  enregistre les tables dans Base.metadata
from app.db import Base, engine
from app.models import UTCDateTime

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def render_item(type_, obj, _autogen_context):
    """Les migrations n'importent pas le code applicatif : UTCDateTime s'écrit sa.DateTime()."""
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime()"
    return False


# render_as_batch : SQLite ne sait pas modifier une colonne, Alembic recrée la table
OPTS = dict(target_metadata=Base.metadata, render_as_batch=True, render_item=render_item)

if context.is_offline_mode():
    context.configure(url=engine.url.render_as_string(hide_password=False), literal_binds=True, **OPTS)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        context.configure(connection=connection, **OPTS)
        with context.begin_transaction():
            context.run_migrations()
