"""清掉指定單的處理結果（恢復成未填寫）。只在老闆要求時用。
用法：python tools/clear_results.py id1 id2 ...
"""
import json, os, re, sys, urllib.request

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
api = re.search(r'api:\s*"([^"]+)"', open(os.path.join(root, 'config.js'), encoding='utf-8').read()).group(1)
key = open(os.path.join(root, 'admin.key'), encoding='utf-8').read().strip()
body = json.dumps({'action': 'delete_results', 'key': key, 'ids': sys.argv[1:]}).encode('utf-8')
req = urllib.request.Request(api, data=body, method='POST', headers={'Content-Type': 'text/plain;charset=utf-8'})
with urllib.request.urlopen(req, timeout=120) as r:
    print(r.read().decode('utf-8'))
j = json.load(urllib.request.urlopen(api, timeout=60))
print('results left:', len(j['results']), [x['id'] for x in j['results']])
