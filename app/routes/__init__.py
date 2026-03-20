"""Routes 模块"""

from app.routes.auth import router as auth_router
from app.routes.components import router as components_router
from app.routes.records import router as records_router
from app.routes.approvals import router as approvals_router
from app.routes.dashboard import router as dashboard_router

__all__ = [
    "auth_router",
    "components_router",
    "records_router",
    "approvals_router",
    "dashboard_router",
]
