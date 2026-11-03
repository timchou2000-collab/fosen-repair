"""把負評待辦送到追房表（Apps Script 後端）。
用法：python tools/push_complaints.py items.json
items.json：[{id, priority(高/中/低), room, listing, roomType, category, complaint, action, sources(換行分隔), latest(YYYY-MM-DD), added}]
同 id 會覆蓋（用來更新）。管理金鑰放在 repo 根目錄 admin.key（不進 git）；網址取自 config.js。
"""
import json, os, re, sys, urllib.request

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
api = re.search(r'api:\s*"([^"]+)"', open(os.path.join(root, 'config.js'), encoding='utf-8').read()).group(1)
key = open(os.path.join(root, 'admin.key'), encoding='utf-8').read().strip()
items = json.load(open(sys.argv[1], encoding='utf-8'))
body = json.dumps({'action': 'upsert_complaints', 'key': key, 'items': items}, ensure_ascii=False).encode('utf-8')
req = urllib.request.Request(api, data=body, method='POST', headers={'Content-Type': 'text/plain;charset=utf-8'})
with urllib.request.urlopen(req, timeout=120) as r:
    print(r.read().decode('utf-8'))
