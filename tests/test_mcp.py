"""Real SDK subprocess test; fake only Zotero's authenticated HTTP endpoint."""
import json
import os
import sys
import unittest
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor')]
import runtime_bootstrap
import anyio
import pymupdf
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPTests(unittest.TestCase):
    def test_authenticated_context_pdf_and_selection_over_stdio(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            pdf_path = Path(folder) / 'sample.pdf'
            with pymupdf.open() as pdf:
                page = pdf.new_page()
                page.insert_text((72,72), 'Evidence: a reproducible local MCP test.')
                pdf.save(pdf_path)
            current = {'document_id':'test:ABC', 'path':str(pdf_path), 'page':1,
                       'title':'测试论文', 'selection':{'text':'reproducible', 'pages':[1]}}
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.headers.get('Authorization') != 'Bearer test-only-token':
                        self.send_response(401)
                        self.end_headers()
                        return
                    data = json.dumps(current, ensure_ascii=False).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type','application/json')
                    self.send_header('Content-Length',str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                def log_message(self, *args):
                    pass
            http = ThreadingHTTPServer(('127.0.0.1',0),Handler)
            thread = threading.Thread(target=http.serve_forever,daemon=True)
            thread.start()
            config = Path(folder) / 'config.json'
            config.write_text(json.dumps({'token':'test-only-token','port':http.server_port}),encoding='utf-8')
            async def check():
                params = StdioServerParameters(command=sys.executable,
                    args=['-B',str(ROOT / 'server.py'),'--config',str(config)],cwd=str(ROOT),
                    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
                async with stdio_client(params) as (read,write):
                    async with ClientSession(read,write) as session:
                        with anyio.fail_after(20):
                            await session.initialize()
                            result = await session.call_tool('get_reading_context',{})
                            self.assertFalse(result.is_error)
                            snap = json.loads(result.content[0].text)
                            self.assertEqual(snap['title'],'测试论文')
                            self.assertEqual(snap['selection']['text'],'reproducible')
                            sid = snap['snapshot_id']
                            current.clear()
                            current['error'] = 'no_active_reader'
                            result = await session.call_tool('read_pages',{'snapshot_id':sid,'first_page':1,'last_page':1})
                            self.assertIn('Evidence',result.content[0].text)
                            result = await session.call_tool('search_paper',{'snapshot_id':sid,'query':'reproducible'})
                            self.assertIn('reproducible',result.content[0].text)
                            result = await session.call_tool('get_page_image',{'snapshot_id':sid,'page':1})
                            self.assertEqual(result.content[0].type,'image')
                            result = await session.call_tool('get_reading_context',{})
                            self.assertTrue(result.is_error)
                            self.assertIn('no_active_reader',result.content[0].text)
            try:
                anyio.run(check)
            finally:
                http.shutdown()
                http.server_close()
                thread.join(timeout=2)

    def test_stdio_handshake_tools_and_no_reader_error(self):
        async def check():
            params = StdioServerParameters(command=sys.executable,
                args=['-B', str(ROOT / 'server.py')], cwd=str(ROOT),
                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    with anyio.fail_after(20):
                        await session.initialize()
                        listed = await session.list_tools()
                        self.assertEqual({t.name for t in listed.tools},
                            {'get_reading_context','read_pages','search_paper','get_page_image'})
                        result = await session.call_tool('read_pages',
                            {'snapshot_id':'unknown','first_page':1,'last_page':1})
                        self.assertTrue(result.is_error)
        anyio.run(check)


if __name__ == '__main__':
    unittest.main()
