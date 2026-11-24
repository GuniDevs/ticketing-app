from __future__ import annotations

from flask import Blueprint, jsonify

from ..auth import roles_required
from ..services import report_service

bp = Blueprint("reports", __name__, url_prefix="/api/reports")


@bp.get("/summary")
@roles_required("agent", "admin")
def summary():
    return jsonify(report_service.summary())
