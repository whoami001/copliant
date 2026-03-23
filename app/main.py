"""
Compliance Hub - 软件合规管理系统

内部工具，用于管理研发、安全、法务的软件合规流程。
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import traceback

from app.config import get_settings
from app.exceptions import AppException
from app.routes import auth, components, records, approvals, dashboard, legal_declarations
from app.utils import logger

settings = get_settings()


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""

    app = FastAPI(
        title=settings.app_name,
        description="软件合规管理系统 - 内部工具",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS 中间件
    allowed_hosts = settings.allowed_hosts
    origins = ["*"] if allowed_hosts == "*" else [h.strip() for h in allowed_hosts.split(",") if h.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth", tags=["auth"])
    app.include_router(components.router, prefix=f"{settings.api_prefix}/components", tags=["components"])
    app.include_router(records.router, prefix=f"{settings.api_prefix}/compliance-records", tags=["records"])
    app.include_router(approvals.router, prefix=f"{settings.api_prefix}/approvals", tags=["approvals"])
    app.include_router(dashboard.router, prefix=f"{settings.api_prefix}/dashboard", tags=["dashboard"])
    app.include_router(legal_declarations.router, prefix=f"{settings.api_prefix}/legal-declarations", tags=["legal-declarations"])

    # 健康检查
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "0.1.0"}

    # 全局异常处理器
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.error(f"Request: {request.method} {request.url}")
        raise exc


    # 静态文件服务
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # 前端页面路由
    @app.get("/app")
    async def serve_app():
        return FileResponse("static/index.html")

    # 根路径
    @app.get("/")
    async def root():
        return FileResponse("static/index.html")

    logger.info("Compliance Hub 应用启动")

    return app


app = create_app()
