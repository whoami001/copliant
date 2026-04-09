#!/usr/bin/env python3
"""
Seed database with test users for each role.

Run: python seed_users.py
"""

from app.database import engine, get_db, SessionLocal
from app.models.user import User, UserRole
from app.models.compliance_record import ComplianceRecord
from app.models.component import Component
from app.models.legal_declaration import LegalDeclaration

# 创建所有表
from app.database import Base
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # 定义测试用户 - 使用与前端一致的邮箱
    test_users = [
        {"email": "engineer@test.com", "name": "工程师用户", "role": UserRole.ENGINEER},
        {"email": "security@test.com", "name": "安全评审用户", "role": UserRole.SECURITY},
        {"email": "legal@test.com", "name": "法务审批用户", "role": UserRole.LEGAL},
        {"email": "admin@test.com", "name": "管理员用户", "role": UserRole.ADMIN},
    ]

    print("开始 seeding 测试用户...")
    created_count = 0

    for user_data in test_users:
        # 检查用户是否已存在
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()
        if existing_user:
            print(f"  用户 {user_data['email']} 已存在 (id={existing_user.id}, role={existing_user.role.value})")
            continue

        # 创建新用户 - 不指定 ID，让数据库自增
        user = User(
            email=user_data["email"],
            name=user_data["name"],
            role=user_data["role"],
            is_active=True,
        )
        db.add(user)
        db.flush()  # 立即写入以获取 ID
        created_count += 1
        print(f"  创建用户：{user_data['email']} (id={user.id}, role={user_data['role'].value})")

    db.commit()

    # 验证用户已创建
    all_users = db.query(User).all()
    print(f"\nSeeding 完成！数据库中共有 {len(all_users)} 个用户:")
    for user in all_users:
        print(f"  - {user.email} ({user.role.value})")

except Exception as e:
    db.rollback()
    print(f"Seeding 失败：{e}")
    raise
finally:
    db.close()
