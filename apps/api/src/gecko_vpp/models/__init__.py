"""ORM models — one module per Postgres schema.

Importing this package imports every model so SQLAlchemy's MetaData is fully
populated (alembic autogenerate + tests rely on this).
"""

from gecko_vpp.models.base import Base, metadata
from gecko_vpp.models import core  # noqa: F401
from gecko_vpp.models import market  # noqa: F401
from gecko_vpp.models import dispatch  # noqa: F401
from gecko_vpp.models import ems  # noqa: F401
from gecko_vpp.models import regulatory  # noqa: F401
from gecko_vpp.models import agents  # noqa: F401
from gecko_vpp.models import audit  # noqa: F401

__all__ = ["Base", "metadata"]
