"""Build the paired XPI and client config snippets, exclusively in this project."""
import hashlib
import json
import secrets
import sys
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
DIST = ROOT / 'dist'
DIST.mkdir(exist_ok=True)
config_path = ROOT / 'runtime.json'
if not config_path.exists():
    config_path.write_text(json.dumps({'token': secrets.token_urlsafe(32)}, indent=2), encoding='utf-8')
config = json.loads(config_path.read_text(encoding='utf-8'))
token = config['token']
# Keep the unpacked development plugin installable too. Never print the token.
(ROOT / 'plugin' / 'secret.js').write_text('var AGENT_READER_TOKEN = ' + json.dumps(token) + ';\n', encoding='utf-8')
manifest = json.loads((ROOT / 'plugin/manifest.json').read_text(encoding='utf-8'))
package = DIST / f"agent-reader-bridge-{manifest['version']}.xpi"
with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in ['manifest.json', 'bootstrap.js', 'adapter.js', 'secret.js']:
        archive.write(ROOT / 'plugin' / name, name)

python = sys.executable
command_args = ['-B', str(ROOT / 'server.py')]
toml = ('[mcp_servers.zotero_reader]\n'
        f'command = {json.dumps(python, ensure_ascii=False)}\n'
        f'args = {json.dumps(command_args, ensure_ascii=False)}\n'
        'startup_timeout_sec = 30\n'
        'tool_timeout_sec = 90\n'
        '[mcp_servers.zotero_reader.env]\n'
        'PYTHONDONTWRITEBYTECODE = "1"\n')
(DIST / 'codex-config.toml').write_text(toml, encoding='utf-8')
(DIST / 'agent-config.json').write_text(json.dumps({'mcpServers': {'zotero_reader': {
    'command': python, 'args': command_args, 'env': {'PYTHONDONTWRITEBYTECODE':'1'}
}}}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
sha = hashlib.sha256(package.read_bytes()).hexdigest()
(DIST / 'SHA256SUMS.txt').write_text(f'{sha}  {package.name}\n', encoding='utf-8')
print(json.dumps({'xpi':str(package), 'sha256':sha, 'client_configs':['codex-config.toml','agent-config.json']}, ensure_ascii=False))
