#!/usr/bin/env python3
"""
合并同一系统的旧通知消息

将旧格式的多条通知合并为一条新格式通知
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models.notification import Notification, NotificationType
from app.models.user import User
import re
from datetime import datetime

def merge_security_rejected_notifications():
    """合并所有用户的安全驳回通知"""
    db = SessionLocal()
    try:
        # 获取所有用户
        users = db.query(User).all()
        
        for user in users:
            # 获取该用户所有未读的安全驳回通知
            notifications = db.query(Notification).filter(
                Notification.user_id == user.id,
                Notification.type == NotificationType.SECURITY_REJECTED,
                Notification.is_read == False,
            ).order_by(Notification.created_at.desc()).all()
            
            if len(notifications) <= 1:
                continue
            
            # 按系统名称分组
            system_groups = {}
            for notif in notifications:
                # 从旧格式消息中提取系统名称
                # 格式：您的合规记录「<component>@<version> - <system_name>」...
                match = re.search(r' - ([^」]+)」', notif.message)
                if match:
                    system_name = match.group(1).strip()
                else:
                    # 新格式：系统：<system_name>
                    match = re.search(r'系统：([^(（\n]+)', notif.message)
                    system_name = match.group(1).strip() if match else "未知系统"
                
                if system_name not in system_groups:
                    system_groups[system_name] = []
                system_groups[system_name].append(notif)
            
            # 合并每组消息
            for system_name, group in system_groups.items():
                if len(group) <= 1:
                    continue
                
                # 保留最新的一条，更新其内容
                latest = group[0]
                old_ones = group[1:]
                
                # 收集所有驳回原因和字段
                reasons = []
                fields = set()
                component_count = len(group)
                
                for notif in group:
                    reason_match = re.search(r'驳回原因：([^\n]*)', notif.message)
                    if reason_match:
                        reasons.append(reason_match.group(1).strip())
                    
                    fields_match = re.search(r'需要补充的字段：([^\n]*)', notif.message)
                    if fields_match:
                        for f in fields_match.group(1).split(','):
                            if f.strip():
                                fields.add(f.strip())
                
                # 更新最新通知的格式
                latest.message = (
                    f"系统：{system_name}（{component_count} 个组件）\n"
                    f"驳回原因：{reasons[0] if reasons else '待补充'}\n"
                    f"需要补充的字段：{', '.join(sorted(fields)) if fields else '无'}\n"
                    f"备注：{reasons[0] if reasons else '待补充'}"
                )
                latest.created_at = datetime.utcnow()
                
                # 删除旧消息
                for notif in old_ones:
                    db.delete(notif)
                
                print(f"用户 {user.email}: 合并系统 '{system_name}' 的 {component_count} 条消息为 1 条")
        
        db.commit()
        print("完成！")
        
    except Exception as e:
        db.rollback()
        print(f"错误：{e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    merge_security_rejected_notifications()
