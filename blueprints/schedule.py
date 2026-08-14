from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Event, Department
from decorators import admin_required

bp = Blueprint('schedule', __name__)

CATEGORIES = [
    ('meeting', '会议', '#3b82f6'),
    ('lecture', '讲座', '#8b5cf6'),
    ('prep', '筹备', '#f59e0b'),
    ('competition', '比赛', '#ef4444'),
    ('training', '培训', '#10b981'),
    ('other', '其他', '#6b7280'),
]


@bp.route('/')
@login_required
def index():
    events = Event.query.order_by(Event.start_time.desc()).all()
    departments = Department.query.all()
    return render_template('schedule/index.html', events=events,
                           categories=CATEGORIES, departments=departments)


@bp.route('/calendar')
@login_required
def calendar():
    return render_template('schedule/calendar.html')


@bp.route('/events.json')
@login_required
def events_json():
    events = Event.query.all()
    data = []
    for e in events:
        data.append({
            'id': e.id,
            'title': e.title,
            'start': e.start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'end': e.end_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'description': e.description or '',
            'location': e.location or '',
            'color': e.color or '#3b82f6',
        })
    return jsonify(data)


@bp.route('/create', methods=['POST'])
@admin_required
def create():
    title = request.form.get('title', '').strip()
    if not title:
        flash('标题不能为空', 'danger')
        return redirect(url_for('schedule.index'))

    start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
    end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
    category = request.form.get('category', 'other')
    color = dict((c[0], c[2]) for c in CATEGORIES).get(category, '#6b7280')

    event = Event(
        title=title,
        description=request.form.get('description', '').strip(),
        start_time=start_time,
        end_time=end_time,
        location=request.form.get('location', '').strip(),
        category=category,
        color=color,
        creator_id=current_user.id,
        department_id=request.form.get('department_id') or None,
    )
    db.session.add(event)
    db.session.commit()
    flash('日程创建成功', 'success')
    return redirect(url_for('schedule.calendar'))


@bp.route('/<int:event_id>/delete', methods=['POST'])
@admin_required
def delete(event_id):
    event = Event.query.get_or_404(event_id)
    if not (current_user.is_admin or event.creator_id == current_user.id):
        flash('无权删除', 'danger')
        return redirect(url_for('schedule.index'))
    db.session.delete(event)
    db.session.commit()
    flash('日程已删除', 'info')
    return redirect(url_for('schedule.index'))
