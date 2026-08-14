from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from models import db, Project, Task, User, Department
from decorators import admin_required

bp = Blueprint('tasks', __name__)

PRIORITY_COLORS = {'low': '#10b981', 'normal': '#3b82f6', 'high': '#f59e0b', 'urgent': '#ef4444'}


def _kanban_from_status(stage_name):
    for status, stage, _ in Task.KANBAN_COLUMNS:
        if stage == stage_name:
            return status
    stage_to_col = {
        '待办': 'todo',
        '需求确认': 'todo',
        '方案设计': 'doing',
        '执行中': 'doing',
        '验收': 'review',
        '已完成': 'done',
    }
    return stage_to_col.get(stage_name, 'todo')


@bp.route('/')
@admin_required
def index():
    project_id = request.args.get('project_id', type=int)
    projects = Project.query.order_by(Project.created_at.desc()).all()

    query = Task.query.filter(Task.parent_id.is_(None))
    if project_id:
        query = query.filter_by(project_id=project_id)
    query = query.order_by(Task.sort_order.asc(), Task.created_at.desc())
    tasks = query.all()

    deps = Department.query.all()
    users = User.query.all()
    current_project = Project.query.get(project_id) if project_id else None

    return render_template('tasks/kanban.html',
                           tasks=tasks,
                           projects=projects,
                           current_project=current_project,
                           departments=deps,
                           users=users,
                           stage_opts=Task.STAGES,
                           priority_colors=PRIORITY_COLORS)


@bp.route('/task/create', methods=['POST'])
@admin_required
def create_task():
    title = request.form.get('title', '').strip()
    if not title:
        flash('任务标题不能为空', 'danger')
        return redirect(url_for('tasks.index'))

    project_id = request.form.get('project_id')
    parent_id = request.form.get('parent_id') or None

    task = Task(
        title=title,
        description=request.form.get('description', '').strip(),
        project_id=int(project_id) if project_id else None,
        parent_id=int(parent_id) if parent_id else None,
        kanban_status=request.form.get('kanban_status', 'todo'),
        stage=request.form.get('stage', '待办'),
        priority=request.form.get('priority', 'normal'),
        assignee_id=int(request.form.get('assignee_id')) if request.form.get('assignee_id') else None,
        creator_id=current_user.id,
        department_id=int(request.form.get('department_id')) if request.form.get('department_id') else None,
        due_date=datetime.strptime(request.form['due_date'], '%Y-%m-%d').date() if request.form.get('due_date') else None,
    )
    db.session.add(task)
    db.session.commit()
    flash(f'任务「{title}」创建成功', 'success')
    return redirect(request.form.get('next') or url_for('tasks.index'))


@bp.route('/task/<int:task_id>/update', methods=['POST'])
@admin_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json(silent=True) or request.form.to_dict()

    if not (current_user.is_admin or task.creator_id == current_user.id or task.assignee_id == current_user.id):
        return jsonify({'error': '无权操作'}), 403

    if 'kanban_status' in data:
        task.kanban_status = data['kanban_status']
        if task.kanban_status == 'done':
            task.stage = '已完成'
        elif task.kanban_status == 'todo':
            task.stage = '待办'
        elif task.kanban_status == 'review':
            task.stage = '验收'

    if 'stage' in data:
        task.stage = data['stage']
        task.kanban_status = _kanban_from_status(task.stage)

    if 'title' in data:
        task.title = data['title'].strip()
    if 'description' in data:
        task.description = data['description'].strip()
    if 'priority' in data:
        task.priority = data['priority']
    if 'assignee_id' in data:
        task.assignee_id = int(data['assignee_id']) if data['assignee_id'] else None
    if 'due_date' in data and data['due_date']:
        task.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
    if 'project_id' in data:
        task.project_id = int(data['project_id']) if data['project_id'] else None

    db.session.commit()

    if request.is_json or request.accept_mimetypes.accept_json:
        return jsonify({'ok': True, 'progress': task.compute_progress()})
    return redirect(request.form.get('next') or url_for('tasks.index'))


@bp.route('/task/<int:task_id>/delete', methods=['POST'])
@admin_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if not (current_user.is_admin or task.creator_id == current_user.id):
        flash('无权删除', 'danger')
        return redirect(url_for('tasks.index'))
    db.session.delete(task)
    db.session.commit()
    flash('任务已删除', 'info')
    return redirect(url_for('tasks.index'))


@bp.route('/task/<int:task_id>/progress', methods=['POST'])
@admin_required
def set_progress(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json(silent=True)
    if not (current_user.is_admin or task.creator_id == current_user.id or task.assignee_id == current_user.id):
        return jsonify({'error': '无权操作'}), 403
    if 'stage' in data:
        task.stage = data['stage']
        task.kanban_status = _kanban_from_status(task.stage)
    db.session.commit()
    return jsonify({'ok': True, 'progress': task.compute_progress()})


@bp.route('/project/create', methods=['POST'])
@admin_required
def create_project():
    name = request.form.get('name', '').strip()
    if not name:
        flash('项目名称不能为空', 'danger')
        return redirect(url_for('tasks.index'))

    project = Project(
        name=name,
        description=request.form.get('description', '').strip(),
        owner_id=current_user.id,
        department_id=int(request.form.get('department_id')) if request.form.get('department_id') else None,
        due_date=datetime.strptime(request.form['due_date'], '%Y-%m-%d').date() if request.form.get('due_date') else None,
    )
    db.session.add(project)
    db.session.commit()
    flash(f'项目「{name}」创建成功', 'success')
    return redirect(url_for('tasks.index', project_id=project.id))


@bp.route('/project/<int:project_id>/delete', methods=['POST'])
@admin_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not (current_user.is_admin or project.owner_id == current_user.id):
        flash('无权删除', 'danger')
        return redirect(url_for('tasks.index'))
    db.session.delete(project)
    db.session.commit()
    flash('项目已删除', 'info')
    return redirect(url_for('tasks.index'))
