# backend/api/__init__.py
from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

from api.users import *  # noqa
from api.categories import *  # noqa
from api.types import *  # noqa
from api.seedlings import *  # noqa
from api.sales import *  # noqa
from api.dashboard import *  # noqa
from api.images import *  # noqa