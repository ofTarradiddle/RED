#!/usr/bin/env python3
"""Serve only the validated public release, never source files or ledgers."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from publishing.private_nav import PRIVATE_ROUTE, render_dashboard
from publishing.private_spy import render as render_spy

ROOT = Path(__file__).resolve().parent
REFRESH_STATE={'running':False,'message':'Ready. Refresh updates dated holdings, prices, dividend accruals and the daily unitary expense.'}
REFRESH_LOCK=threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        request=urlsplit(self.path)
        if request.path == PRIVATE_ROUTE:
            if self.headers.get('Host','') not in (f'localhost:{self.server.server_port}',f'127.0.0.1:{self.server.server_port}'):
                self.send_error(403,'Local host required');return None
            try:
                if parse_qs(request.query).get('view')!=['scenario']:
                    path=ROOT/'data/shadow_spy/latest.json'
                    report=json.loads(path.read_text()) if path.exists() else None
                    return self.html_response(render_spy(report,REFRESH_STATE.copy()))
                from publishing.workbook import import_workbook
                snapshot=import_workbook(ROOT/'workbooks/hetzerk-demo.xlsx')
                fund=next(f for f in snapshot['funds'] if f['fund_id']=='redi')
                return self.html_response(render_dashboard(fund,parse_qs(request.query,keep_blank_values=True)))
            except ValueError as exc:
                self.send_error(400,str(exc))
                return None
        path=Path(self.translate_path(self.path))
        if path.is_dir(): path=path/'index.html'
        if path.is_file() and path.suffix=='.html':
            html=path.read_text()
            # Only the localhost server activates this otherwise ordinary word.
            html=html.replace('<span data-perspective-word="">Perspective</span>',f'<a class="perspective-word" href="{PRIVATE_ROUTE}" aria-label="Open personal review">Perspective</a>')
            return self.html_response(html)
        return super().send_head()

    def do_POST(self):
        if urlsplit(self.path).path != PRIVATE_ROUTE+'refresh':
            self.send_error(404);return
        # A browser cannot trigger this localhost mutation cross-origin.
        host=self.headers.get('Host','')
        origin=self.headers.get('Origin','')
        if host not in (f'localhost:{self.server.server_port}',f'127.0.0.1:{self.server.server_port}') or origin not in (f'http://{host}',):
            self.send_error(403,'Same-origin local form required');return
        with REFRESH_LOCK:
            if not REFRESH_STATE['running']:
                REFRESH_STATE.update(running=True,message='Refresh running. Reload results in a few minutes; the previous release remains available.')
                def run():
                    try:
                        log=ROOT/'data/shadow_spy/refresh.log';log.parent.mkdir(parents=True,exist_ok=True)
                        with log.open('w') as out:
                            result=subprocess.run([sys.executable,'-m','scripts.refresh_spy','--build'],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=1800)
                        message='Refresh complete. Latest dated results are below.' if result.returncode==0 else 'Refresh failed. Previous public release retained; see data/shadow_spy/refresh.log.'
                    except Exception as exc: message=f'Refresh failed: {exc}'
                    with REFRESH_LOCK: REFRESH_STATE.update(running=False,message=message)
                threading.Thread(target=run,daemon=True).start()
        self.send_response(303);self.send_header('Location',PRIVATE_ROUTE);self.end_headers()

    def html_response(self, html):
        body=html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        return BytesIO(body)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        connect = "'self'"
        try:
            config = json.loads((ROOT / 'dist/innovation/config.json').read_text())
            endpoint = urlsplit(config.get('leaderboardUrl') or '')
            if endpoint.scheme == 'https' and endpoint.hostname and not endpoint.username and not endpoint.password:
                connect += f' https://{endpoint.netloc}'
        except (OSError, ValueError, TypeError):
            pass
        self.send_header('Content-Security-Policy', f"default-src 'self'; connect-src {connect}; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        super().end_headers()

    def list_directory(self, path):
        self.send_error(404, 'Page not found')
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    if not (ROOT/'dist/index.html').exists():
        from publishing.build import build
        build(ROOT/'workbooks/hetzerk-demo.xlsx')
    handler = partial(Handler, directory=str(ROOT/'dist'))
    with ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
        print(f'Hetzerk local review: http://localhost:{args.port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
