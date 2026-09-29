#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exact Verkoopkansen Tool

Werkwijze:
  1. Klik 'Open Exact'  -> browser opent, log in en ga ZELF naar de juiste administratie
                           (en eventueel direct naar de suspects-lijst die je wilt verwerken).
  2. Klik 'START'       -> de tool pakt de lijst in de huidige administratie en maakt voor
                           elk bedrijf een verkoopkans aan, slaat op en controleert of het gelukt is.

Alles wat de tool doet wordt bewaard:
  - logs/<datum_tijd>.log          volledige log van elke run
  - logs/fout_<...>.png / .html    screenshot + pagina bij een mislukt bedrijf
  - verwerkt.json                  welke bedrijven al een verkoopkans hebben (per titel),
                                   zodat een nieuwe run die overslaat
"""
import sys, os, re, json, threading, queue, glob, webbrowser, time, asyncio
from datetime import datetime
from urllib.parse import urlparse, parse_qs

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except: pass

from flask import Flask, render_template_string, request, jsonify, Response

# Wanneer bevroren als .app (Mac) zit de binary in ExactTool.app/Contents/MacOS/
# Data bestanden staan naast de .app, dus 3 niveaus omhoog
if getattr(sys, 'frozen', False):
    if sys.platform == 'darwin':
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(sys.executable))))
    else:
        BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Waar de tool zijn eigen bestanden bewaart (sessie, logs, verwerkt.json).
# Als Mac-app in /Programma's mag je daar niet schrijven -> ~/Documents/ExactTool
if getattr(sys, 'frozen', False) and sys.platform == 'darwin':
    DATA_DIR = os.path.join(os.path.expanduser('~'), 'Documents', 'ExactTool')
else:
    DATA_DIR = BASE_DIR
os.makedirs(DATA_DIR, exist_ok=True)

# Mac-app zonder terminal: uitvoer naar een bestand i.p.v. nergens heen
if sys.stdout is None or sys.stderr is None:
    _uit = open(os.path.join(DATA_DIR, 'app_uitvoer.log'), 'a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stdout or _uit
    sys.stderr = sys.stderr or _uit

SESSIE        = os.path.join(DATA_DIR, 'browser_sessie')
BROWSERS_DIR  = os.path.join(BASE_DIR, '_browsers')
LOG_DIR       = os.path.join(DATA_DIR, 'logs')
VERWERKT_FILE = os.path.join(DATA_DIR, 'verwerkt.json')
BASE_URL      = 'https://start.exactonline.nl'
PORT          = 5050

# Windows: browsers staan in _browsers naast de app. Mac: standaard Playwright-map
# (~/Library/Caches/ms-playwright). PyInstaller zet deze variabele zelf op '0'
# (= browser ín de app zoeken), dat overschrijven we hier bewust.
if os.path.isdir(BROWSERS_DIR):
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = BROWSERS_DIR
elif getattr(sys, 'frozen', False):
    if sys.platform == 'darwin':
        _pw = os.path.join(os.path.expanduser('~'), 'Library', 'Caches', 'ms-playwright')
    elif sys.platform == 'win32':
        _pw = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'ms-playwright')
    else:
        _pw = os.path.join(os.path.expanduser('~'), '.cache', 'ms-playwright')
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = _pw

app   = Flask(__name__)
state = {
    'browser_open': False,
    'running': False,
    'stop': False,
    'cmd_queue': queue.Queue(),
    'subscribers': [],
    'history': [],
    'bedrijven_info': {},
    'json_naam': '',
    'logfile': None,
}
state_lock = threading.Lock()

# ── Standaard JSON laden ──────────────────────────────────────────────────────
default_json = next((p for p in [
    os.path.join(DATA_DIR, 'bedrijven_data.json'),
    os.path.join(BASE_DIR, 'bedrijven_data.json'),
    os.path.join(getattr(sys, '_MEIPASS', BASE_DIR), 'bedrijven_data.json'),
] if os.path.exists(p)), None)
if default_json:
    with open(default_json, encoding='utf-8') as _f:
        _d = json.load(_f)
    state['bedrijven_info'] = _d.get('info', _d)
    state['json_naam'] = os.path.basename(default_json)


# ════════════════════════════════════════════════════════════════════════════
# Berichten naar de webpagina + logbestand
# ════════════════════════════════════════════════════════════════════════════

def publish(item):
    with state_lock:
        if item.get('type') == 'log':
            state['history'].append(item)
            del state['history'][:-500]
        for q in list(state['subscribers']):
            q.put(item)


def log(tekst):
    ts = datetime.now().strftime('%H:%M:%S')
    try: print(f'[{ts}] {tekst}', flush=True)
    except: pass   # Mac-app zonder terminal
    if state['logfile']:
        try:
            with open(state['logfile'], 'a', encoding='utf-8') as f:
                f.write(f'[{ts}] {tekst}\n')
        except: pass
    publish({'type': 'log', 'text': tekst, 'ts': ts})


def push_state():
    publish({'type': 'state', 'browser_open': state['browser_open'], 'running': state['running']})


def laad_verwerkt():
    try:
        with open(VERWERKT_FILE, encoding='utf-8') as f:
            return json.load(f)
    except: return {}


def bewaar_verwerkt(data):
    tmp = VERWERKT_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, VERWERKT_FILE)


# ════════════════════════════════════════════════════════════════════════════
# HTML / CSS / JS  (single-page app)
# ════════════════════════════════════════════════════════════════════════════

PAGE = r"""<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Exact Verkoopkansen Tool</title>
<style>
  :root{
    --bg:#0d1117; --card:#161b22; --border:#21262d;
    --accent:#2f81f7; --accent2:#1f6feb;
    --green:#3fb950; --red:#f85149; --yellow:#d29922;
    --text:#e6edf3; --muted:#8b949e;
    --log-bg:#010409; --log-text:#7ee787;
    --radius:10px;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;
       min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:0 0 40px}
  .header{width:100%;background:var(--card);border-bottom:3px solid var(--accent);
          padding:28px 40px 22px;margin-bottom:32px}
  .header h1{font-size:26px;font-weight:700;color:var(--accent);letter-spacing:-.3px}
  .header p{color:var(--muted);font-size:13px;margin-top:6px}
  .wrap{width:100%;max-width:700px;padding:0 20px;display:flex;flex-direction:column;gap:24px}
  .card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:22px 24px}
  .card-label{font-size:13px;font-weight:700;color:var(--text);margin-bottom:10px}
  .hint{font-size:12px;color:var(--muted);margin-top:6px;line-height:1.5}
  input[type=text], select{
    background:#0d1117;border:1px solid var(--border);color:var(--text);
    border-radius:8px;padding:10px 14px;font-size:14px;width:100%;
    outline:none;transition:border .15s;font-family:inherit}
  input[type=text]:focus, select:focus{border-color:var(--accent)}
  select{cursor:pointer;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%238b949e' stroke-width='1.5' fill='none'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center;padding-right:32px}
  .datum-row{display:flex;gap:14px}
  .datum-col{display:flex;flex-direction:column;gap:6px}
  .datum-col label{font-size:11px;color:var(--muted)}
  .datum-col select{width:auto;min-width:80px}
  .json-row{display:flex;align-items:center;gap:12px}
  .json-row input[type=text]{flex:1;color:var(--muted)}
  .json-status{font-size:12px;margin-top:8px;min-height:18px}
  #fileInput{display:none}
  .check{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text);cursor:pointer}
  .log-box{background:var(--log-bg);border:1px solid var(--border);border-radius:var(--radius);
           padding:14px 16px;height:260px;overflow-y:auto;
           font-family:'Consolas','Courier New',monospace;font-size:12px;
           color:var(--log-text);white-space:pre-wrap;word-break:break-all}
  .prog-label{font-size:12px;color:var(--muted);margin-bottom:8px}
  .prog-track{background:var(--border);border-radius:99px;height:14px;overflow:hidden}
  .prog-bar{background:var(--accent);height:100%;border-radius:99px;width:0%;transition:width .4s ease}
  .btn-row{display:flex;gap:10px}
  .btn{border:none;border-radius:10px;cursor:pointer;font-family:inherit;
       font-weight:700;transition:background .15s,transform .1s;outline:none}
  .btn:active{transform:scale(.97)}
  .btn:disabled{opacity:.4;cursor:not-allowed}
  .btn-open{flex:1;height:56px;font-size:16px;background:var(--card);color:var(--text);border:1px solid var(--accent)}
  .btn-open:hover:not(:disabled){background:#1c2330}
  .btn-start{flex:1.4;height:56px;font-size:18px;background:var(--accent);color:#fff}
  .btn-start:hover:not(:disabled){background:var(--accent2)}
  .btn-stop{width:56px;height:56px;font-size:20px;background:var(--card);color:var(--text);border:1px solid var(--border)}
  .btn-stop:hover:not(:disabled){background:var(--red);border-color:var(--red)}
  .status-bar{font-size:11px;color:var(--green);display:flex;align-items:center;gap:6px}
  .dot{width:8px;height:8px;border-radius:50%;background:var(--green);display:inline-block}
  .dot.busy{background:var(--yellow);animation:pulse 1s infinite}
  .dot.error{background:var(--red)}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
  .btn-file{background:var(--accent2);color:#fff;border:none;border-radius:8px;
            padding:10px 18px;font-size:13px;cursor:pointer;white-space:nowrap;
            font-family:inherit;font-weight:600;transition:background .15s}
  .btn-file:hover{background:var(--accent)}
</style>
</head>
<body>

<div class="header">
  <h1>⚡ Exact Verkoopkansen Tool</h1>
  <p>1. Open Exact &nbsp;→&nbsp; 2. log in en ga zelf naar de juiste administratie &nbsp;→&nbsp; 3. START</p>
</div>

<div class="wrap">

  <div>
    <div class="card-label">✏️ &nbsp;Titel verkoopkans</div>
    <input type="text" id="titel" value="belcentrum 12-05-26 Tim. S" placeholder="bijv. belcentrum 12-05-26 Tim. S">
  </div>

  <div>
    <div class="card-label">📅 &nbsp;Sluitingsdatum</div>
    <div class="datum-row">
      <div class="datum-col">
        <label>Dag</label>
        <select id="dag">{% for d in range(1,32) %}<option value="{{'{:02d}'.format(d)}}"{% if d==12 %} selected{% endif %}>{{'{:02d}'.format(d)}}</option>{% endfor %}</select>
      </div>
      <div class="datum-col">
        <label>Maand</label>
        <select id="maand">{% for m in range(1,13) %}<option value="{{'{:02d}'.format(m)}}"{% if m==5 %} selected{% endif %}>{{'{:02d}'.format(m)}}</option>{% endfor %}</select>
      </div>
      <div class="datum-col">
        <label>Jaar</label>
        <select id="jaar">{% for y in ['2025','2026','2027','2028'] %}<option{% if y=='2026' %} selected{% endif %}>{{y}}</option>{% endfor %}</select>
      </div>
    </div>
  </div>

  <div>
    <div class="card-label">🏷️ &nbsp;Fase-code</div>
    <input type="text" id="fase" value="VB" style="width:140px">
    <div class="hint">De code van de verkoopkansfase zoals die in deze administratie heet (standaard VB = Voorbereid).</div>
  </div>

  <div>
    <div class="card-label">⚡ &nbsp;Aantal vensters tegelijk</div>
    <select id="vensters" style="width:auto;min-width:90px">{% for n in range(1,11) %}<option{% if n==8 %} selected{% endif %}>{{n}}</option>{% endfor %}</select>
    <div class="hint">Meer vensters = sneller. 8 vensters doet ca. 50 klanten in 1-2 minuten.</div>
  </div>

  <div>
    <div class="card-label">👤 &nbsp;Accountmanager-code (optioneel)</div>
    <input type="text" id="rmcode" value="2107693" placeholder="leeg = alle suspects in de administratie">
    <div class="hint">Wordt alleen gebruikt als je bij START niet zelf al op een relatielijst staat.
      Sta je al op de lijst die je wilt verwerken? Dan pakt de tool precies die lijst.</div>
  </div>

  <div>
    <div class="card-label">📂 &nbsp;Bedrijvenlijst (JSON)</div>
    <div class="card">
      <div class="json-row">
        <input type="text" id="jsonNaam" readonly value="{{ json_naam or 'Geen bestand geselecteerd' }}">
        <button class="btn-file" onclick="document.getElementById('fileInput').click()">📁 Kies bestand</button>
        <input type="file" id="fileInput" accept=".json" onchange="laadJson(this)">
      </div>
      <div class="json-status" id="jsonStatus">
        {% if json_count %}<span style="color:var(--green)">✅ &nbsp;{{ json_count }} bedrijven geladen</span>{% endif %}
      </div>
      <label class="check" style="margin-top:12px">
        <input type="checkbox" id="overslaan" checked>
        Bedrijven die met deze titel al verwerkt zijn overslaan
      </label>
    </div>
  </div>

  <div>
    <div class="card-label">🖥️ &nbsp;Activiteit log <span style="color:var(--muted);font-weight:400">(wordt ook opgeslagen in de map logs)</span></div>
    <div class="log-box" id="log"></div>
  </div>

  <div class="card">
    <div class="prog-label" id="progLabel">Gereed</div>
    <div class="prog-track"><div class="prog-bar" id="progBar"></div></div>
  </div>

  <div class="btn-row">
    <button class="btn btn-open"  id="btnOpen"  onclick="openExact()">🌐&nbsp; Open Exact</button>
    <button class="btn btn-start" id="btnStart" onclick="starten()" disabled>▶&nbsp;&nbsp;START</button>
    <button class="btn btn-stop"  id="btnStop"  onclick="stoppen()" disabled>⏹</button>
  </div>

  <div style="display:flex;justify-content:space-between;align-items:center">
    <div class="status-bar">
      <span class="dot" id="dot"></span>
      <span id="statusTxt">Gereed</span>
    </div>
    <button onclick="afsluiten()" style="background:none;border:none;color:var(--muted);
      font-size:12px;cursor:pointer;padding:4px 8px;border-radius:6px;
      font-family:inherit;transition:color .15s"
      onmouseover="this.style.color='var(--red)'"
      onmouseout="this.style.color='var(--muted)'">
      ✕ &nbsp;App afsluiten
    </button>
  </div>

</div>

<script>
let jsonLoaded = {{ 'true' if json_count else 'false' }};
let browserOpen = false, running = false;

function addLog(txt, ts){
  const box = document.getElementById('log');
  ts = ts || new Date().toLocaleTimeString('nl-NL');
  box.textContent += `[${ts}]  ${txt}\n`;
  box.scrollTop = box.scrollHeight;
}

function setStatus(txt, type='ok'){
  document.getElementById('statusTxt').textContent = txt;
  document.getElementById('dot').className = 'dot' + (type==='busy' ? ' busy' : type==='error' ? ' error' : '');
}

function render(){
  document.getElementById('btnOpen').disabled  = browserOpen;
  document.getElementById('btnStart').disabled = !browserOpen || running;
  document.getElementById('btnStop').disabled  = !running;
  document.getElementById('btnStart').textContent = running ? '⏳  Bezig...' : '▶  START';
  if(running) setStatus('Verwerken...', 'busy');
  else if(browserOpen) setStatus('Browser open - ga naar je administratie en klik START');
  else setStatus('Gereed');
}

function laadJson(input){
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    fetch('/upload_json', {method:'POST', headers:{'Content-Type':'application/json'}, body: e.target.result})
    .then(r=>r.json()).then(d=>{
      document.getElementById('jsonNaam').value = file.name;
      if(d.ok){
        document.getElementById('jsonStatus').innerHTML =
          `<span style="color:var(--green)">✅ &nbsp;${d.count} bedrijven geladen</span>`;
        jsonLoaded = true;
        addLog(`JSON geladen: ${d.count} bedrijven uit '${file.name}'`);
      } else {
        document.getElementById('jsonStatus').innerHTML =
          `<span style="color:var(--red)">❌ &nbsp;${d.error}</span>`;
      }
    });
  };
  reader.readAsText(file, 'utf-8');
}

function openExact(){
  fetch('/open', {method:'POST'}).then(r=>r.json()).then(d=>{ if(!d.ok) alert(d.error); });
}

function starten(){
  if(!jsonLoaded && !confirm('Geen bedrijven JSON geladen. Toch starten (notitie wordt "Geen data beschikbaar")?')) return;
  const titel = document.getElementById('titel').value.trim();
  if(!titel){ alert('Vul een titel in.'); return; }
  const body = {
    titel,
    dag:   document.getElementById('dag').value,
    maand: document.getElementById('maand').value,
    jaar:  document.getElementById('jaar').value,
    rmcode: document.getElementById('rmcode').value.trim(),
    fase: document.getElementById('fase').value.trim(),
    overslaan: document.getElementById('overslaan').checked,
    vensters: document.getElementById('vensters').value,
  };
  document.getElementById('progBar').style.width = '0%';
  document.getElementById('progLabel').textContent = 'Starten...';
  fetch('/start', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)})
    .then(r=>r.json()).then(d=>{ if(!d.ok) alert(d.error); });
}

function stoppen(){ fetch('/stop', {method:'POST'}); }

function afsluiten(){
  if(confirm('App afsluiten?')) fetch('/shutdown', {method:'POST'}).finally(()=> window.close());
}

const es = new EventSource('/stream');
es.onmessage = e => {
  const msg = JSON.parse(e.data);
  if(msg.type === 'log') addLog(msg.text, msg.ts);
  else if(msg.type === 'state'){ browserOpen = msg.browser_open; running = msg.running; render(); }
  else if(msg.type === 'progress'){
    const pct = msg.total ? (msg.current/msg.total*100) : 0;
    document.getElementById('progBar').style.width = pct + '%';
    document.getElementById('progLabel').textContent = `${msg.current} / ${msg.total} bedrijven verwerkt`;
  } else if(msg.type === 'done'){
    document.getElementById('progBar').style.width = '100%';
    setStatus('Klaar ✓', 'ok');
    alert(`Verwerking klaar!\n\nGeslaagd: ${msg.geslaagd}\nOvergeslagen: ${msg.overgeslagen}\nMislukt: ${msg.mislukt.length}`);
  } else if(msg.type === 'error'){
    setStatus('Fout opgetreden', 'error');
  }
};
render();
</script>
</body>
</html>"""


# ════════════════════════════════════════════════════════════════════════════
# Routes
# ════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template_string(
        PAGE,
        json_naam=state['json_naam'],
        json_count=len(state['bedrijven_info']) if state['bedrijven_info'] else 0,
    )


@app.route('/upload_json', methods=['POST'])
def upload_json():
    try:
        data = json.loads(request.get_data(as_text=True))
        info = data.get('info', data)
        if not isinstance(info, dict):
            raise ValueError('Ongeldig formaat')
        state['bedrijven_info'] = info
        return jsonify(ok=True, count=len(info))
    except Exception as e:
        return jsonify(ok=False, error=str(e))


@app.route('/open', methods=['POST'])
def open_route():
    if state['browser_open']:
        return jsonify(ok=False, error='Browser is al open')
    state['browser_open'] = True
    push_state()
    threading.Thread(target=browser_worker, daemon=True).start()
    return jsonify(ok=True)


@app.route('/start', methods=['POST'])
def start_route():
    if not state['browser_open']:
        return jsonify(ok=False, error='Klik eerst op "Open Exact" en ga naar je administratie.')
    if state['running']:
        return jsonify(ok=False, error='Al bezig')
    state['cmd_queue'].put({'type': 'run', **request.json})
    return jsonify(ok=True)


@app.route('/stop', methods=['POST'])
def stop_route():
    if state['running']:
        state['stop'] = True
        log('Stoppen na het huidige bedrijf...')
    return jsonify(ok=True)


@app.route('/shutdown', methods=['POST'])
def shutdown():
    state['stop'] = True
    state['cmd_queue'].put({'type': 'close'})
    threading.Timer(1.5, lambda: os._exit(0)).start()
    return jsonify(ok=True)


@app.route('/stream')
def stream():
    q = queue.Queue()
    with state_lock:
        for item in state['history']:
            q.put(item)
        state['subscribers'].append(q)
    q.put({'type': 'state', 'browser_open': state['browser_open'], 'running': state['running']})

    def generate():
        try:
            while True:
                try:
                    item = q.get(timeout=15)
                    yield f"data: {json.dumps(item)}\n\n"
                except queue.Empty:
                    yield "data: {\"type\":\"ping\"}\n\n"
        finally:
            with state_lock:
                if q in state['subscribers']:
                    state['subscribers'].remove(q)
    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ════════════════════════════════════════════════════════════════════════════
# Playwright helpers
# ════════════════════════════════════════════════════════════════════════════

# Markeert het invoerveld dat bij een label hoort (Omschrijving, Fase, ...) met
# data-evt zodat Playwright het daarna betrouwbaar kan vinden.
JS_ZOEK_VELD = r"""
([wanted, mark]) => {
  const norm = s => (s||'').replace(/[*: ]/g,' ').replace(/\s+/g,' ').trim().toLowerCase();
  const ok = el => el && el.type !== 'hidden' && el.type !== 'button' && el.type !== 'submit'
                   && el.type !== 'checkbox' && el.type !== 'radio' && !el.disabled
                   && el.offsetParent !== null;
  const velden = 'input, textarea, select';
  document.querySelectorAll('[data-evt="' + mark + '"]').forEach(e => e.removeAttribute('data-evt'));
  for (const lab of document.querySelectorAll('label, td, th, span, div')) {
    if (lab.querySelector(velden)) continue;
    if (!wanted.includes(norm(lab.textContent))) continue;
    let el = null;
    const f = lab.getAttribute('for');
    if (f) el = document.getElementById(f);
    if (ok(el)) { el.setAttribute('data-evt', mark); return el.id || el.name || mark; }
    let cel = lab.closest('td,th') || lab;
    let sib = cel.nextElementSibling;
    for (let i = 0; sib && i < 3; i++, sib = sib.nextElementSibling) {
      for (const c of sib.querySelectorAll(velden)) {
        if (ok(c)) { c.setAttribute('data-evt', mark); return c.id || c.name || mark; }
      }
    }
  }
  return null;
}
"""

# Zoekt de zichtbare Opslaan-knop (button, a, input, span in toolbar) en markeert hem.
JS_ZOEK_OPSLAAN = r"""
() => {
  const norm = s => (s||'').replace(/\s+/g,' ').trim().toLowerCase();
  const zicht = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  document.querySelectorAll('[data-evt-save]').forEach(e => e.removeAttribute('data-evt-save'));
  const ids = ['btnSave','btnsave','Save','cmdSave','SaveButton'];
  for (const id of ids) {
    const el = document.getElementById(id);
    if (el && zicht(el)) { el.setAttribute('data-evt-save','1'); return 'id:' + id; }
  }
  for (const el of document.querySelectorAll('[id$="btnSave"],[id$="_Save"],[id*="btnSave"]')) {
    if (zicht(el) && !/new|nieuw|close|sluit/i.test(el.id)) { el.setAttribute('data-evt-save','1'); return 'id:' + el.id; }
  }
  const kandidaten = document.querySelectorAll('button, a, input[type=button], input[type=submit], [role=button], span, div, td');
  for (const el of kandidaten) {
    const t = norm(el.tagName === 'INPUT' ? el.value : el.textContent);
    const title = norm(el.getAttribute('title'));
    if ((t === 'opslaan' || title === 'opslaan' || t === 'save') && zicht(el)) {
      // liever de klikbare ouder (button/a) dan een losse span
      const klik = el.closest('button, a, [role=button], [onclick]') || el;
      klik.setAttribute('data-evt-save','1');
      return 'tekst:' + klik.tagName;
    }
  }
  return null;
}
"""

# Is de getypte fasecode door Exact herkend? (verborgen ID gevuld of omschrijving verschenen)
JS_FASE_HERKEND = r"""
el => {
  const box = el.closest('td') || el.parentElement;
  if (!box) return false;
  for (const h of box.querySelectorAll('input[type=hidden]')) {
    if (h.value && h.value.trim() && h.value.trim().toUpperCase() !== el.value.trim().toUpperCase()) return true;
  }
  // omschrijving naast het veld (zelfde cel of de cel erna), niet het label ervoor
  for (const cel of [box, box.nextElementSibling]) {
    if (!cel) continue;
    for (const d of cel.querySelectorAll('[id$="_alt"], [id$="_Description"], [id$="Description"], .BrowseDescription, span')) {
      if (d !== el && (d.innerText || '').trim().length > 1 && !d.querySelector('input')) return true;
    }
  }
  return false;
}
"""

JS_FASE_INFO = r"""
el => {
  const box = el.closest('tr') || el.parentElement;
  const h = [...box.querySelectorAll('input')].map(i => (i.id||i.name) + '=' + (i.type) + ':' + (i.value||'').slice(0,20));
  return 'veld ' + (el.id||el.name) + ' waarde "' + el.value + '"; ' + h.join(', ');
}
"""

# Verzamelt zichtbare foutmeldingen op de pagina.
JS_FOUTEN = r"""
() => {
  const out = [];
  const sel = '.ErrorMessage, .Error, .error, .MessageError, .ValidationError, [class*="rror"][class*="essage"], #Messages .Error, .msg-error';
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect();
    const t = (el.innerText || '').trim();
    if (r.width > 0 && r.height > 0 && t && t.length < 400 && !out.includes(t)) out.push(t);
  }
  return out.slice(0, 5);
}
"""


def division_uit_url(url):
    m = re.search(r'[?&]_Division_=(\d+)', url or '')
    return m.group(1) if m else None


def account_id_uit_url(url):
    try:
        qs = parse_qs(urlparse(url).query)
        for k, v in qs.items():
            if k.lower() in ('accountid', 'id'):
                return v[0]
    except: pass
    return None


def volledige_url(url):
    if url.startswith('http'): return url
    if url.startswith('/'):    return BASE_URL + url
    return BASE_URL + '/docs/' + url


def installeer_chromium():
    """Installeert de Chromium die bij deze Playwright-versie hoort (eenmalig, ca. 150 MB)."""
    import subprocess
    from playwright._impl._driver import compute_driver_executable, get_driver_env
    driver = compute_driver_executable()
    cmd = list(driver) if isinstance(driver, (tuple, list)) else [str(driver)]
    r = subprocess.run(cmd + ['install', 'chromium'], env=get_driver_env(),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or 'onbekende fout').strip()[-500:])


async def launch_context(pw):
    """Start Chromium met de bewaarde sessie. Ontbreekt Chromium, dan wordt hij
    automatisch geïnstalleerd; lukt dat niet, dan wordt Google Chrome gebruikt."""
    opts = dict(headless=False, viewport={'width': 1300, 'height': 850},
                args=['--disable-background-timer-throttling',
                      '--disable-renderer-backgrounding',
                      '--disable-backgrounding-occluded-windows'])
    try:
        return await pw.chromium.launch_persistent_context(SESSIE, **opts)
    except Exception as e:
        if "Executable doesn't exist" not in str(e):
            raise
    log('Chromium ontbreekt - wordt nu automatisch geïnstalleerd (eenmalig, 1-2 minuten)...')
    try:
        await asyncio.to_thread(installeer_chromium)
        log('Chromium geïnstalleerd.')
        return await pw.chromium.launch_persistent_context(SESSIE, **opts)
    except Exception as e:
        log(f'Chromium installeren/starten lukte niet ({str(e).splitlines()[0][:150]}), probeer Google Chrome...')
    return await pw.chromium.launch_persistent_context(SESSIE, channel='chrome', **opts)


def browser_worker():
    """Eigen thread met eigen asyncio-loop: opent de browser en voert START-opdrachten uit."""
    try:
        asyncio.run(browser_main())
    except Exception as e:
        import traceback
        log('FOUT browser: ' + str(e))
        log(traceback.format_exc())
        publish({'type': 'error', 'text': str(e)})
    finally:
        state['browser_open'] = False
        state['running'] = False
        push_state()


async def browser_main():
    from playwright.async_api import async_playwright
    for f in glob.glob(os.path.join(SESSIE, 'Singleton*')):
        try: os.remove(f)
        except: pass
    os.makedirs(SESSIE, exist_ok=True)

    async with async_playwright() as pw:
        ctx = await launch_context(pw)
        ctx.set_default_timeout(15000)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(BASE_URL + '/docs/MenuPortal.aspx', wait_until='domcontentloaded')
        log('Browser geopend.')
        log('>>> Log in, kies zelf de juiste ADMINISTRATIE en klik dan op START. <<<')

        while True:
            try:
                cmd = state['cmd_queue'].get_nowait()
            except queue.Empty:
                if not ctx.pages:
                    log('Browser is gesloten.')
                    break
                await asyncio.sleep(0.3)
                continue
            if cmd['type'] == 'close':
                break
            if cmd['type'] == 'run':
                # Het tabblad waar de gebruiker nu in zit (daar staat de gekozen administratie)
                await run_batch(ctx, ctx.pages[0], cmd)
        try: await ctx.close()
        except: pass


async def run_batch(ctx, hoofd, cmd):
    titel, dag, maand, jaar = cmd['titel'], cmd['dag'], cmd['maand'], cmd['jaar']
    rmcode    = (cmd.get('rmcode') or '').strip()
    fase      = (cmd.get('fase') or 'VB').strip() or 'VB'
    overslaan = cmd.get('overslaan', True)
    try:    n_vensters = max(1, min(10, int(cmd.get('vensters') or 6)))
    except: n_vensters = 6

    os.makedirs(LOG_DIR, exist_ok=True)
    stempel = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    state['logfile'] = os.path.join(LOG_DIR, f'{stempel}.log')
    state['running'] = True
    state['stop'] = False
    push_state()

    async def dialoog(d):
        try:
            log(f'  (melding van Exact: "{d.message.strip()[:150]}" -> OK)')
            await d.accept()
        except: pass

    async def screenshot(page, naam):
        veilig = re.sub(r'[^\w\-]+', '_', naam)[:40]
        pad = os.path.join(LOG_DIR, f'fout_{stempel}_{veilig}')
        try: await page.screenshot(path=pad + '.png', full_page=True)
        except: pass
        try:
            delen = []
            for fr in page.frames:
                delen.append(f'\n<!-- FRAME: {fr.url} -->\n')
                try: delen.append(await fr.content())
                except: pass
            with open(pad + '.html', 'w', encoding='utf-8') as f:
                f.write(''.join(delen))
        except: pass
        log(f'  Screenshot + pagina bewaard: logs/{os.path.basename(pad)}.png/.html')

    def laad_notitie(bedrijf_naam):
        b = bedrijf_naam.strip().lower()
        beste = None
        for key, info in state['bedrijven_info'].items():
            k = key.strip().lower()
            if k == b: beste = info; break
            if beste is None and (k in b or b in k): beste = info
        if not beste: return 'Geen data beschikbaar'
        regels = []
        if beste.get('wat'):   regels.append('Wat: '     + beste['wat'])
        if beste.get('groot'): regels.append('Grootte: ' + beste['groot'])
        if beste.get('dmu'):   regels.append('DMU: '     + beste['dmu'])
        if beste.get('kans'):  regels.append('Kans: '    + beste['kans'])
        return '\n'.join(regels)

    async def wacht_op_laden(frame, timeout=15000):
        try: await frame.wait_for_selector('#WaitMessageImg', state='hidden', timeout=timeout)
        except: pass

    async def goto(page, url):
        # Geen 'networkidle': Exact blijft op de achtergrond verkeer houden, dat kost alleen tijd.
        await page.goto(url, wait_until='domcontentloaded')

    async def wacht_op_frame(page, deel, check=None, pogingen=60):
        for _ in range(pogingen):
            for f in page.frames:
                if deel in f.url:
                    if check is None: return f
                    try:
                        if await f.locator(check).count() > 0: return f
                    except: pass
            await asyncio.sleep(0.15)
        return None

    # ── lijst met bedrijven ──────────────────────────────────────────────
    async def get_bedrijven(frame):
        return await frame.evaluate(r"""() => {
          const out = [], gezien = new Set();
          const actie = /^(bewerken|wijzigen|edit|verwijderen|bekijken|openen|kopi[eë]ren|selecteren)$/i;
          const sleutel = h => { const m = h.match(/AccountID=([^&]+)/i); return m ? m[1].toLowerCase() : h; };
          let rijen = document.querySelectorAll('tr.DataDark, tr.DataLight');
          if (!rijen.length) rijen = document.querySelectorAll('tr');
          for (const rij of rijen) {
            if ((rij.id||'').includes('crit') || (rij.className||'').includes('Header')) continue;
            for (const a of rij.querySelectorAll('a')) {
              const href = a.getAttribute('href') || '', t = (a.innerText||'').trim();
              if (t.length > 2 && !actie.test(t) && (href.includes('AccountID') || href.includes('CRMAccount'))) {
                const k = sleutel(href);
                if (!gezien.has(k)) { gezien.add(k); out.push({naam: t, url: href}); }
                break;
              }
            }
          }
          return out;
        }""")

    # ── velden ───────────────────────────────────────────────────────────
    async def veld(frame, labels, mark, fallback_index=None):
        try:
            if await frame.evaluate(JS_ZOEK_VELD, [[l.lower() for l in labels], mark]):
                return frame.locator(f'[data-evt="{mark}"]').first
        except: pass
        if fallback_index is not None:
            loc = frame.locator('input[type="text"]:visible')
            if await loc.count() > fallback_index:
                return loc.nth(fallback_index)
        return None

    async def zoek_opslaan(page, form_frame):
        frames = [form_frame] + [f for f in page.frames if f is not form_frame]
        for f in frames:
            try:
                if await f.evaluate(JS_ZOEK_OPSLAAN):
                    return f.locator('[data-evt-save="1"]').first
            except: pass
        return None

    async def fouten_op_pagina(page):
        out = []
        for f in page.frames:
            try: out += await f.evaluate(JS_FOUTEN)
            except: pass
        return out

    vk_template = {'tpl': None}   # URL-sjabloon 'nieuwe verkoopkans' -> relatiekaart overslaan
    tpl_lock = asyncio.Lock()

    async def nieuwe_vk_url(page, bedrijf):
        acc_id = account_id_uit_url(bedrijf['url'])
        if vk_template['tpl'] and acc_id:
            return vk_template['tpl'].replace('{ACCID}', acc_id)
        await goto(page, volledige_url(bedrijf['url']))
        acc_frame = await wacht_op_frame(page, 'CRMAccount', 'a[href*="SFAOpportunity.aspx"]')
        if not acc_frame:
            log(f'  {bedrijf["naam"]}: FOUT relatiekaart / link "nieuwe verkoopkans" niet gevonden'); return None
        vk = None
        for href in await acc_frame.eval_on_selector_all('a[href*="SFAOpportunity.aspx"]',
                                                         'els => els.map(e => e.getAttribute("href"))'):
            if href and 'BCAction=0' in href: vk = href; break
        if not vk:
            log(f'  {bedrijf["naam"]}: FOUT link "nieuwe verkoopkans" niet gevonden'); return None
        vk = volledige_url(vk.replace('&amp;', '&'))
        if division and '_Division_' not in vk:
            vk += ('&' if '?' in vk else '?') + f'_Division_={division}'
        if acc_id and vk.count(acc_id) == 1:
            vk_template['tpl'] = vk.replace(acc_id, '{ACCID}')
        return vk

    async def maak_verkoopkans(page, bedrijf, notitie):
        vk_url = await nieuwe_vk_url(page, bedrijf)
        if not vk_url: return False
        await goto(page, vk_url)
        ff = await wacht_op_frame(page, 'SFAOpportunity', 'input[type="text"]:visible', pogingen=100)
        if not ff:
            log(f'  {bedrijf["naam"]}: FOUT verkoopkans-formulier niet geladen')
            await screenshot(page, bedrijf['naam']); return False
        await wacht_op_laden(ff, 8000)

        # 1. Omschrijving
        el = await veld(ff, ['Omschrijving', 'Naam'], 'oms', 0)
        if el: await el.fill(titel)
        else:  log(f'  {bedrijf["naam"]}: WAARSCHUWING veld Omschrijving niet gevonden')

        # 2. Fase (bijv. VB). GEEN Enter: dat verstuurt het formulier voordat de fase herkend is.
        el = await veld(ff, ['Fase', 'Verkoopkans fase', 'Verkoopkansfase'], 'fase', 1)
        if el:
            await el.click(); await el.fill('')
            await el.press_sequentially(fase, delay=40)
            await asyncio.sleep(0.6)
            await el.press('Tab')
            herkend = False
            for _ in range(25):          # max ~5 sec wachten op Exact
                await asyncio.sleep(0.2)
                try: herkend = await el.evaluate(JS_FASE_HERKEND)
                except: herkend = False
                if herkend: break
            await wacht_op_laden(ff, 5000)
            if not herkend:
                info = ''
                try: info = await el.evaluate(JS_FASE_INFO)
                except: pass
                log(f'  {bedrijf["naam"]}: WAARSCHUWING fase "{fase}" niet (zeker) herkend door Exact [{info}]')
        else: log(f'  {bedrijf["naam"]}: WAARSCHUWING veld Fase niet gevonden')

        # 3. Sluitingsdatum
        el = await veld(ff, ['Sluitingsdatum', 'Verwachte sluitingsdatum', 'Einddatum'], 'datum', 2)
        if el:
            await el.fill(''); await el.click()
            await el.press_sequentially(f'{dag}{maand}{jaar}', delay=25)
            waarde = await el.input_value()
            if dag not in waarde or jaar not in waarde:
                await el.fill(f'{dag}-{maand}-{jaar}')
            await el.press('Tab')
            await asyncio.sleep(0.2)
        else: log(f'  {bedrijf["naam"]}: WAARSCHUWING veld Sluitingsdatum niet gevonden')

        # 4. Notitie met tijdstempel
        ta = await veld(ff, ['Notities', 'Notitie', 'Opmerkingen'], 'notitie')
        if not ta:
            loc = ff.locator('textarea:visible')
            ta = loc.first if await loc.count() else None
        if ta:
            await ta.click()
            ts_btn = ff.locator('input[value="Tijdstempel"], button:has-text("Tijdstempel"), a:has-text("Tijdstempel"), [title="Tijdstempel"]')
            if await ts_btn.count():
                try: await ts_btn.first.click(); await asyncio.sleep(0.2)
                except: pass
            await ta.evaluate('el => { el.focus(); el.selectionStart = el.selectionEnd = el.value.length; }')
            await page.keyboard.insert_text(('\n' if (await ta.input_value()).strip() else '') + notitie)
            await ta.dispatch_event('change')
        else: log(f'  {bedrijf["naam"]}: WAARSCHUWING notitieveld niet gevonden')

        # 5. Opslaan
        knop = await zoek_opslaan(page, ff)
        if not knop:
            log(f'  {bedrijf["naam"]}: FOUT Opslaan knop niet gevonden')
            await screenshot(page, bedrijf['naam']); return False

        # Markeer het formulier: verdwijnt de markering, dan heeft Exact de pagina herladen (= opgeslagen)
        try: await ff.evaluate('() => { window.__evt_voor_opslaan = 1; }')
        except: pass
        try:
            await knop.click(timeout=5000)
        except Exception:
            try: await knop.evaluate('el => el.click()')
            except Exception as e:
                log(f'  {bedrijf["naam"]}: FOUT klikken op Opslaan mislukt: {e}')
                await screenshot(page, bedrijf['naam']); return False

        herladen = False
        for _ in range(100):   # max ~20 sec
            await asyncio.sleep(0.2)
            try:
                if ff.is_detached() or not await ff.evaluate('() => window.__evt_voor_opslaan === 1'):
                    herladen = True; break
            except Exception:
                herladen = True; break
            if await fouten_op_pagina(page): break
        if herladen:
            try: await page.wait_for_load_state('domcontentloaded', timeout=10000)
            except: pass
            await asyncio.sleep(0.2)

        fouten = await fouten_op_pagina(page)
        if fouten:
            log(f'  {bedrijf["naam"]}: FOUT bij opslaan: ' + ' | '.join(fouten))
            await screenshot(page, bedrijf['naam']); return False
        if not herladen:
            log(f'  {bedrijf["naam"]}: FOUT Exact reageerde niet op Opslaan (controleer dit bedrijf in Exact)')
            await screenshot(page, bedrijf['naam']); return False
        return True

    # ── Hoofdstroom ──────────────────────────────────────────────────────
    geslaagd, mislukt, overgeslagen = 0, [], 0
    werk_paginas = []
    division = None
    try:
        log(f'═══ START ═══  Titel: "{titel}"  |  Sluitingsdatum: {dag}-{maand}-{jaar}  |  {n_vensters} vensters tegelijk')
        log(f'Log wordt bewaard in logs/{os.path.basename(state["logfile"])}')

        # Gekozen administratie uitlezen uit de pagina waar de gebruiker staat
        for p in ctx.pages:
            for f in p.frames:
                division = division_uit_url(f.url)
                if division: hoofd = p; break
            if division: break
        log(f'Administratie: {division or "de administratie die nu in Exact openstaat"}')

        lf = next((f for f in hoofd.frames if 'CRMAccounts.aspx' in f.url), None)
        if lf:
            log('Je staat al op een relatielijst - precies die lijst wordt verwerkt.')
        else:
            url = BASE_URL + '/docs/CRMAccounts.aspx?Status=S&Selector=List%3atList'
            if division: url += f'&_Division_={division}'
            if rmcode:   url += f'&RelationManagerCode={rmcode}'
            log('Suspects-lijst laden...')
            await goto(hoofd, url)
            lf = await wacht_op_frame(hoofd, 'CRMAccounts.aspx', pogingen=100)
        if not lf:
            raise RuntimeError('Relatielijst (CRMAccounts) niet gevonden. Ben je ingelogd en in de juiste administratie?')

        await wacht_op_laden(lf)
        bedrijven = await get_bedrijven(lf)
        log(f'Gevonden: {len(bedrijven)} bedrijven in Exact')
        if not bedrijven:
            raise RuntimeError('Geen bedrijven gevonden in de lijst')

        verwerkt = laad_verwerkt()
        sleutel = titel
        klaar = set(verwerkt.get(sleutel, []))
        totaal = len(bedrijven)
        teller = {'n': 0}

        werk = asyncio.Queue()
        for i, b in enumerate(bedrijven):
            if overslaan and b['naam'] in klaar:
                overgeslagen += 1
                teller['n'] += 1
            else:
                werk.put_nowait(b)
        if overgeslagen:
            log(f'{overgeslagen} bedrijven hebben al een verkoopkans met deze titel -> overgeslagen')
        publish({'type': 'progress', 'current': teller['n'], 'total': totaal})
        t_start = time.time()

        # Eerste bedrijf alleen doen: dan kennen we de link voor 'nieuwe verkoopkans'
        # en kunnen de andere vensters direct naar het formulier springen.
        async def verwerk(page, bedrijf):
            nonlocal geslaagd
            t0 = time.time()
            try:
                ok = await maak_verkoopkans(page, bedrijf, laad_notitie(bedrijf['naam']))
            except Exception as e:
                log(f'  {bedrijf["naam"]}: FOUT {str(e).splitlines()[0]}')
                await screenshot(page, bedrijf['naam']); ok = False
            teller['n'] += 1
            if ok:
                geslaagd += 1
                klaar.add(bedrijf['naam'])
                verwerkt[sleutel] = sorted(klaar)
                bewaar_verwerkt(verwerkt)
                log(f'[{teller["n"]}/{totaal}] ✓ {bedrijf["naam"]}  ({time.time() - t0:.1f}s)')
            else:
                mislukt.append(bedrijf['naam'])
                log(f'[{teller["n"]}/{totaal}] ✗ {bedrijf["naam"]}')
            publish({'type': 'progress', 'current': teller['n'], 'total': totaal})

        async def worker(page):
            while not state['stop']:
                try: bedrijf = werk.get_nowait()
                except asyncio.QueueEmpty: return
                await verwerk(page, bedrijf)

        async def nieuwe_pagina():
            p = await ctx.new_page()
            p.on('dialog', dialoog)
            werk_paginas.append(p)
            return p

        if not werk.empty():
            eerste = await nieuwe_pagina()
            # Proefdraaien met 1 venster: pas als dat lukt gaan de andere vensters open.
            for poging in range(2):
                if werk.empty() or state['stop']: break
                voor = geslaagd
                await verwerk(eerste, werk.get_nowait())
                if geslaagd > voor: break
            if geslaagd == 0 and not werk.empty():
                log('De eerste bedrijven mislukten - gestopt zodat niet de hele lijst mislukt.')
                log('Kijk in de map logs naar de screenshot/.html van de mislukte bedrijven.')
            else:
                extra = [await nieuwe_pagina() for _ in range(min(n_vensters, werk.qsize() + 1) - 1)]
                await asyncio.gather(*(worker(p) for p in [eerste] + extra))

        if state['stop']: log('Gestopt door gebruiker.')
        duur = time.time() - t_start
        log(f'═══ KLAAR in {int(duur // 60)}m{int(duur % 60):02d}s ═══  '
            f'{geslaagd} geslaagd, {overgeslagen} overgeslagen, {len(mislukt)} mislukt')
        for m in mislukt: log('  ✗ ' + m)
        if mislukt: log('Klik nogmaals op START om alleen de mislukte bedrijven opnieuw te proberen.')
        publish({'type': 'done', 'geslaagd': geslaagd, 'overgeslagen': overgeslagen, 'mislukt': mislukt})
    except Exception as e:
        import traceback
        log('FOUT: ' + str(e))
        log(traceback.format_exc())
        publish({'type': 'error', 'text': str(e)})
    finally:
        for p in werk_paginas:
            try: await p.close()
            except: pass
        state['running'] = False
        state['stop'] = False
        push_state()


# ════════════════════════════════════════════════════════════════════════════
# Start
# ════════════════════════════════════════════════════════════════════════════

def al_actief():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sk:
        return sk.connect_ex(('127.0.0.1', PORT)) == 0


if __name__ == '__main__':
    url = f'http://127.0.0.1:{PORT}'
    if al_actief():
        # App draait al: alleen het venster openen
        webbrowser.open(url)
        sys.exit(0)
    try:
        print(f'\n  Exact Tool draait op {url}')
        print('  Sluit dit venster om de app te stoppen.\n')
    except: pass
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(port=PORT, debug=False, threaded=True)
