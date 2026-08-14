from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Notice
from decorators import admin_required

bp = Blueprint('notices', __name__)


@bp.route('/')
@login_required
def index():
    notices = Notice.query.order_by(
        Notice.is_top.desc(),
        Notice.created_at.desc()
    ).all()
    return render_template('notices/index.html', notices=notices)


@bp.route('/create', methods=['POST'])
@admin_required
def create():
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    if not title or not content:
        flash('标题和内容不能为空', 'danger')
        return redirect(url_for('notices.index'))

    notice = Notice(
        title=title,
        content=content,
        priority=request.form.get('priority', 'normal'),
        is_top=bool(request.form.get('is_top')),
        author_id=current_user.id,
    )
    db.session.add(notice)
    db.session.commit()
    flash('公告发布成功', 'success')
    return redirect(url_for('notices.index'))


@bp.route('/<int:notice_id>/toggle', methods=['POST'])
@admin_required
def toggle_top(notice_id):
    notice = Notice.query.get_or_404(notice_id)
    notice.is_top = not notice.is_top
    db.session.commit()
    flash('已更新置顶状态', 'info')
    return redirect(url_for('notices.index'))


@bp.route('/<int:notice_id>/delete', methods=['POST'])
@admin_required
def delete(notice_id):
    notice = Notice.query.get_or_404(notice_id)
    db.session.delete(notice)
    db.session.commit()
    flash('公告已删除', 'info')
    return redirect(url_for('notices.index'))
