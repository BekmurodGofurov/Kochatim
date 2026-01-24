# backend/api/__init__.py
from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

# route fayllar import qilinmasa endpointlar ishlamaydi
from api import users  # noqa: F401
from api import categories  # noqa: F401
from api import types  # noqa: F401
from api import seedlings  # noqa: F401
from api import sales  # noqa: F401
from api import images  # noqa: F401  <- MUHIM
from api import dashboard  # noqa: F401