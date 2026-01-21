# backend/auth/__init__.py
from flask import Blueprint

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

from auth.otp import *  # noqa
from auth.telegram_webapp import *  # noqa
from auth.user_id_login import * #noqa