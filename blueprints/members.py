from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models import db, User, Department
from decorators import admin_required

bp = Blueprint('members', __name__)


@bp.route('/')
@login_required
def index():
    group_id = request.args.get('group_id', type=int)
    query = User.query
    if group_id:
        query = query.filter_by(department_id=group_id)
    members = query.order_by(User.role.desc(), User.created_at.asc()).all()
    groups = Department.query.order_by(Department.name.asc()).all()
    return render_template('members/index.html', members=members,
                           groups=groups, current_group=group_id)


@bp.route('/create', methods=['POST'])
@admin_required
def create():
    username = request.form.get('username', '').strip()
    real_name = request.form.get('real_name', '').strip()
    password = request.form.get('password', '')

    if not username or not real_name or not password:
        flash('请填写完整信息', 'danger')
        return redirect(url_for('members.index'))

    if User.query.filter_by(username=username).first():
        flash('用户名已存在', 'danger')
        return redirect(url_for('members.index'))

    user = User(
        username=username,
        real_name=real_name,
        role=request.form.get('role', 'member'),
        position=request.form.get('position', '').strip(),
        phone=request.form.get('phone', '').strip(),
        email=request.form.get('email', '').strip(),
        department_id=request.form.get('department_id') or None,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    flash(f'成员 {real_name} 添加成功', 'success')
    return redirect(url_for('members.index'))


@bp.route('/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete(user_id):
    if user_id == current_user.id:
        flash('不能删除自己', 'danger')
        return redirect(url_for('members.index'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('成员已删除', 'info')
    return redirect(url_for('members.index'))


@bp.route('/<int:user_id>/edit', methods=['POST'])
@login_required
def update(user_id):
    user = User.query.get_or_404(user_id)
    is_self = (user_id == current_user.id)

    if not (current_user.is_admin or is_self):
        flash('无权修改', 'danger')
        return redirect(url_for('members.index'))

    user.real_name = request.form.get('real_name', user.real_name or '').strip()

    if current_user.is_admin:
        user.role = request.form.get('role', user.role)
        user.position = request.form.get('position', '').strip() or None
        user.department_id = int(request.form['department_id']) if request.form.get('department_id') else None

    user.phone = request.form.get('phone', '').strip() or None
    user.email = request.form.get('email', '').strip() or None

    new_pwd = request.form.get('password', '').strip()
    if current_user.is_admin and new_pwd:
        user.set_password(new_pwd)

    db.session.commit()
    flash(f'成员「{user.real_name or user.username}」信息已更新', 'success')
    return redirect(url_for('members.index'))


# ---------- 分组 (Department) CRUD ----------

@bp.route('/groups/create', methods=['POST'])
@admin_required
def create_group():
    name = request.form.get('group_name', '').strip()
    description = request.form.get('group_desc', '').strip()
    if not name:
        flash('分组名称不能为空', 'danger')
        return redirect(url_for('members.index'))
    if Department.query.filter_by(name=name).first():
        flash('分组名称已存在', 'danger')
        return redirect(url_for('members.index'))
    g = Department(name=name, description=description or None)
    db.session.add(g)
    db.session.commit()
    flash(f'分组「{name}」已创建', 'success')
    return redirect(url_for('members.index'))


@bp.route('/groups/<int:group_id>/rename', methods=['POST'])
@admin_required
def rename_group(group_id):
    group = Department.query.get_or_404(group_id)
    name = request.form.get('group_name', '').strip()
    description = request.form.get('group_desc', '').strip()
    if not name:
        flash('分组名称不能为空', 'danger')
        return redirect(url_for('members.index'))
    if Department.query.filter_by(name=name).first() and Department.query.filter_by(name=name).first().id != group_id:
        flash('分组名称已存在', 'danger')
        return redirect(url_for('members.index'))
    group.name = name
    group.description = description or None
    db.session.commit()
    flash(f'分组已更新', 'success')
    return redirect(url_for('members.index'))


@bp.route('/groups/<int:group_id>/delete', methods=['POST'])
@admin_required
def delete_group(group_id):
    group = Department.query.get_or_404(group_id)
    if group.members.count() > 0:
        flash(f'分组内还有 {group.members.count()} 名成员，无法删除。请先重新分配成员。', 'warning')
        return redirect(url_for('members.index'))
    dept_count = Department.query.count()
    if dept_count <= 1:
        flash('至少保留一个分组', 'warning')
        return redirect(url_for('members.index'))
    name = group.name
    db.session.delete(group)
    db.session.commit()
    flash(f'分组「{name}」已删除', 'info')
    return redirect(url_for('members.index'))
