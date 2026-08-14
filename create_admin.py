import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User


def create_admin(username, real_name, password):
    app = create_app()
    with app.app_context():
        existing = User.query.filter_by(username=username).first()
        if existing:
            existing.role = 'admin'
            existing.real_name = real_name or existing.real_name
            if password:
                existing.set_password(password)
            db.session.commit()
            print(f"✓ 用户 '{username}' 已升级为管理员")
        else:
            user = User(username=username, real_name=real_name or username, role='admin')
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"✓ 管理员 '{username}' 创建成功")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法:")
        print("  python create_admin.py <用户名> [真实姓名] [密码]")
        print()
        print("示例:")
        print("  python create_admin.py zhangsan 张三 pass123")
        print("  python create_admin.py lisi   李四")
        print()
        print("  密码留空则自动生成: admin123456")
        sys.exit(1)

    uname = sys.argv[1]
    rname = sys.argv[2] if len(sys.argv) > 2 else ''
    pwd = sys.argv[3] if len(sys.argv) > 3 else 'admin123456'
    create_admin(uname, rname, pwd)
