from flask import Blueprint, render_template
from flask_login import login_required
from models import Event, Notice, User, Department

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
def index():
    from datetime import datetime

    upcoming = Event.query.filter(Event.start_time >= datetime.now()) \
        .order_by(Event.start_time.asc()).limit(5).all()

    notices = Notice.query.order_by(
        Notice.is_top.desc(),
        Notice.created_at.desc()
    ).limit(5).all()

    stats = {
        'members': User.query.count(),
        'departments': Department.query.count(),
        'events_this_month': Event.query.filter(
            Event.start_time >= datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ).count(),
        'notices': Notice.query.count(),
    }

    return render_template('index.html',
                           upcoming_events=upcoming,
                           notices=notices,
                           stats=stats)
