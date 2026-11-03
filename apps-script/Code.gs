/**
 * 丰森負評追房表 — Google Apps Script 後端
 * 綁在 Google 試算表「丰森追房資料（網頁後台）」上（擴充功能 → Apps Script）。
 * 第一次：執行 setup() 一次，再「部署 → 新增部署 → 網頁應用程式（存取權：任何人）」。
 *
 * 分頁：
 *   complaints 負評待辦（評價專員用管理金鑰新增）
 *   results    處理結果（房務主管在網頁上填）
 *   設定       B1＝填寫密碼 PIN（空白＝不用密碼）、B2＝管理金鑰
 */
const SH_C = 'complaints';
const SH_R = 'results';
const SH_S = '設定';
const HEAD_C = ['id', 'priority', 'room', 'listing', 'roomType', 'category', 'complaint', 'action', 'sources', 'latest', 'added'];
const HEAD_R = ['id', 'status', 'note', 'by', 'at'];
const STATUS = ['未處理', '處理中', '已完成', '無法處理'];

function setup() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  ensure_(ss, SH_C, HEAD_C);
  ensure_(ss, SH_R, HEAD_R);
  let s = ss.getSheetByName(SH_S);
  if (!s) {
    s = ss.insertSheet(SH_S);
    s.getRange('A1:A3').setValues([['填寫密碼（PIN）'], ['管理金鑰（評價專員用，勿外流）'], ['說明']]);
    s.getRange('B1:B3').setNumberFormat('@').setValues([
      [String(1000 + Math.floor(Math.random() * 9000))],
      [Utilities.getUuid()],
      ['PIN 可以直接改，存檔後網頁立即生效；B1 清空＝不用密碼']
    ]);
    s.setColumnWidth(1, 260); s.setColumnWidth(2, 340);
  }
  const first = ss.getSheets()[0];
  if (first.getName() !== SH_C && first.getLastRow() === 0 && ss.getSheets().length > 3) ss.deleteSheet(first);
}

function ensure_(ss, name, head) {
  let s = ss.getSheetByName(name);
  if (!s) {
    s = ss.insertSheet(name);
    s.getRange('A:Z').setNumberFormat('@');
    s.getRange(1, 1, 1, head.length).setValues([head]);
    s.setFrozenRows(1);
  }
  return s;
}

function sheet_(name) { return SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name); }

function cfg_() {
  const v = sheet_(SH_S).getRange('B1:B2').getDisplayValues();
  return { pin: String(v[0][0]).trim(), key: String(v[1][0]).trim() };
}

function rows_(name) {
  const v = sheet_(name).getDataRange().getDisplayValues();
  const h = v.shift() || [];
  return v.filter(r => r[0]).map(r => {
    const o = {};
    h.forEach((k, i) => { o[k] = r[i]; });
    return o;
  });
}

function safe_(x) {
  const s = x == null ? '' : String(x);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function upsert_(name, obj) {
  const s = sheet_(name);
  const v = s.getDataRange().getDisplayValues();
  const h = v[0];
  const row = h.map(k => safe_(obj[k]));
  const i = v.findIndex((r, ix) => ix > 0 && r[0] === String(obj.id));
  if (i > 0) s.getRange(i + 1, 1, 1, h.length).setValues([row]);
  else s.getRange(s.getLastRow() + 1, 1, 1, h.length).setValues([row]);
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

function doGet() {
  const c = cfg_();
  return out_({ ok: true, needPin: !!c.pin, complaints: rows_(SH_C), results: rows_(SH_R) });
}

function doPost(e) {
  let b;
  try { b = JSON.parse(e.postData.contents); } catch (x) { return out_({ ok: false, error: 'bad_json' }); }
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const c = cfg_();
    if (b.action === 'result') {
      if (c.pin && String(b.pin || '').trim() !== c.pin) return out_({ ok: false, error: 'bad_pin' });
      if (STATUS.indexOf(b.status) < 0) return out_({ ok: false, error: 'bad_status' });
      if (!rows_(SH_C).some(r => r.id === String(b.id))) return out_({ ok: false, error: 'no_such_item' });
      upsert_(SH_R, {
        id: String(b.id), status: b.status,
        note: String(b.note || '').slice(0, 1000),
        by: String(b.by || '').slice(0, 40),
        at: new Date().toISOString()
      });
      return out_({ ok: true });
    }
    if (b.action === 'upsert_complaints') {
      if (!c.key || b.key !== c.key) return out_({ ok: false, error: 'bad_key' });
      const items = Array.isArray(b.items) ? b.items : [];
      items.forEach(it => { if (it && it.id) upsert_(SH_C, it); });
      return out_({ ok: true, n: items.length });
    }
    if (b.action === 'check_pin') {
      return out_({ ok: !c.pin || String(b.pin || '').trim() === c.pin });
    }
    return out_({ ok: false, error: 'bad_action' });
  } finally {
    lock.releaseLock();
  }
}
