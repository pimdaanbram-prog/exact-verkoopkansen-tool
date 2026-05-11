#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, json, os, glob
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIE   = os.path.join(BASE_DIR, 'browser_sessie')
BASE_URL = 'https://start.exactonline.nl'
SUSPECTS_URL = BASE_URL + '/docs/CRMAccounts.aspx?Status=S&Selector=List%3atList&_Division_=4021621&RelationManagerCode=2107693'
DATA_FILE = os.path.join(BASE_DIR, 'bedrijven_data.json')
NAAM      = 'belcentrum 12-05-26 Tim. S'
SLUITDATUM = '12-05-2026'

def wacht(p, ms=1500):
    p.wait_for_timeout(ms)

def verwijder_lock():
    for f in glob.glob(os.path.join(SESSIE, 'Singleton*')):
        try: os.remove(f)
        except: pass

def is_ingelogd(page):
    url = page.url.lower()
    return ('exactonline.nl' in url and 'returnurl' not in url
            and 'login' not in url and 'oauth' not in url and 'adfs' not in url)

def wacht_op_login(page):
    teller = 0
    while teller < 120:
        if is_ingelogd(page):
            print('Ingelogd!'); return True
        if teller == 0:
            print('=== LOG IN VIA DE BROWSER - script wacht automatisch ===')
        wacht(page, 2000); teller += 2
        try: page.wait_for_load_state('networkidle', timeout=3000)
        except: pass
    return False

def wacht_op_laden(frame, timeout=20000):
    try: frame.wait_for_selector('#WaitMessageImg', state='hidden', timeout=timeout)
    except: pass
    wacht(frame, 1000)

def zoek_frame(page, zoekterm):
    for f in page.frames:
        if zoekterm in f.url: return f
    return None

def get_bedrijven(frame):
    bedrijven = []
    for rij in frame.query_selector_all('tr.DataDark, tr.DataLight'):
        for link in rij.query_selector_all('a'):
            href = link.get_attribute('href') or ''
            tekst = link.inner_text().strip()
            if tekst and len(tekst) > 2 and ('AccountID' in href or 'CRMAccount' in href):
                bedrijven.append({'naam': tekst, 'url': href}); break
    if not bedrijven:
        for rij in frame.query_selector_all('tr'):
            rij_id = rij.get_attribute('id') or ''
            if 'crit' in rij_id or 'Header' in (rij.get_attribute('class') or ''): continue
            for link in rij.query_selector_all('a'):
                href = link.get_attribute('href') or ''
                tekst = link.inner_text().strip()
                if tekst and len(tekst) > 2 and ('AccountID' in href or 'CRMAccount' in href):
                    bedrijven.append({'naam': tekst, 'url': href}); break
    return bedrijven

def laad_notitie(bedrijf_naam, data):
    for key, info in data.items():
        k = key.strip().lower()
        b = bedrijf_naam.strip().lower()
        if k == b or k in b or b in k:
            regels = []
            if info.get('wat'):   regels.append('Wat: ' + info['wat'])
            if info.get('groot'): regels.append('Grootte: ' + info['groot'])
            if info.get('dmu'):   regels.append('DMU: ' + info['dmu'])
            if info.get('kans'):  regels.append('Kans: ' + info['kans'])
            return '\n'.join(regels)
    return 'Geen data beschikbaar'

def maak_verkoopkans(page, bedrijf, notitie_tekst):
    naam = bedrijf['naam']
    url  = bedrijf['url']
    print('  Bezig: ' + naam)

    # Navigeer naar bedrijfspagina
    if url.startswith('http'):   full_url = url
    elif url.startswith('/'):    full_url = BASE_URL + url
    else:                        full_url = BASE_URL + '/docs/' + url
    page.goto(full_url)
    try: page.wait_for_load_state('networkidle', timeout=15000)
    except: pass
    wacht(page, 2000)

    # Zoek account frame
    account_frame = None
    for f in page.frames:
        if 'CRMAccountCard' in f.url or ('CRMAccount' in f.url and 'Accounts.aspx' not in f.url):
            account_frame = f; break
    if not account_frame:
        print('  FOUT: account frame niet gevonden'); return False

    # Zoek SFAOpportunity link
    vk_url = None
    for link in account_frame.query_selector_all('a'):
        href = link.get_attribute('href') or ''
        if 'SFAOpportunity.aspx' in href and 'BCAction=0' in href:
            vk_url = href; break
    if not vk_url:
        print('  FOUT: verkoopkans link niet gevonden'); return False

    # Navigeer naar formulier
    full_vk = BASE_URL + '/docs/' + vk_url if not vk_url.startswith('http') else vk_url
    page.goto(full_vk)
    try: page.wait_for_load_state('networkidle', timeout=15000)
    except: pass
    wacht(page, 2000)

    # Zoek formulier frame
    form_frame = None
    for f in page.frames:
        if 'SFAOpportunity' in f.url:
            form_frame = f; break
    if not form_frame:
        form_frame = page.main_frame

    # 1. Omschrijving
    try:
        inputs = form_frame.query_selector_all('input[type="text"]')
        if inputs:
            inputs[0].click()
            inputs[0].fill(NAAM)
            print('  Omschrijving: ' + NAAM)
    except Exception as e:
        print('  Fout omschrijving: ' + str(e))

    wacht(page, 500)

    # 2. Fase = VB
    try:
        inputs = form_frame.query_selector_all('input[type="text"]')
        if len(inputs) >= 2:
            inputs[1].click()
            inputs[1].triple_click()
            inputs[1].type('VB')
            wacht(page, 1000)
            inputs[1].press('Enter')
            wacht(page, 500)
            print('  Fase: VB')
    except Exception as e:
        print('  Fout fase: ' + str(e))

    wacht(page, 500)

    # 3. Sluitingsdatum - typ karakter voor karakter
    try:
        inputs = form_frame.query_selector_all('input[type="text"]')
        if len(inputs) >= 3:
            d = inputs[2]
            d.click()
            wacht(page, 2000)
            page.keyboard.type('12', delay=200)
            wacht(page, 500)
            page.keyboard.type('05', delay=200)
            wacht(page, 500)
            page.keyboard.type('2026', delay=200)
            wacht(page, 2000)
            val = d.input_value()
            print('  Datum: ' + str(val))
            d.press('Tab')
            wacht(page, 1000)
        else:
            print('  WAARSCHUWING: datum veld niet gevonden (inputs: ' + str(len(inputs)) + ')')
    except Exception as e:
        print('  Fout datum: ' + str(e))

    wacht(page, 500)

    # 4. Notities - tijdstempel + tekst
    try:
        notitie_area = form_frame.query_selector('textarea')
        if notitie_area:
            notitie_area.click()
            wacht(page, 500)
            # Zoek tijdstempel knop op meerdere manieren
            tijdstempel = form_frame.query_selector('input[value="Tijdstempel"]')
            if not tijdstempel:
                tijdstempel = form_frame.query_selector('button:has-text("Tijdstempel")')
            if not tijdstempel:
                for el in form_frame.query_selector_all('input[type="button"], input[type="submit"], button'):
                    if 'Tijdstempel' in (el.get_attribute('value') or el.inner_text()):
                        tijdstempel = el; break
            if tijdstempel:
                tijdstempel.click()
                wacht(page, 1000)
                print('  Tijdstempel toegevoegd')
            else:
                print('  WAARSCHUWING: tijdstempel knop niet gevonden')
            notitie_area.press('End')
            notitie_area.type('\n' + notitie_tekst)
            print('  Notitie ingevuld')
        else:
            print('  WAARSCHUWING: notitie niet gevonden')
    except Exception as e:
        print('  Fout notitie: ' + str(e))

    wacht(page, 500)

    # 5. Opslaan
    try:
        opslaan = None
        for f in [form_frame, page.main_frame]:
            opslaan = f.query_selector('input[value="Opslaan"]')
            if opslaan: break
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
            wacht(page, 2000)
            print('  Opgeslagen!')
            return True
        else:
            print('  FOUT: Opslaan knop niet gevonden')
            return False
    except Exception as e:
        print('  Fout opslaan: ' + str(e)); return False

def main():
    verwijder_lock()
    data = {}
    if os.path.exists(DATA_FILE):
        raw = json.load(open(DATA_FILE, encoding='utf-8'))
        data = raw.get('info', {})
        print('Data: ' + str(len(data)) + ' bedrijven geladen')
    else:
        print('WAARSCHUWING: bedrijven_data.json niet gevonden')

    try:
        with sync_playwright() as p:
            os.makedirs(SESSIE, exist_ok=True)
            ctx = p.chromium.launch_persistent_context(
                SESSIE, headless=False, viewport={'width': 1400, 'height': 900}
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            wacht(page, 2000)

            page.goto(BASE_URL + '/docs/MenuPortal.aspx')
            try: page.wait_for_load_state('networkidle', timeout=10000)
            except: pass
            wacht(page, 2000)

            if not wacht_op_login(page):
                input('Niet ingelogd. Enter -> '); ctx.close(); return

            print('Navigeren naar suspects...')
            page.goto(SUSPECTS_URL)
            try: page.wait_for_load_state('networkidle', timeout=15000)
            except: pass
            wacht(page, 3000)

            crm_frame = zoek_frame(page, 'CRMAccounts')
            if not crm_frame:
                print('FOUT: CRM frame niet gevonden')
                input('Enter -> '); ctx.close(); return

            wacht_op_laden(crm_frame)
            bedrijven = get_bedrijven(crm_frame)
            print('Gevonden: ' + str(len(bedrijven)) + ' bedrijven')

            if not bedrijven:
                print('Geen bedrijven!'); input('Enter -> '); ctx.close(); return

            print('')
            print('Naam:           ' + NAAM)
            print('Sluitingsdatum: ' + SLUITDATUM)
            print('Fase:          VB (Voorbereid)')
            print('Bedrijven:     ' + str(len(bedrijven)))
            bevestig = input('\nStarten? (ja/nee): ')
            if bevestig.lower() not in ['ja', 'j', 'yes', 'y']:
                print('Gestopt.'); ctx.close(); return

            geslaagd = 0
            mislukt = []
            for i, bedrijf in enumerate(bedrijven):
                print('')
                print('[' + str(i+1) + '/' + str(len(bedrijven)) + '] ' + bedrijf['naam'])
                notitie = laad_notitie(bedrijf['naam'], data)
                ok = maak_verkoopkans(page, bedrijf, notitie)
                if ok: geslaagd += 1
                else: mislukt.append(bedrijf['naam'])

            print('')
            print('=== KLAAR ===')
            print('Geslaagd: ' + str(geslaagd) + '/' + str(len(bedrijven)))
            if mislukt:
                print('Mislukt:')
                for m in mislukt: print('  - ' + m)

            input('Druk Enter om te sluiten -> ')
            ctx.close()

    except Exception as e:
        import traceback
        print('FOUT: ' + str(e))
        traceback.print_exc()
        input('Druk Enter om te sluiten -> ')

if __name__ == '__main__': main()
