#!/usr/bin/env python3
"""Assemble connector-sized UTF-8 source fragments, then run the tested EGM4000 server."""
from pathlib import Path
import os
ROOT=Path(__file__).resolve().parent

def joined(directory, suffix):
    return ''.join(p.read_text(encoding='utf-8') for p in sorted((ROOT/'source_parts'/directory).glob('*'+suffix)))

app_js=joined('static_app','.jsfrag')
(ROOT/'static'/'app.js').write_text(app_js,encoding='utf-8')
server_source=joined('server','.pyfrag')
compile(server_source,str(ROOT/'server.generated.py'),'exec')
if os.environ.get('EGM_ASSEMBLE_ONLY')=='1':
    print('EGM4000 source assembly verified.')
else:
    exec(compile(server_source,str(ROOT/'server.generated.py'),'exec'),globals(),globals())
