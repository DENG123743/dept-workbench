from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models import db, Topic, Reply

bp = Blueprint('qa', __name__)


@bp.route('/suggestions')
@login_required
def suggestions():
    if not current_user.is_admin:
        return abort(403)
    status_filter = request.args.get('status', '')
    query = Topic.query.filter_by(category='suggestion')
    if status_filter:
        query = query.filter_by(status=status_filter)
    topics = query.order_by(Topic.created_at.desc()).all()
    topic_replies_map = {t.id: t.replies.order_by(Reply.created_at.asc()).all() for t in topics}
    return render_template('qa/suggestions.html', topics=topics,
                           statuses=Topic.STATUSES, current_status=status_filter,
                           topic_replies_map=topic_replies_map)


@bp.route('')
@login_required
def qa_list():
    status_filter = request.args.get('status', '')
    query = Topic.query.filter_by(category='qa')
    if status_filter:
        query = query.filter_by(status=status_filter)
    topics = query.order_by(Topic.updated_at.desc()).all()
    return render_template('qa/qa_list.html', topics=topics,
                           statuses=Topic.STATUSES, current_status=status_filter)


@bp.route('/<int:topic_id>')
@login_required
def qa_detail(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if topic.category != 'qa':
        abort(404)
    return render_template('qa/qa_detail.html', topic=topic, replies=topic.replies.order_by(Reply.created_at.asc()).all())


@bp.route('/<int:topic_id>/reply', methods=['POST'])
@login_required
def qa_reply(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    content = request.form.get('content', '').strip()
    if not content:
        flash('回复内容不能为空', 'danger')
        return redirect(url_for('qa.qa_detail', topic_id=topic_id))

    is_official = current_user.is_admin
    reply = Reply(
        topic_id=topic.id,
        content=content,
        author_id=current_user.id,
        is_official=is_official,
    )
    db.session.add(reply)

    if is_official and topic.status == 'open':
        topic.status = 'processing'

    topic.updated_at = datetime.now()
    db.session.commit()
    flash('回复已发布', 'success')
    return redirect(url_for('qa.qa_detail', topic_id=topic_id))


@bp.route('/create', methods=['POST'])
@login_required
def create_qa():
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    if not title or not content:
        flash('标题和内容均不能为空', 'danger')
        return redirect(url_for('qa.qa_list'))

    topic = Topic(
        title=title, content=content,
        category='qa', status='open',
        author_id=current_user.id,
    )
    db.session.add(topic)
    db.session.commit()
    flash('提问已发布，等待解答', 'success')
    return redirect(url_for('qa.qa_detail', topic_id=topic.id))


@bp.route('/<int:topic_id>/resolve', methods=['POST'])
@login_required
def resolve_qa(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if not (current_user.is_admin or topic.author_id == current_user.id):
        flash('无权操作', 'danger')
        return redirect(url_for('qa.qa_detail', topic_id=topic_id))
    topic.status = 'resolved'
    db.session.commit()
    flash('已标记为已解决', 'success')
    return redirect(url_for('qa.qa_detail', topic_id=topic_id))


@bp.route('/suggestion/submit', methods=['POST'])
@login_required
def submit_suggestion():
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    priority = request.form.get('priority', 'normal')
    if not title or not content:
        flash('标题和内容均不能为空', 'danger')
        return redirect(request.referrer or url_for('qa.qa_list'))

    topic = Topic(
        title=title, content=content,
        category='suggestion', status='open',
        priority=priority,
        author_id=current_user.id,
    )
    db.session.add(topic)
    db.session.commit()
    flash('建议已提交，感谢你的反馈！管理员会认真考虑', 'success')
    return redirect(request.referrer or url_for('qa.qa_list'))


@bp.route('/suggestion/<int:topic_id>/<action>', methods=['POST'])
@login_required
def suggestion_action(topic_id, action):
    if not current_user.is_admin:
        abort(403)
    topic = Topic.query.get_or_404(topic_id)
    if topic.category != 'suggestion':
        abort(404)

    if action == 'accept':
        topic.status = 'resolved'
        flash('建议已采纳', 'success')
    elif action == 'reject':
        topic.status = 'rejected'
        flash('建议已忽略', 'info')
    elif action == 'processing':
        topic.status = 'processing'
        flash('建议标记为处理中', 'info')

    db.session.commit()
    return redirect(url_for('qa.suggestions'))


@bp.route('/suggestion/<int:topic_id>/reply', methods=['POST'])
@login_required
def suggestion_reply(topic_id):
    if not current_user.is_admin:
        abort(403)
    topic = Topic.query.get_or_404(topic_id)
    content = request.form.get('content', '').strip()
    if not content:
        flash('回复内容不能为空', 'danger')
        return redirect(url_for('qa.suggestions'))

    reply = Reply(
        topic_id=topic.id,
        content=content,
        author_id=current_user.id,
        is_official=True,
    )
    db.session.add(reply)
    db.session.commit()
    flash('已回复建议', 'success')
    return redirect(url_for('qa.suggestions'))


@bp.route('/<int:topic_id>/delete', methods=['POST'])
@login_required
def delete_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if not (current_user.is_admin or topic.author_id == current_user.id):
        flash('无权删除', 'danger')
        return redirect(url_for('qa.qa_list'))
    db.session.delete(topic)
    db.session.commit()
    flash('已删除', 'info')
    if topic.category == 'suggestion':
        return redirect(url_for('qa.suggestions'))
    return redirect(url_for('qa.qa_list'))
