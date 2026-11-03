"""把負評待辦送到追房網頁（Apps Script 後端）。
用法：python tools/push_complaints.py items.json [--only id1,id2,...]
items.json：[{id, priority(高/中/低), room, listing, roomType, category, complaint, action, sources(換行分隔), latest(YYYY-MM-DD), added}]
--only：只送指定 id（老闆評估後核准的那幾筆）。同 id 會覆蓋（用來更新）。
管理金鑰放在 repo 根目錄 admin.key（不進 git）；網址取自 config.js。
"""
import argparse, json, os, re, urllib.request

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument('items')
ap.add_argument('--only', default='')
a = ap.parse_args()
api = re.search(r'api:\s*"([^"]+)"', open(os.path.join(root, 'config.js'), encoding='utf-8').read()).group(1)
key = open(os.path.join(root, 'admin.key'), encoding='utf-8').read().strip()
items = json.load(open(a.items, encoding='utf-8'))
if a.only:
    want = [x.strip() for x in a.only.split(',') if x.strip()]
    missing = [x for x in want if x not in {i['id'] for i in items}]
    if missing:
        raise SystemExit('找不到這些 id：' + ', '.join(missing))
    items = [i for i in items if i['id'] in want]
body = json.dumps({'action': 'upsert_complaints', 'key': key, 'items': items}, ensure_ascii=False).encode('utf-8')
req = urllib.request.Request(api, data=body, method='POST', headers={'Content-Type': 'text/plain;charset=utf-8'})
with urllib.request.urlopen(req, timeout=120) as r:
    print(r.read().decode('utf-8'), 'sent:', ', '.join(i['id'] for i in items))
