import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, FileResource, Department

bp = Blueprint('files', __name__)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_file(file_storage):
    original = secure_filename(file_storage.filename)
    ext = original.rsplit('.', 1)[-1].lower() if '.' in original else ''
    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
    file_storage.save(save_path)
    return unique_name, save_path, os.path.getsize(save_path), ext


@bp.route('/')
@login_required
def index():
    dept_id = request.args.get('department_id', type=int)
    category = request.args.get('category', '')
    query = FileResource.query
    if dept_id:
        query = query.filter_by(department_id=dept_id)
    if category:
        query = query.filter_by(category=category)
    files = query.order_by(FileResource.created_at.desc()).all()
    departments = Department.query.all()
    categories = ['general', 'schedule', 'lecture', 'competition', 'training']
    return render_template('files/index.html', files=files, departments=departments,
                           categories=categories, current_dept=dept_id, current_category=category)


@bp.route('/upload', methods=['POST'])
@login_required
def upload():
    file = request.files.get('file')
    if not file or file.filename == '':
        flash('请选择要上传的文件', 'danger')
        return redirect(url_for('files.index'))

    if not allowed_file(file.filename):
        flash('不支持的文件类型', 'danger')
        return redirect(url_for('files.index'))

    try:
        unique_name, save_path, size, ext = save_file(file)
    except Exception as e:
        flash(f'文件保存失败: {e}', 'danger')
        return redirect(url_for('files.index'))

    original_name = secure_filename(file.filename)
    resource = FileResource(
        filename=unique_name,
        original_name=original_name,
        file_path=save_path,
        file_size=size,
        file_type=ext,
        category=request.form.get('category', 'general'),
        description=request.form.get('description', '').strip(),
        uploader_id=current_user.id,
        department_id=request.form.get('department_id') or None,
    )
    db.session.add(resource)
    db.session.commit()
    flash(f'文件 {original_name} 上传成功', 'success')
    return redirect(url_for('files.index'))


@bp.route('/<int:file_id>/delete', methods=['POST'])
@login_required
def delete(file_id):
    resource = FileResource.query.get_or_404(file_id)
    if not (current_user.is_admin or resource.uploader_id == current_user.id):
        flash('无权删除', 'danger')
        return redirect(url_for('files.index'))

    if os.path.exists(resource.file_path):
        os.remove(resource.file_path)

    db.session.delete(resource)
    db.session.commit()
    flash('文件已删除', 'info')
    return redirect(url_for('files.index'))
