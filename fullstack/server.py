#!/usr/bin/env python3
"""Assemble connector-sized UTF-8 source fragments, then run the tested EGM4000 server."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent


def joined(directory, suffix):
    return ''.join(
        p.read_text(encoding='utf-8')
        for p in sorted((ROOT / 'source_parts' / directory).glob('*' + suffix))
    )


app_js = joined('static_app', '.jsfrag')
(ROOT / 'static' / 'app.js').write_text(app_js, encoding='utf-8')

server_source = joined('server', '.pyfrag')

# Older split-source layouts placed the blocking HTTP server startup at the end
# of fragment 06. Newer route extensions live in later fragments, so starting
# there prevents those fragments from ever executing. Relocate the one startup
# block to the end of the fully assembled source before compiling/running it.
startup_block = """\nif __name__=='__main__':\n    print(f'EGM4000 public fullstack: http://{HOST}:{PORT}')\n    ThreadingHTTPServer((HOST,PORT),App).serve_forever()\n"""
if startup_block in server_source:
    server_source = server_source.replace(startup_block, '\n', 1).rstrip() + startup_block

compile(server_source, str(ROOT / 'server.generated.py'), 'exec')
if os.environ.get('EGM_ASSEMBLE_ONLY') == '1':
    print('EGM4000 source assembly verified.')
else:
    exec(compile(server_source, str(ROOT / 'server.generated.py'), 'exec'), globals(), globals())
