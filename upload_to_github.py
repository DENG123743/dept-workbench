"""
直接调 GitHub API 上传文件（不需要 Git）
============================================

使用方法：
1. 在 GitHub 生成一个 Token（见脚本底部注释）
2. 把 TOKEN 填到下面
3. 运行：python upload_to_github.py
"""
import os
import sys
import base64
import json
import time
import requests

# ══════════════════════════════════════════════════════
# 配置区（只改这两行）
# ══════════════════════════════════════════════════════
TOKEN = ""          # 你的 GitHub Token，例如 "ghp_xxxxxxxxxxxxxxxx"
OWNER = "DENG123743"
REPO  = "dept-workbench"
BRANCH = "main"
# ══════════════════════════════════════════════════════

WORKDIR = os.path.dirname(os.path.abspath(__file__))

EXCLUDE_DIRS = {'venv', '__pycache__', '.git', '.idea', '.vscode', 'uploads'}
EXCLUDE_FILES = {
    'deploy.py', 'tunnel.py', '_mkzip.py', '_check_zip.py',
}
EXCLUDE_EXTS = {'.pyc', '.db', '.zip', '.db-journal'}


def collect_files():
    files = []
    for root, dirs, filenames in os.walk(WORKDIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]
        for f in filenames:
            if f in EXCLUDE_FILES:
                continue
            _, ext = os.path.splitext(f)
            if ext in EXCLUDE_EXTS:
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, WORKDIR).replace('\\', '/')
            if rel.startswith('.'):
                continue
            files.append((rel, full))
    return sorted(files)


def upload_file(session, path, local_path):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    with open(local_path, 'rb') as f:
        raw = f.read()

    # GitHub contents API 要求 1-100MB，base64 后不能含 null
    b64 = base64.b64encode(raw).decode('utf-8')

    # 检查文件是否已存在（拿 sha 用于 update）
    sha = None
    try:
        r = session.get(url, headers=headers, params={'ref': BRANCH}, timeout=15)
        if r.status_code == 200:
            sha = r.json().get('sha')
    except Exception:
        pass

    payload = {
        "message": f"{'更新' if sha else '添加'} {path}",
        "content": b64,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha

    r = session.put(url, headers=headers, json=payload, timeout=30)

    if r.status_code in (200, 201):
        return True, r.json().get('content', {}).get('html_url', '')
    else:
        return False, r.text


def main():
    if not TOKEN:
        print("❌ 请先在脚本顶部填写 TOKEN")
        print()
        print("生成 Token 步骤：")
        print("  1. 打开 https://github.com/settings/tokens")
        print("  2. 点 'Generate new token' → 选 'Generate new token (classic)'")
        print("     或者选 'Generate new token (fine-grained)'")
        print("  3. Note 随便填，Expiration 选 90 天就行")
        print("  4. 权限选 'repo'（完整仓库访问）")
        print("  5. 点 Generate token → 复制那个 ghp_ 开头的字符串")
        sys.exit(1)

    files = collect_files()
    print(f"📦 待上传 {len(files)} 个文件")
    print(f"📍 仓库  https://github.com/{OWNER}/{REPO}")
    print()

    session = requests.Session()
    ok_count = 0
    fail_count = 0

    for i, (path, local) in enumerate(files, 1):
        status, detail = upload_file(session, path, local)
        icon = "✅" if status else "❌"
        print(f"  [{i}/{len(files)}] {icon} {path}")
        if not status:
            print(f"        错误: {detail[:200]}")
            fail_count += 1
        else:
            ok_count += 1
        time.sleep(0.3)  # 避免触发 GitHub API 限速

    print()
    print(f"🎉 上传完成！成功 {ok_count} 个，失败 {fail_count} 个")
    print(f"🔗 仓库地址: https://github.com/{OWNER}/{REPO}")
    print()
    if ok_count > 0:
        print("👉 接下来去 Zeabur: https://zeabur.com → Import 这个仓库 → Deploy")


if __name__ == '__main__':
    main()
