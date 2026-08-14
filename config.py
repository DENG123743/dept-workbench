import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _db_uri():
    uri = os.environ.get('DATABASE_URL')
    if uri:
        if uri.startswith('postgres://'):
            uri = uri.replace('postgres://', 'postgresql://', 1)
        return uri
    return 'sqlite:///' + os.path.join(BASE_DIR, 'workbench.db')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dept-workbench-secret-key-2026'
    SQLALCHEMY_DATABASE_URI = _db_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'txt', 'md', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar'
    }
