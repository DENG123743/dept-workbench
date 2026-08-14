from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.Text)
    members = db.relationship('User', backref='department', lazy='dynamic')
    projects = db.relationship('Project', backref='department', lazy='dynamic')


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    real_name = db.Column(db.String(64))
    role = db.Column(db.String(20), default='member')
    position = db.Column(db.String(64))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)

    events = db.relationship('Event', backref='creator', lazy='dynamic')
    notices = db.relationship('Notice', backref='author', lazy='dynamic')
    files = db.relationship('FileResource', backref='uploader', lazy='dynamic')
    tasks = db.relationship('Task', backref='assignee', lazy='dynamic', foreign_keys='Task.assignee_id')
    created_tasks = db.relationship('Task', backref='creator', lazy='dynamic', foreign_keys='Task.creator_id')
    projects = db.relationship('Project', backref='owner', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    category = db.Column(db.String(50), default='meeting')
    color = db.Column(db.String(20), default='#3b82f6')
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)

    department = db.relationship('Department', backref='events')


class Notice(db.Model):
    __tablename__ = 'notices'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='normal')
    is_top = db.Column(db.Boolean, default=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)


class FileResource(db.Model):
    __tablename__ = 'files'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(50))
    category = db.Column(db.String(50), default='general')
    description = db.Column(db.Text)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)

    department = db.relationship('Department', backref='files')

    @property
    def size_display(self):
        if not self.file_size:
            return '-'
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.now)
    tasks = db.relationship('Task', backref='project', lazy='dynamic', cascade='all, delete-orphan')


class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    parent_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))

    kanban_status = db.Column(db.String(20), default='todo')
    stage = db.Column(db.String(30), default='待办')
    priority = db.Column(db.String(20), default='normal')
    progress = db.Column(db.Integer, default=0)
    color = db.Column(db.String(20), default='#3b82f6')

    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))

    due_date = db.Column(db.Date)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    children = db.relationship('Task', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')

    STAGES = [
        ('待办', '#6b7280'),
        ('需求确认', '#3b82f6'),
        ('方案设计', '#8b5cf6'),
        ('执行中', '#f59e0b'),
        ('验收', '#10b981'),
        ('已完成', '#059669'),
    ]

    KANBAN_COLUMNS = [
        ('todo', '待办', '#6b7280'),
        ('doing', '进行中', '#3b82f6'),
        ('review', '待验收', '#f59e0b'),
        ('done', '已完成', '#10b981'),
    ]

    def compute_progress(self):
        if self.children.count() > 0:
            sub_total = self.children.count()
            sub_done = self.children.filter(Task.kanban_status == 'done').count()
            return int(sub_done * 100 / sub_total)
        stage_idx = next((i for i, (s, _) in enumerate(self.STAGES) if s == self.stage), 0)
        return int(stage_idx * 100 / (len(self.STAGES) - 1))


class Meeting(db.Model):
    __tablename__ = 'meetings'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    meeting_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    code = db.Column(db.String(20), unique=True, index=True)
    status = db.Column(db.String(20), default='upcoming')
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)

    checkins = db.relationship('CheckIn', backref='meeting', lazy='dynamic', cascade='all, delete-orphan')
    department = db.relationship('Department', backref='meetings')


class CheckIn(db.Model):
    __tablename__ = 'checkins'
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    real_name = db.Column(db.String(64))
    role = db.Column(db.String(20), default='member')
    check_in_time = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), default='present')

    user = db.relationship('User', backref='checkins')


class Topic(db.Model):
    __tablename__ = 'topics'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    category = db.Column(db.String(20), default='qa')
    status = db.Column(db.String(20), default='open')
    priority = db.Column(db.String(20), default='normal')
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    replies = db.relationship('Reply', backref='topic', lazy='dynamic', cascade='all, delete-orphan')
    author = db.relationship('User', foreign_keys=[author_id])

    CATEGORIES = [('qa', '答疑'), ('suggestion', '建议')]
    STATUSES = [('open', '待处理'), ('processing', '处理中'), ('resolved', '已解决'), ('rejected', '已忽略')]


class Reply(db.Model):
    __tablename__ = 'replies'
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_official = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    author = db.relationship('User', foreign_keys=[author_id])
