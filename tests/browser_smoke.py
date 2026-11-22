"""CI-only Chromium checks at a GitHub Pages project subpath."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def main():
    shots=ROOT/'browser-checks';shots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        shutil.copytree(ROOT/'dist',Path(temp)/ROOT.name)
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=temp))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch()
                page=browser.new_page(viewport={'width':1280,'height':1000})
                errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/{ROOT.name}/')
                page.locator('#edition').filter(has_text='Captured').wait_for()
                assert page.locator('#documents button').count()==4
                page.locator('#before').select_option('')
                page.locator('#baseline').filter(has_text='baseline').wait_for()
                assert page.locator('#units details').count()>20
                page.locator('#units summary').first.click()
                assert 'Definitions' in page.locator('#units details').first.inner_text()
                page.locator('#search').fill('access')
                assert page.locator('#units details').count()>0
                page.locator('#search').fill('<img src=x onerror=alert(1)>')
                assert page.locator('#units details').count()==0
                assert page.locator('img').count()==0
                page.locator('#search').fill('')
                page.locator('#change-filter').select_option('changed')
                assert 'No units match' in page.locator('#units').inner_text()
                page.locator('#change-filter').select_option('all')
                page.locator('#documents button').filter(has_text='Personal Information Protection Act Regulations').click()
                page.locator('#evidence summary').click()
                assert 'Document amendment metadata' in page.locator('#evidence').inner_text()
                assert '2027-08-01' in page.locator('#evidence').inner_text()
                with page.expect_download() as event: page.locator('#export').click()
                assert event.value.suggested_filename=='lawdelta-sections.csv'
                page.locator('#documents button').first.click()
                page.locator('#units summary').first.click()

                page.screenshot(path=str(shots/'desktop.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal mobile overflow'
                page.screenshot(path=str(shots/'mobile.png'),full_page=True)
                assert not errors,errors
                browser.close()
        finally: server.shutdown()
    print('Browser checks passed: subpath, real data, filters, export, safe text, desktop and mobile')
if __name__=='__main__':main()
