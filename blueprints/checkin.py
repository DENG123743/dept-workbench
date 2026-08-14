import secrets
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Meeting, CheckIn, User, Department
from decorators import admin_required

bp = Blueprint('checkin', __name__)


def _new_code():
    while True:
        code = secrets.token_urlsafe(4).upper()[:6]
        if not Meeting.query.filter_by(code=code).first():
            return code


@bp.route('/')
@login_required
def index():
    meetings = Meeting.query.order_by(Meeting.meeting_time.desc()).all()
    return render_template('checkin/index.html', meetings=meetings)


@bp.route('/create', methods=['POST'])
@admin_required
def create():
    title = request.form.get('title', '').strip()
    meeting_time = request.form.get('meeting_time')
    if not title or not meeting_time:
        flash('请填写会议标题和时间', 'danger')
        return redirect(url_for('checkin.index'))

    meeting = Meeting(
        title=title,
        description=request.form.get('description', '').strip(),
        location=request.form.get('location', '').strip(),
        meeting_time=datetime.strptime(meeting_time, '%Y-%m-%dT%H:%M'),
        end_time=datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M') if request.form.get('end_time') else None,
        department_id=int(request.form['department_id']) if request.form.get('department_id') else None,
        creator_id=current_user.id,
        code=_new_code(),
        status='upcoming',
    )
    db.session.add(meeting)
    db.session.commit()
    flash(f'会议「{title}」已创建，签到码：{meeting.code}', 'success')
    return redirect(url_for('checkin.detail', meeting_id=meeting.id))


@bp.route('/<int:meeting_id>')
@login_required
def detail(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    checkins = meeting.checkins.order_by(CheckIn.check_in_time.asc()).all()
    members = User.query.all()
    present_count = len([c for c in checkins if c.status == 'present'])
    return render_template('checkin/detail.html', meeting=meeting, checkins=checkins,
                           members=members, present_count=present_count)


@bp.route('/<int:meeting_id>/open', methods=['POST'])
@admin_required
def open_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    meeting.status = 'ongoing'
    db.session.commit()
    flash('会议已开启签到', 'success')
    return redirect(url_for('checkin.detail', meeting_id=meeting.id))


@bp.route('/<int:meeting_id>/close', methods=['POST'])
@admin_required
def close_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    meeting.status = 'ended'
    db.session.commit()
    flash('会议已结束', 'info')
    return redirect(url_for('checkin.detail', meeting_id=meeting.id))


@bp.route('/<int:meeting_id>/delete', methods=['POST'])
@admin_required
def delete_meeting(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    db.session.delete(meeting)
    db.session.commit()
    flash('会议已删除', 'info')
    return redirect(url_for('checkin.index'))


@bp.route('/sign', methods=['GET', 'POST'])
def public_sign():
    code = request.args.get('code', '').upper()

    if request.method == 'POST':
        code = request.form.get('code', '').upper()
        real_name = request.form.get('real_name', '').strip()
        meeting = Meeting.query.filter_by(code=code).first()
        msg_type = 'danger'
        msg = ''

        if not meeting:
            msg, msg_type = '签到码不存在，请检查后重试', 'danger'
        elif meeting.status not in ('upcoming', 'ongoing'):
            msg, msg_type = '会议已结束，无法签到', 'warning'
        elif current_user.is_authenticated:
            if meeting.checkins.filter_by(user_id=current_user.id).first():
                msg, msg_type = '你已经签到过了，请勿重复提交', 'warning'
            else:
                checkin = CheckIn(
                    meeting_id=meeting.id,
                    user_id=current_user.id,
                    real_name=current_user.real_name or current_user.username,
                    role='member',
                )
                db.session.add(checkin)
                db.session.commit()
                msg, msg_type = f'✅ 签到成功！欢迎「{checkin.real_name}」', 'success'
        elif real_name:
            checkin = CheckIn(
                meeting_id=meeting.id,
                real_name=real_name,
                role='guest',
            )
            db.session.add(checkin)
            db.session.commit()
            msg, msg_type = f'✅ 签到成功！欢迎「{checkin.real_name}」', 'success'
        else:
            msg, msg_type = '请填写真实姓名或先登录', 'danger'

        meeting = Meeting.query.filter_by(code=code).first() if code else None
        return render_template('checkin/public_sign.html',
                               code=code, meeting=meeting,
                               flash_msg=msg, flash_type=msg_type)

    meeting = Meeting.query.filter_by(code=code).first() if code else None
    return render_template('checkin/public_sign.html', code=code, meeting=meeting)


@bp.route('/api/<int:meeting_id>/checkins')
@login_required
def api_checkins(meeting_id):
    meeting = Meeting.query.get_or_404(meeting_id)
    data = [
        {
            'id': c.id,
            'name': c.real_name,
            'role': c.role,
            'time': c.check_in_time.strftime('%H:%M:%S'),
            'status': c.status,
        }
        for c in meeting.checkins.order_by(CheckIn.check_in_time.asc()).all()
    ]
    return jsonify({'checkins': data, 'total': len(data),
                    'present': len([d for d in data if d['status'] == 'present'])})
