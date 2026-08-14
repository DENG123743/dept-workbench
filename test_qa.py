"""
QA / Suggestion 板块权限与功能完整测试
--------------------------------------
覆盖范围：
  [答疑板块]  列表 / 详情 / 提问 / 回复 / 标记已解决 / 删除
  [建议模块]  提交建议 / 建议管理页访问控制 / 采纳 / 忽略 / 处理中 / 管理员回复
  [侧边栏]    管理员 vs 成员 导航可见性

运行方式：
  python test_qa.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User, Topic, Reply


class QATestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def setUp(self):
        self.client = self.app.test_client()
        # 每次清理 topics / replies 表，保留 users
        Reply.query.delete()
        Topic.query.delete()
        db.session.commit()

        self.admin = User.query.filter_by(username='admin').first()
        self.member = User.query.filter_by(username='member1').first()
        self.other = User.query.filter_by(username='member2').first()
        if not all([self.admin, self.member, self.other]):
            self.skipTest('测试数据不完整，请先初始化数据库')

    # ── 工具方法 ────────────────────────────────────────────────────

    def login_as_admin(self):
        return self.client.post('/login', data={
            'username': 'admin', 'password': 'admin123',
        }, follow_redirects=True)

    def login_as_member(self):
        return self.client.post('/login', data={
            'username': 'member1', 'password': 'member123',
        }, follow_redirects=True)

    def create_qa_topic(self, author_id, title='测试问题', content='测试内容'):
        t = Topic(title=title, content=content, category='qa',
                  status='open', author_id=author_id)
        db.session.add(t)
        db.session.commit()
        return t

    def create_suggestion(self, author_id, title='测试建议', content='建议内容'):
        t = Topic(title=title, content=content, category='suggestion',
                  status='open', author_id=author_id)
        db.session.add(t)
        db.session.commit()
        return t

    # ===============================================================
    # 一、侧边栏可见性
    # ===============================================================

    def test_sidebar_member_sees_qa_not_suggestion(self):
        self.login_as_member()
        h = self.client.get('/', follow_redirects=True).get_data(as_text=True)
        self.assertIn('答疑板块', h)
        self.assertNotIn('建议管理', h)

    def test_sidebar_admin_sees_both(self):
        self.login_as_admin()
        h = self.client.get('/', follow_redirects=True).get_data(as_text=True)
        self.assertIn('答疑板块', h)
        self.assertIn('建议管理', h)

    # ===============================================================
    # 二、答疑板块 —— 全员可访问
    # ===============================================================

    def test_qa_index_requires_login(self):
        r = self.client.get('/qa', follow_redirects=False)
        self.assertIn(r.status_code, (301, 302))
        self.assertIn('login', r.headers.get('Location', '').lower())

    def test_qa_index_member_ok(self):
        self.login_as_member()
        r = self.client.get('/qa')
        self.assertEqual(r.status_code, 200)
        self.assertIn('发起提问', r.get_data(as_text=True))

    def test_qa_index_admin_ok(self):
        self.login_as_admin()
        self.assertEqual(self.client.get('/qa').status_code, 200)

    def test_qa_detail_member_ok(self):
        self.login_as_member()
        t = self.create_qa_topic(self.admin.id)
        r = self.client.get(f'/qa/{t.id}')
        self.assertEqual(r.status_code, 200)

    def test_qa_detail_404_wrong_category(self):
        """用 suggestion 的 id 访问 qa 详情 → 404"""
        self.login_as_member()
        s = self.create_suggestion(self.admin.id)
        r = self.client.get(f'/qa/{s.id}')
        self.assertEqual(r.status_code, 404)

    # ── 发起提问 ──

    def test_qa_create_member_ok(self):
        self.login_as_member()
        r = self.client.post('/qa/create', data={
            'title': '我的问题', 'content': '详细描述',
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        t = Topic.query.filter_by(title='我的问题').first()
        self.assertIsNotNone(t)
        self.assertEqual(t.category, 'qa')
        self.assertEqual(t.author_id, self.member.id)
        self.assertEqual(t.status, 'open')

    def test_qa_create_empty_title_rejected(self):
        self.login_as_member()
        before = Topic.query.count()
        r = self.client.post('/qa/create', data={'title': '', 'content': 'x'},
                             follow_redirects=True)
        after = Topic.query.count()
        self.assertEqual(before, after)
        self.assertEqual(r.status_code, 200)

    def test_qa_create_empty_content_rejected(self):
        self.login_as_member()
        before = Topic.query.count()
        self.client.post('/qa/create', data={'title': 'x', 'content': ''})
        self.assertEqual(before, Topic.query.count())

    # ── 回复 ──

    def test_qa_reply_member_is_not_official(self):
        self.login_as_member()
        t = self.create_qa_topic(self.admin.id)
        r = self.client.post(f'/qa/{t.id}/reply', data={
            'content': '成员回复',
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        reply = Reply.query.filter_by(topic_id=t.id).first()
        self.assertIsNotNone(reply)
        self.assertFalse(reply.is_official)

    def test_qa_reply_admin_is_official_and_triggers_processing(self):
        self.login_as_admin()
        t = self.create_qa_topic(self.member.id)
        self.assertEqual(t.status, 'open')
        self.client.post(f'/qa/{t.id}/reply', data={'content': '官方答复'},
                         follow_redirects=True)
        reply = Reply.query.filter_by(topic_id=t.id).first()
        self.assertTrue(reply.is_official)
        db.session.refresh(t)
        self.assertEqual(t.status, 'processing')

    def test_qa_reply_empty_rejected(self):
        self.login_as_member()
        t = self.create_qa_topic(self.admin.id)
        before = Reply.query.count()
        self.client.post(f'/qa/{t.id}/reply', data={'content': ''})
        self.assertEqual(before, Reply.query.count())

    # ── 标记已解决 ──

    def test_qa_resolve_author_ok(self):
        self.login_as_member()
        t = self.create_qa_topic(self.member.id)
        self.client.post(f'/qa/{t.id}/resolve', follow_redirects=True)
        db.session.refresh(t)
        self.assertEqual(t.status, 'resolved')

    def test_qa_resolve_admin_ok(self):
        self.login_as_admin()
        t = self.create_qa_topic(self.member.id)
        self.client.post(f'/qa/{t.id}/resolve', follow_redirects=True)
        db.session.refresh(t)
        self.assertEqual(t.status, 'resolved')

    def test_qa_resolve_other_member_forbidden(self):
        self.login_as_member()
        t = self.create_qa_topic(self.other.id)  # 别人的问题
        db.session.refresh(t)
        before_status = t.status
        self.client.post(f'/qa/{t.id}/resolve', follow_redirects=True)
        db.session.refresh(t)
        self.assertEqual(t.status, before_status)  # 状态未变

    # ── 删除 ──

    def test_qa_delete_author_ok(self):
        self.login_as_member()
        t = self.create_qa_topic(self.member.id)
        self.client.post(f'/qa/{t.id}/delete', follow_redirects=True)
        self.assertIsNone(Topic.query.get(t.id))

    def test_qa_delete_admin_ok(self):
        self.login_as_admin()
        t = self.create_qa_topic(self.member.id)
        self.client.post(f'/qa/{t.id}/delete', follow_redirects=True)
        self.assertIsNone(Topic.query.get(t.id))

    def test_qa_delete_other_member_forbidden(self):
        self.login_as_member()
        t = self.create_qa_topic(self.other.id)
        self.client.post(f'/qa/{t.id}/delete', follow_redirects=True)
        self.assertIsNotNone(Topic.query.get(t.id))

    # ===============================================================
    # 三、建议模块 —— 仅管理员可见/处理，成员可提交
    # ===============================================================

    # ── 管理页访问控制 ──

    def test_suggestions_index_admin_ok(self):
        self.login_as_admin()
        self.create_suggestion(self.member.id, 'A', 'B')
        r = self.client.get('/qa/suggestions')
        self.assertEqual(r.status_code, 200)
        self.assertIn('A', r.get_data(as_text=True))

    def test_suggestions_index_member_403(self):
        self.login_as_member()
        r = self.client.get('/qa/suggestions')
        self.assertEqual(r.status_code, 403)

    def test_suggestions_index_unauth_redirect(self):
        r = self.client.get('/qa/suggestions')
        self.assertIn(r.status_code, (301, 302))

    # ── 成员提交建议 ──

    def test_suggestion_submit_member_ok(self):
        self.login_as_member()
        before = Topic.query.filter_by(category='suggestion').count()
        r = self.client.post('/qa/suggestion/submit', data={
            'title': '希望加个深色模式',
            'content': '晚上看屏幕太刺眼',
            'priority': 'high',
        }, follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        after = Topic.query.filter_by(category='suggestion').count()
        self.assertEqual(after, before + 1)
        s = Topic.query.filter_by(title='希望加个深色模式').first()
        self.assertIsNotNone(s)
        self.assertEqual(s.author_id, self.member.id)
        self.assertEqual(s.status, 'open')

    def test_suggestion_submit_empty_rejected(self):
        self.login_as_member()
        before = Topic.query.filter_by(category='suggestion').count()
        self.client.post('/qa/suggestion/submit', data={'title': '', 'content': 'x'})
        self.client.post('/qa/suggestion/submit', data={'title': 'x', 'content': ''})
        self.assertEqual(before, Topic.query.filter_by(category='suggestion').count())

    # ── 管理员采纳 / 忽略 / 处理中 ──

    def test_suggestion_action_accept(self):
        self.login_as_admin()
        s = self.create_suggestion(self.member.id, 'S1', 'C1')
        self.client.post(f'/qa/suggestion/{s.id}/accept', follow_redirects=True)
        db.session.refresh(s)
        self.assertEqual(s.status, 'resolved')

    def test_suggestion_action_reject(self):
        self.login_as_admin()
        s = self.create_suggestion(self.member.id, 'S2', 'C2')
        self.client.post(f'/qa/suggestion/{s.id}/reject', follow_redirects=True)
        db.session.refresh(s)
        self.assertEqual(s.status, 'rejected')

    def test_suggestion_action_processing(self):
        self.login_as_admin()
        s = self.create_suggestion(self.member.id, 'S3', 'C3')
        self.client.post(f'/qa/suggestion/{s.id}/processing', follow_redirects=True)
        db.session.refresh(s)
        self.assertEqual(s.status, 'processing')

    def test_suggestion_action_member_403(self):
        self.login_as_member()
        s = self.create_suggestion(self.member.id, 'S4', 'C4')
        for action in ('accept', 'reject', 'processing'):
            r = self.client.post(f'/qa/suggestion/{s.id}/{action}')
            self.assertEqual(r.status_code, 403, f'action={action}')

    def test_suggestion_action_wrong_topic_type_404(self):
        """对 qa 类型的 topic 调 suggestion_action → 404"""
        self.login_as_admin()
        t = self.create_qa_topic(self.member.id, 'Q', 'Q')
        r = self.client.post(f'/qa/suggestion/{t.id}/accept')
        self.assertEqual(r.status_code, 404)

    # ── 管理员回复建议 ──

    def test_suggestion_reply_admin_ok(self):
        self.login_as_admin()
        s = self.create_suggestion(self.member.id, 'S5', 'C5')
        self.client.post(f'/qa/suggestion/{s.id}/reply', data={
            'content': '我们采纳这个建议',
        }, follow_redirects=True)
        reply = Reply.query.filter_by(topic_id=s.id).first()
        self.assertIsNotNone(reply)
        self.assertTrue(reply.is_official)
        self.assertEqual(reply.author_id, self.admin.id)

    def test_suggestion_reply_member_403(self):
        self.login_as_member()
        s = self.create_suggestion(self.member.id, 'S6', 'C6')
        r = self.client.post(f'/qa/suggestion/{s.id}/reply', data={'content': 'no'})
        self.assertEqual(r.status_code, 403)

    def test_suggestion_reply_empty_rejected(self):
        self.login_as_admin()
        s = self.create_suggestion(self.member.id, 'S7', 'C7')
        before = Reply.query.count()
        self.client.post(f'/qa/suggestion/{s.id}/reply', data={'content': ''})
        self.assertEqual(before, Reply.query.count())

    # ── 按状态筛选 ──

    def test_suggestions_filter_by_status(self):
        self.login_as_admin()
        self.create_suggestion(self.member.id, '待处理', 'x')
        s2 = self.create_suggestion(self.member.id, '已解决', 'x')
        s2.status = 'resolved'
        db.session.commit()
        r = self.client.get('/qa/suggestions?status=resolved')
        h = r.get_data(as_text=True)
        self.assertIn('已解决', h)
        self.assertNotIn('待处理', h)


if __name__ == '__main__':
    unittest.main(verbosity=2)
