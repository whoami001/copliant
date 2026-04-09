#!/usr/bin/env python
"""创建测试用户脚本"""

import sys
sys.path.insert(0, '.')

from sqlalchemy.orm import Session
from app.database import SessionLocal, Base, engine
from app.models.user import User, UserRole

# 确保表存在
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # 测试用户列表
    test_users = [
        {"email": "engineer@test.com", "name": "张三 (研发)", "role": UserRole.ENGINEER},
        {"email": "security@test.com", "name": "李四 (安全)", "role": UserRole.SECURITY},
        {"email": "legal@test.com", "name": "王五 (法务)", "role": UserRole.LEGAL},
        {"email": "admin@test.com", "name": "管理员", "role": UserRole.ADMIN},
    ]

    print("创建测试用户...")
    print("=" * 50)

    for user_data in test_users:
        # 检查是否已存在
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if existing:
            print(f"跳过 (已存在): {user_data['email']} - {existing.name}")
            continue

        user = User(
            email=user_data["email"],
            name=user_data["name"],
            role=user_data["role"],
            is_active=True,
        )
        db.add(user)
        print(f"创建：{user_data['email']} - {user_data['name']} (ID: {user.id})")

    db.commit()
    print("=" * 50)
    print("测试用户创建完成！")

    # 显示所有用户
    print("\n所有测试用户：")
    for user in db.query(User).all():
        print(f"  - {user.email}: {user.name} (角色：{user.role.value})")

except Exception as e:
    db.rollback()
    print(f"错误：{e}")
    raise
finally:
    db.close()
