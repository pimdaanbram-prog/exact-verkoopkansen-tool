#!/usr/bin/env python3
import os, glob
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIE   = os.path.join(BASE_DIR, 'browser_sessie')
BASE_URL = 'https://start.exactonline.nl'
SUSPECTS_URL = BASE_URL + '/docs/CRMAccounts.aspx?Status=S&Selector=List%3atList&_Division_=4021621&RelationManagerCode=2107693'

def wacht(p, ms=1500): p.wait_for_timeout(ms)

def verwijder_lock():
    for f in glob.glob(os.path.join(SESSIE, 'Singleton*')):
        try: os.remove(f)
        except: pass

def main():
    verwijder_lock()
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(SESSIE, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(BASE_URL + '/docs/MenuPortal.aspx')
        try: page.wait_for_load_state('networkidle', timeout=10000)
        except: pass
        wacht(page, 3000)
        url = page.url.lower()
        while 'returnurl' in url or 'login' in url:
            print('Log in via browser...')
            wacht(page, 3000)
            url = page.url.lower()
        page.goto(SUSPECTS_URL)
        try: page.wait_for_load_state('networkidle', timeout=15000)
        except: pass
        wacht(page, 3000)
        crm = None
        for f in page.frames:
            if 'CRMAccounts' in f.url: crm = f; break
        try: crm.wait_for_selector('#WaitMessageImg', state='hidden', timeout=20000)
        except: pass
        wacht(page, 1000)
        namen = []
        for rij in crm.query_selector_all('tr.DataDark, tr.DataLight'):
            for link in rij.query_selector_all('a'):
                href = link.get_attribute('href') or ''
                t = link.inner_text().strip()
                if t and len(t) > 2 and ('AccountID' in href or 'CRMAccount' in href):
                    namen.append(t); break
        print('ALLE BEDRIJVEN (' + str(len(namen)) + '):')
        for n in namen: print('  ' + n)
        ctx.close()

if __name__ == '__main__': main()
