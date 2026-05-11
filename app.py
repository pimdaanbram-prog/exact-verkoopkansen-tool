#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, json, threading, queue, glob, webbrowser, time
from datetime import datetime

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
SESSIE       = os.path.join(BASE_DIR, 'browser_sessie')
BROWSERS_DIR = os.path.join(BASE_DIR, '_browsers')
BASE_URL     = 'https://start.exactonline.nl'
SUSPECTS_URL = (BASE_URL + '/docs/CRMAccounts.aspx'
                '?Status=S&Selector=List%3atList'
                '&_Division_=4021621&RelationManagerCode=2107693')

os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', BROWSERS_DIR)

app   = Flask(__name__)
state = {
    'running': False,
    'log_queue': queue.Queue(),
    'bedrijven_info': {},
    'json_naam': '',
    'progress': (0, 0),
}

# ── Standaard JSON laden ──────────────────────────────────────────────────────
default_json = os.path.join(BASE_DIR, 'bedrijven_data.json')
if os.path.exists(default_json):
    with open(default_json, encoding='utf-8') as _f:
        _d = json.load(_f)
    state['bedrijven_info'] = _d.get('info', _d)
    state['json_naam'] = os.path.basename(default_json)


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

  /* ── header ── */
  .header{width:100%;background:var(--card);border-bottom:3px solid var(--accent);
          padding:28px 40px 22px;margin-bottom:32px}
  .header h1{font-size:26px;font-weight:700;color:var(--accent);letter-spacing:-.3px}
  .header p{color:var(--muted);font-size:13px;margin-top:6px}

  /* ── layout ── */
  .wrap{width:100%;max-width:700px;padding:0 20px;display:flex;flex-direction:column;gap:24px}

  /* ── card ── */
  .card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:22px 24px}
  .card-label{font-size:13px;font-weight:700;color:var(--text);margin-bottom:10px}

  /* ── inputs ── */
  input[type=text], select{
    background:#0d1117;border:1px solid var(--border);color:var(--text);
    border-radius:8px;padding:10px 14px;font-size:14px;width:100%;
    outline:none;transition:border .15s;font-family:inherit}
  input[type=text]:focus, select:focus{border-color:var(--accent)}
  select{cursor:pointer;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%238b949e' stroke-width='1.5' fill='none'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center;padding-right:32px}

  /* ── datum row ── */
  .datum-row{display:flex;gap:14px}
  .datum-col{display:flex;flex-direction:column;gap:6px}
  .datum-col label{font-size:11px;color:var(--muted)}
  .datum-col select{width:auto;min-width:80px}

  /* ── json card ── */
  .json-row{display:flex;align-items:center;gap:12px}
  .json-row input[type=text]{flex:1;color:var(--muted)}
  .json-status{font-size:12px;margin-top:8px;min-height:18px}

  /* ── file input hidden ── */
  #fileInput{display:none}

  /* ── log ── */
  .log-box{background:var(--log-bg);border:1px solid var(--border);border-radius:var(--radius);
           padding:14px 16px;height:200px;overflow-y:auto;
           font-family:'Consolas','Courier New',monospace;font-size:12px;
           color:var(--log-text);white-space:pre-wrap;word-break:break-all}

  /* ── progress ── */
  .prog-label{font-size:12px;color:var(--muted);margin-bottom:8px}
  .prog-track{background:var(--border);border-radius:99px;height:14px;overflow:hidden}
  .prog-bar{background:var(--accent);height:100%;border-radius:99px;width:0%;
            transition:width .4s ease}

  /* ── buttons ── */
  .btn-row{display:flex;gap:10px}
  .btn{border:none;border-radius:10px;cursor:pointer;font-family:inherit;
       font-weight:700;transition:background .15s,transform .1s;outline:none}
  .btn:active{transform:scale(.97)}
  .btn-start{flex:1;height:56px;font-size:18px;background:var(--accent);color:#fff}
  .btn-start:hover:not(:disabled){background:var(--accent2)}
  .btn-start:disabled{opacity:.45;cursor:not-allowed}
  .btn-stop{width:56px;height:56px;font-size:20px;background:var(--card);
            color:var(--text);border:1px solid var(--border)}
  .btn-stop:hover:not(:disabled){background:var(--red);border-color:var(--red)}
  .btn-stop:disabled{opacity:.3;cursor:not-allowed}

  /* ── status bar ── */
  .status-bar{font-size:11px;color:var(--green);display:flex;align-items:center;gap:6px}
  .dot{width:8px;height:8px;border-radius:50%;background:var(--green);display:inline-block}
  .dot.busy{background:var(--yellow);animation:pulse 1s infinite}
  .dot.error{background:var(--red)}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}

  /* ── bestand knop ── */
  .btn-file{background:var(--accent2);color:#fff;border:none;border-radius:8px;
            padding:10px 18px;font-size:13px;cursor:pointer;white-space:nowrap;
            font-family:inherit;font-weight:600;transition:background .15s}
  .btn-file:hover{background:var(--accent)}
</style>
</head>
<body>

<div class="header">
  <h1>⚡ Exact Verkoopkansen Tool</h1>
  <p>Automatisch verkoopkansen aanmaken in Exact Online</p>
</div>

<div class="wrap">

  <!-- Titel -->
  <div>
    <div class="card-label">✏️ &nbsp;Titel verkoopkans</div>
    <input type="text" id="titel" value="belcentrum 12-05-26 Tim. S" placeholder="bijv. belcentrum 12-05-26 Tim. S">
  </div>

  <!-- Datum -->
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

  <!-- JSON -->
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
    </div>
  </div>

  <!-- Log -->
  <div>
    <div class="card-label">🖥️ &nbsp;Activiteit log</div>
    <div class="log-box" id="log">Gereed om te starten...<br></div>
  </div>

  <!-- Progress -->
  <div class="card">
    <div class="prog-label" id="progLabel">Gereed om te starten</div>
    <div class="prog-track"><div class="prog-bar" id="progBar"></div></div>
  </div>

  <!-- Knoppen -->
  <div class="btn-row">
    <button class="btn btn-start" id="btnStart" onclick="starten()">▶&nbsp;&nbsp;STARTEN</button>
    <button class="btn btn-stop"  id="btnStop"  onclick="stoppen()" disabled>⏹</button>
  </div>

  <!-- Statusbalk + afsluiten -->
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
let evtSource = null;
let jsonLoaded = {{ 'true' if json_count else 'false' }};

function addLog(txt){
  const box = document.getElementById('log');
  const ts  = new Date().toLocaleTimeString('nl-NL');
  box.textContent += `[${ts}]  ${txt}\n`;
  box.scrollTop = box.scrollHeight;
}

function setStatus(txt, type='ok'){
  document.getElementById('statusTxt').textContent = txt;
  const dot = document.getElementById('dot');
  dot.className = 'dot' + (type==='busy' ? ' busy' : type==='error' ? ' error' : '');
}

function setRunning(r){
  document.getElementById('btnStart').disabled = r;
  document.getElementById('btnStop').disabled  = !r;
  document.getElementById('btnStart').textContent = r ? '⏳  Bezig...' : '▶  STARTEN';
}

function laadJson(input){
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    fetch('/upload_json', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: e.target.result
    }).then(r=>r.json()).then(d=>{
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

function starten(){
  if(!jsonLoaded){ alert('Selecteer eerst een bedrijven JSON bestand.'); return; }
  const titel = document.getElementById('titel').value.trim();
  if(!titel){ alert('Vul een titel in.'); return; }

  const dag   = document.getElementById('dag').value;
  const maand = document.getElementById('maand').value;
  const jaar  = document.getElementById('jaar').value;

  document.getElementById('progBar').style.width = '0%';
  document.getElementById('progLabel').textContent = 'Starten...';
  setRunning(true);
  setStatus('Verwerken...', 'busy');
  addLog(`Titel: '${titel}'  |  Datum: ${dag}-${maand}-${jaar}`);
  addLog('Browser wordt geopend in Exact Online...');

  fetch('/start', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({titel, dag, maand, jaar})
  });

  // SSE stream
  if(evtSource) evtSource.close();
  evtSource = new EventSource('/stream');
  evtSource.onmessage = e => {
    const msg = JSON.parse(e.data);
    if(msg.type === 'log'){
      addLog(msg.text);
    } else if(msg.type === 'progress'){
      const pct = msg.total ? (msg.current/msg.total*100) : 0;
      document.getElementById('progBar').style.width = pct + '%';
      document.getElementById('progLabel').textContent =
        `${msg.current} / ${msg.total} bedrijven verwerkt`;
    } else if(msg.type === 'done'){
      addLog(`═══ KLAAR ═══  ${msg.geslaagd} geslaagd${msg.mislukt.length ? ', '+msg.mislukt.length+' mislukt' : ''}`);
      msg.mislukt.forEach(m => addLog('  ✗ ' + m));
      document.getElementById('progBar').style.width = '100%';
      setRunning(false);
      setStatus('Klaar ✓', 'ok');
      evtSource.close();
      alert(`Verwerking klaar!\n\nGeslaagd: ${msg.geslaagd}\nMislukt: ${msg.mislukt.length}`);
    } else if(msg.type === 'error'){
      addLog('FOUT: ' + msg.text);
      setRunning(false);
      setStatus('Fout opgetreden', 'error');
      evtSource.close();
    }
  };
}

function stoppen(){
  fetch('/stop', {method:'POST'});
  addLog('Stopaanvraag verzonden...');
}

function afsluiten(){
  if(confirm('App afsluiten?')){
    fetch('/shutdown', {method:'POST'}).finally(()=> window.close());
  }
}
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
        raw  = request.get_data(as_text=True)
        data = json.loads(raw)
        info = data.get('info', data)
        if not isinstance(info, dict):
            raise ValueError('Ongeldig formaat')
        state['bedrijven_info'] = info
        return jsonify(ok=True, count=len(info))
    except Exception as e:
        return jsonify(ok=False, error=str(e))


@app.route('/start', methods=['POST'])
def start_route():
    if state['running']:
        return jsonify(ok=False, error='Al bezig')
    payload = request.json
    t = threading.Thread(
        target=run_automation,
        args=(payload['titel'], payload['dag'], payload['maand'], payload['jaar']),
        daemon=True,
    )
    t.start()
    return jsonify(ok=True)


@app.route('/stop', methods=['POST'])
def stop_route():
    state['running'] = False
    return jsonify(ok=True)


@app.route('/shutdown', methods=['POST'])
def shutdown():
    state['running'] = False
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return jsonify(ok=True)


@app.route('/stream')
def stream():
    def generate():
        while True:
            try:
                item = state['log_queue'].get(timeout=30)
                yield f"data: {json.dumps(item)}\n\n"
                if item.get('type') in ('done', 'error'):
                    break
            except queue.Empty:
                yield "data: {\"type\":\"ping\"}\n\n"
    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ════════════════════════════════════════════════════════════════════════════
# Automation
# ════════════════════════════════════════════════════════════════════════════

def run_automation(naam, dag, maand, jaar):
    state['running'] = True
    q = state['log_queue']

    def log(t):       q.put({'type': 'log', 'text': t})
    def prog(c, tot): q.put({'type': 'progress', 'current': c, 'total': tot})

    try:
        from playwright.sync_api import sync_playwright

        def wacht(ctx, ms=1500): ctx.wait_for_timeout(ms)

        def verwijder_lock():
            for f in glob.glob(os.path.join(SESSIE, 'Singleton*')):
                try: os.remove(f)
                except: pass

        def is_ingelogd(page):
            u = page.url.lower()
            return ('exactonline.nl' in u and 'returnurl' not in u
                    and 'login' not in u and 'oauth' not in u and 'adfs' not in u)

        def wacht_op_login(page):
            for i in range(60):
                if is_ingelogd(page): log('Ingelogd!'); return True
                if i == 0: log('=== LOG IN VIA DE BROWSER ===')
                wacht(page, 2000)
                try: page.wait_for_load_state('networkidle', timeout=3000)
                except: pass
            return False

        def wacht_op_laden(frame, timeout=20000):
            try: frame.wait_for_selector('#WaitMessageImg', state='hidden', timeout=timeout)
            except: pass
            wacht(frame, 1000)

        def get_bedrijven(frame):
            result = []
            for rij in frame.query_selector_all('tr.DataDark, tr.DataLight'):
                for link in rij.query_selector_all('a'):
                    href  = link.get_attribute('href') or ''
                    tekst = link.inner_text().strip()
                    if tekst and len(tekst) > 2 and ('AccountID' in href or 'CRMAccount' in href):
                        result.append({'naam': tekst, 'url': href}); break
            if not result:
                for rij in frame.query_selector_all('tr'):
                    if 'crit' in (rij.get_attribute('id') or '') or 'Header' in (rij.get_attribute('class') or ''):
                        continue
                    for link in rij.query_selector_all('a'):
                        href  = link.get_attribute('href') or ''
                        tekst = link.inner_text().strip()
                        if tekst and len(tekst) > 2 and ('AccountID' in href or 'CRMAccount' in href):
                            result.append({'naam': tekst, 'url': href}); break
            return result

        def laad_notitie(bedrijf_naam):
            for key, info in state['bedrijven_info'].items():
                k = key.strip().lower(); b = bedrijf_naam.strip().lower()
                if k == b or k in b or b in k:
                    regels = []
                    if info.get('wat'):   regels.append('Wat: '     + info['wat'])
                    if info.get('groot'): regels.append('Grootte: ' + info['groot'])
                    if info.get('dmu'):   regels.append('DMU: '     + info['dmu'])
                    if info.get('kans'):  regels.append('Kans: '    + info['kans'])
                    return '\n'.join(regels)
            return 'Geen data beschikbaar'

        def maak_verkoopkans(page, bedrijf, notitie_tekst):
            url = bedrijf['url']
            full_url = url if url.startswith('http') else (
                BASE_URL + url if url.startswith('/') else BASE_URL + '/docs/' + url)
            page.goto(full_url)
            try: page.wait_for_load_state('networkidle', timeout=15000)
            except: pass
            wacht(page, 2000)

            acc_frame = next(
                (f for f in page.frames if 'CRMAccountCard' in f.url
                 or ('CRMAccount' in f.url and 'Accounts.aspx' not in f.url)), None)
            if not acc_frame: log('  FOUT: account frame niet gevonden'); return False

            vk_url = next(
                (link.get_attribute('href') for link in acc_frame.query_selector_all('a')
                 if 'SFAOpportunity.aspx' in (link.get_attribute('href') or '')
                 and 'BCAction=0' in (link.get_attribute('href') or '')), None)
            if not vk_url: log('  FOUT: verkoopkans link niet gevonden'); return False

            full_vk = vk_url if vk_url.startswith('http') else BASE_URL + '/docs/' + vk_url
            page.goto(full_vk)
            try: page.wait_for_load_state('networkidle', timeout=15000)
            except: pass
            wacht(page, 2000)

            form_frame = next((f for f in page.frames if 'SFAOpportunity' in f.url), page.main_frame)

            try:
                inputs = form_frame.query_selector_all('input[type="text"]')
                if inputs: inputs[0].click(); inputs[0].fill(naam)
            except Exception as e: log(f'  Fout omschrijving: {e}')

            wacht(page, 500)

            try:
                inputs = form_frame.query_selector_all('input[type="text"]')
                if len(inputs) >= 2:
                    inputs[1].click(); inputs[1].triple_click()
                    inputs[1].type('VB'); wacht(page, 1000)
                    inputs[1].press('Enter'); wacht(page, 500)
            except Exception as e: log(f'  Fout fase: {e}')

            wacht(page, 500)

            try:
                inputs = form_frame.query_selector_all('input[type="text"]')
                if len(inputs) >= 3:
                    d = inputs[2]; d.click(); wacht(page, 2000)
                    page.keyboard.type(dag,   delay=200); wacht(page, 500)
                    page.keyboard.type(maand, delay=200); wacht(page, 500)
                    page.keyboard.type(jaar,  delay=200); wacht(page, 2000)
                    d.press('Tab'); wacht(page, 1000)
            except Exception as e: log(f'  Fout datum: {e}')

            wacht(page, 500)

            try:
                ta = form_frame.query_selector('textarea')
                if ta:
                    ta.click(); wacht(page, 500)
                    ts_btn = form_frame.query_selector('input[value="Tijdstempel"]')
                    if not ts_btn: ts_btn = form_frame.query_selector('button:has-text("Tijdstempel")')
                    if not ts_btn:
                        for el in form_frame.query_selector_all('input[type="button"],input[type="submit"],button'):
                            if 'Tijdstempel' in (el.get_attribute('value') or el.inner_text()):
                                ts_btn = el; break
                    if ts_btn: ts_btn.click(); wacht(page, 1000)
                    ta.press('End'); ta.type('\n' + notitie_tekst)
            except Exception as e: log(f'  Fout notitie: {e}')

            wacht(page, 500)

            try:
                opslaan = next(
                    (f.query_selector('input[value="Opslaan"]')
                     for f in [form_frame, page.main_frame]
                     if f.query_selector('input[value="Opslaan"]')), None)
                if not opslaan:
                    for f in page.frames:
                        try:
                            opslaan = f.get_by_text('Opslaan', exact=True).first
                            if opslaan: break
                        except: pass
                if opslaan:
                    opslaan.click()
                    try: page.wait_for_load_state('networkidle', timeout=10000)
                    except: pass
                    wacht(page, 2000); return True
                else: log('  FOUT: Opslaan knop niet gevonden'); return False
            except Exception as e: log(f'  Fout opslaan: {e}'); return False

        # ── Hoofdstroom ────────────────────────────────────────────────────
        verwijder_lock()
        with sync_playwright() as pw:
            os.makedirs(SESSIE, exist_ok=True)
            ctx  = pw.chromium.launch_persistent_context(
                SESSIE, headless=False, viewport={'width': 1400, 'height': 900})
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            wacht(page, 2000)
            page.goto(BASE_URL + '/docs/MenuPortal.aspx')
            try: page.wait_for_load_state('networkidle', timeout=10000)
            except: pass
            wacht(page, 2000)

            if not wacht_op_login(page):
                ctx.close(); q.put({'type': 'error', 'text': 'Login niet gelukt'}); return

            log('Laden suspects lijst...')
            page.goto(SUSPECTS_URL)
            try: page.wait_for_load_state('networkidle', timeout=15000)
            except: pass
            wacht(page, 3000)

            crm_frame = next((f for f in page.frames if 'CRMAccounts' in f.url), None)
            if not crm_frame:
                ctx.close(); q.put({'type': 'error', 'text': 'CRM frame niet gevonden'}); return

            wacht_op_laden(crm_frame)
            bedrijven = get_bedrijven(crm_frame)
            log(f'Gevonden: {len(bedrijven)} bedrijven in Exact')

            if not bedrijven:
                ctx.close(); q.put({'type': 'error', 'text': 'Geen bedrijven gevonden'}); return

            geslaagd = 0; mislukt = []; totaal = len(bedrijven)

            for i, bedrijf in enumerate(bedrijven):
                if not state['running']: log('Gestopt door gebruiker.'); break
                log(f"[{i+1}/{totaal}]  {bedrijf['naam']}")
                notitie = laad_notitie(bedrijf['naam'])
                if maak_verkoopkans(page, bedrijf, notitie):
                    geslaagd += 1; log('  ✓ Opgeslagen')
                else:
                    mislukt.append(bedrijf['naam'])
                prog(i + 1, totaal)

            ctx.close()
            q.put({'type': 'done', 'geslaagd': geslaagd, 'mislukt': mislukt})

    except Exception as e:
        import traceback
        log(traceback.format_exc())
        q.put({'type': 'error', 'text': str(e)})
    finally:
        state['running'] = False


# ════════════════════════════════════════════════════════════════════════════
# Start
# ════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    port = 5050
    url  = f'http://127.0.0.1:{port}'
    print(f'\n  Exact Tool draait op {url}')
    print('  Sluit dit venster om de app te stoppen.\n')
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(port=port, debug=False, threaded=True)
