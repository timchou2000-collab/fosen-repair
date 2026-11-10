"""把「處理過」的追房任務移出追房表（老闆 2026-11-10 規則）。
處理過＝狀態「已完成」或「無法處理」。移出條件（二選一）：
  1. 標成處理過滿 10 天（以處理結果的時間 at、台灣日期計）→ 每天評價專員巡查時自動移出
  2. 老闆同意 → 用 --ids 指定（只接受處理過的任務；未處理/處理中的會拒絕）
移出時：先把任務＋處理結果寫進封存檔（不進這個公開 repo），再刪 complaints 與 results 兩邊
（results 也刪，以免同一個 id 之後重新立項時沿用舊的「已完成」）。

用法：
  python tools/cleanup_closed.py                 # 只列出（不刪）
  python tools/cleanup_closed.py --apply         # 刪掉滿 10 天的
  python tools/cleanup_closed.py --ids r-307,r-506 --apply   # 老闆同意提早移出
"""
import argparse, csv, datetime as dt, json, os, re, urllib.request

KEEP_DAYS = 10
CLOSED = {'已完成', '無法處理'}
TW = dt.timezone(dt.timedelta(hours=8))
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--ids', default='')
ap.add_argument('--archive', default=r'D:\AI\code\SM_control\fosen_officer\review_watch\tracker_archive.csv')
a = ap.parse_args()

api = re.search(r'api:\s*"([^"]+)"', open(os.path.join(root, 'config.js'), encoding='utf-8').read()).group(1)
key = open(os.path.join(root, 'admin.key'), encoding='utf-8').read().strip()
j = json.load(urllib.request.urlopen(api, timeout=60))
res = {r['id']: r for r in j['results']}
today = dt.datetime.now(TW).date()


def tw_date(iso):
    try:
        return dt.datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(TW).date()
    except Exception:
        return None


def ymd(s):
    try:
        return dt.date.fromisoformat(s.strip())
    except Exception:
        return None


want = {x.strip() for x in a.ids.split(',') if x.strip()}
picked, keep = [], []
for c in j['complaints']:
    r = res.get(c['id'], {})
    st = r.get('status', '未處理')
    d_done = tw_date(r.get('at', '')) if st in CLOSED else None
    since = (today - d_done).days if d_done else None
    added = ymd(c.get('added', ''))
    row = dict(c, status=st, note=r.get('note', ''), by=r.get('by', ''), at=r.get('at', ''),
               days_open=(d_done - added).days if (d_done and added) else '',
               days_since_closed=since if since is not None else '')
    if c['id'] in want:
        if st not in CLOSED:
            print(f'拒絕 {c["id"]}（{c["room"]}）：狀態「{st}」還沒處理完，不能移出')
            continue
        row['reason'] = '老闆同意'
        picked.append(row)
    elif st in CLOSED and since is not None and since >= KEEP_DAYS:
        row['reason'] = f'處理後滿 {KEEP_DAYS} 天'
        picked.append(row)
    elif st in CLOSED:
        keep.append(row)
missing = want - {c['id'] for c in j['complaints']}
for m in sorted(missing):
    print(f'找不到 {m}')

print(f'今天 {today}；要移出 {len(picked)} 筆：')
for p in picked:
    print(f'  {p["id"]}｜{p["room"]}｜{p["status"]}｜{p["reason"]}｜處理於 {p["at"][:10]}')
print(f'處理過但還沒滿 {KEEP_DAYS} 天（需老闆同意才能提早移出）{len(keep)} 筆：')
for k in keep:
    print(f'  {k["id"]}｜{k["room"]}｜{k["status"]}｜已處理 {k["days_since_closed"]} 天')

if a.apply and picked:
    cols = ['removed_on', 'reason', 'id', 'priority', 'room', 'listing', 'roomType', 'category', 'complaint', 'action',
            'sources', 'latest', 'added', 'status', 'note', 'by', 'at', 'days_open']
    new = not os.path.exists(a.archive)
    with open(a.archive, 'a', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        if new:
            w.writeheader()
        for p in picked:
            w.writerow(dict(p, removed_on=str(today)))
    ids = [p['id'] for p in picked]
    for action in ('delete_complaints', 'delete_results'):
        body = json.dumps({'action': action, 'key': key, 'ids': ids}).encode('utf-8')
        req = urllib.request.Request(api, data=body, method='POST', headers={'Content-Type': 'text/plain;charset=utf-8'})
        with urllib.request.urlopen(req, timeout=120) as r:
            print(action, r.read().decode('utf-8'))
    print('已封存到', a.archive)
elif picked:
    print('（只列出；加 --apply 才會真的移出）')
