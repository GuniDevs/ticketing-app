"""The HTTP layer: read the request, call a service, shape the JSON answer. No business rules here."""

from .auth_controller import bp as auth_bp
from .comment_controller import bp as comment_bp
from .feedback_controller import bp as feedback_bp
from .report_controller import bp as report_bp
from .tag_controller import bp as tag_bp
from .ticket_controller import bp as ticket_bp
from .user_controller import bp as user_bp

ALL_BLUEPRINTS = (auth_bp, user_bp, ticket_bp, comment_bp, tag_bp, feedback_bp, report_bp)

__all__ = ["ALL_BLUEPRINTS"]
