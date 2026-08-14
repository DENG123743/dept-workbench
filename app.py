import os
import socket
from datetime import datetime, date
from flask import Flask, render_template, flash, redirect, url_for, request, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from config import Config
from models import db, User, Department, Event, Notice, FileResource

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = '请先登录'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from blueprints.dashboard import bp as dashboard_bp
    from blueprints.schedule import bp as schedule_bp
    from blueprints.members import bp as members_bp
    from blueprints.notices import bp as notices_bp
    from blueprints.files import bp as files_bp
    from blueprints.tasks import bp as tasks_bp
    from blueprints.checkin import bp as checkin_bp
    from blueprints.qa import bp as qa_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(schedule_bp, url_prefix='/schedule')
    app.register_blueprint(members_bp, url_prefix='/members')
    app.register_blueprint(notices_bp, url_prefix='/notices')
    app.register_blueprint(files_bp, url_prefix='/files')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(checkin_bp, url_prefix='/checkin')
    app.register_blueprint(qa_bp, url_prefix='/qa')

    @app.context_processor
    def inject_globals():
        def _detect_lan_base():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
                s.close()
                return f'http://{ip}:5000'
            except Exception:
                return None

        request_host = request.host_url.rstrip('/') if request else ''
        lan_base = _detect_lan_base()

        share_base = request_host
        if lan_base and ('127.0.0.1' in request_host or 'localhost' in request_host):
            share_base = lan_base

        return {
            'now': datetime.now(),
            'today': date.today(),
            'base_template': 'base.html',
            'share_base_url': share_base,
        }

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash('登录成功', 'success')
                next_page = request.args.get('next') or url_for('dashboard.index')
                return redirect(next_page)
            flash('用户名或密码错误', 'danger')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('已退出登录', 'info')
        return redirect(url_for('login'))

    @app.route('/uploads/<path:filename>')
    @login_required
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)

    with app.app_context():
        db.create_all()
        seed_data()

    return app


def seed_data():
    if Department.query.count() == 0:
        depts = [
            Department(name='解剖小组', description='负责解剖相关讲座和教学活动'),
            Department(name='病理小组', description='负责病理学相关讲座和病例分析'),
            Department(name='法医学小组', description='负责法医学讲座和专业活动'),
            Department(name='组委会', description='负责比赛组织和评审工作'),
        ]
        db.session.add_all(depts)
        db.session.flush()

        admin = User(username='admin', real_name='系统管理员', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)

        demo_users = [
            ('leader', '张组长', '组长', '13800138001', 'leader123', depts[0]),
            ('member1', '李同学', '成员', '13800138002', 'member123', depts[0]),
            ('member2', '王同学', '成员', '13800138003', 'member123', depts[1]),
            ('member3', '赵同学', '成员', '13800138004', 'member123', depts[2]),
        ]
        for u in demo_users:
            user = User(username=u[0], real_name=u[1], position=u[2], phone=u[3], department=u[5])
            user.set_password(u[4])
            db.session.add(user)

        db.session.flush()

        now = datetime.now()
        demo_events = [
            Event(title='秋季招新宣讲会', description='面向新生的部门招新宣讲',
                  start_time=datetime(now.year, now.month, min(now.day + 2, 28), 19, 0),
                  end_time=datetime(now.year, now.month, min(now.day + 2, 28), 21, 0),
                  location='教学楼A301', category='meeting', color='#3b82f6',
                  creator_id=admin.id, department_id=depts[3].id),
            Event(title='解剖小组周会', description='本周工作汇总与下周安排',
                  start_time=datetime(now.year, now.month, min(now.day + 1, 28), 20, 0),
                  end_time=datetime(now.year, now.month, min(now.day + 1, 28), 21, 30),
                  location='线上腾讯会议', category='meeting', color='#10b981',
                  creator_id=admin.id, department_id=depts[0].id),
            Event(title='法医学讲座筹备', description='场地、嘉宾、宣传物料准备',
                  start_time=datetime(now.year, now.month, min(now.day + 5, 28), 14, 0),
                  end_time=datetime(now.year, now.month, min(now.day + 5, 28), 17, 0),
                  location='行政楼会议室', category='prep', color='#f59e0b',
                  creator_id=admin.id, department_id=depts[2].id),
        ]
        db.session.add_all(demo_events)

        demo_notices = [
            Notice(title='关于秋季招新的通知', content='请各小组负责人于本周六前提交招新计划和宣讲材料。',
                   priority='high', is_top=True, author_id=admin.id),
            Notice(title='部员大会时间调整', content='原定周三的部员大会调整至周五晚7点，地点不变。',
                   priority='normal', author_id=admin.id),
        ]
        db.session.add_all(demo_notices)

        db.session.commit()


app = create_app()


if __name__ == '__main__':
    def _lan_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'

    lan_ip = _lan_ip()
    print('=' * 50)
    print('  部门工作台启动中...')
    print('  默认管理员: admin / admin123')
    print(f'  本机访问:   http://127.0.0.1:5000')
    print(f'  局域网访问: http://{lan_ip}:5000')
    print('=' * 50)
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
