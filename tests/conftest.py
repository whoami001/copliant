"""pytest 配置"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.config import get_settings

# 测试数据库配置
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
settings = get_settings()


def create_auth_token(email: str) -> str:
    """创建认证 token"""
    return jwt.encode({"email": email}, settings.secret_key, algorithm=settings.algorithm)


@pytest.fixture
def auth_headers(db_session):
    """创建工程师用户的认证 headers"""
    # 确保用户存在于数据库中
    user = db_session.query(User).filter(User.email == "engineer@test.com").first()
    if not user:
        user = User(
            email="engineer@test.com",
            name="Test Engineer",
            role=UserRole.ENGINEER,
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
    token = create_auth_token("engineer@test.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def security_auth_headers(db_session):
    """创建安全用户的认证 headers"""
    user = db_session.query(User).filter(User.email == "security@test.com").first()
    if not user:
        user = User(
            email="security@test.com",
            name="Test Security",
            role=UserRole.SECURITY,
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
    token = create_auth_token("security@test.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def legal_auth_headers(db_session):
    """创建设务用户的认证 headers"""
    user = db_session.query(User).filter(User.email == "legal@test.com").first()
    if not user:
        user = User(
            email="legal@test.com",
            name="Test Legal",
            role=UserRole.LEGAL,
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
    token = create_auth_token("legal@test.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(db_session):
    """创建管理员用户的认证 headers"""
    user = db_session.query(User).filter(User.email == "admin@test.com").first()
    if not user:
        user = User(
            email="admin@test.com",
            name="Test Admin",
            role=UserRole.ADMIN,
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
    token = create_auth_token("admin@test.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def engineer(db_session):
    """创建工程师用户"""
    user = User(
        id=1,
        email="engineer@test.com",
        name="Test Engineer",
        role=UserRole.ENGINEER,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def security(db_session):
    """创建安全用户"""
    user = User(
        id=2,
        email="security@test.com",
        name="Test Security",
        role=UserRole.SECURITY,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def legal(db_session):
    """创建设务用户"""
    user = User(
        id=3,
        email="legal@test.com",
        name="Test Legal",
        role=UserRole.LEGAL,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin(db_session):
    """创建管理员用户"""
    user = User(
        id=4,
        email="admin@test.com",
        name="Test Admin",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user
