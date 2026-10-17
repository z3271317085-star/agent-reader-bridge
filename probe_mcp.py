"""Probe the installed Zotero -> real STDIO MCP chain without a model call."""
import runtime_bootstrap

import argparse
import json
import os
import sys
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent


async def probe(include_page=False):
    params = StdioServerParameters(command=sys.executable,
        args=['-B', str(ROOT / 'server.py')], cwd=str(ROOT),
        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            with anyio.fail_after(30):
                await session.initialize()
                listed = await session.list_tools()
                result = await session.call_tool('get_reading_context', {})
                output = {'transport': 'stdio', 'tools': [t.name for t in listed.tools]}
                if result.is_error:
                    output['error'] = result.content[0].text
                    print(json.dumps(output, ensure_ascii=False, indent=2))
                    return False
                context = json.loads(result.content[0].text)
                selection = context.get('selection', {})
                output['context'] = {key: context.get(key) for key in (
                    'title', 'document_id', 'reader_id', 'page', 'page_label',
                    'page_count', 'view', 'revision', 'captured_at', 'snapshot_id')}
                output['selection'] = {'text': selection.get('text', '')[:1000],
                    'pages': selection.get('pages', []),
                    'truncated_for_display': len(selection.get('text', '')) > 1000}
                if include_page:
                    # A selected passage can be on the next visible page even
                    # while Zotero's persisted viewport anchor is on the prior one.
                    relevant = sorted({context['page'], *selection.get('pages', [])})[:10]
                    output['pages_read'] = relevant
                    output['selected_page_context'] = []
                    for selected_page in relevant:
                        if selected_page == context['page']:
                            continue
                        selected_result = await session.call_tool('read_pages', {
                            'snapshot_id': context['snapshot_id'],
                            'first_page': selected_page, 'last_page': selected_page})
                        if selected_result.is_error:
                            output['page_error'] = selected_result.content[0].text
                            continue
                        selected_data = json.loads(selected_result.content[0].text)
                        for selected in selected_data['pages']:
                            output['selected_page_context'].append({**selected,
                                'text': selected['text'][:6000],
                                'truncated_for_display': len(selected['text']) > 6000})
                    result = await session.call_tool('read_pages', {
                        'snapshot_id': context['snapshot_id'],
                        'first_page': context['page'], 'last_page': context['page']})
                    if result.is_error:
                        output['page_error'] = result.content[0].text
                    else:
                        data = json.loads(result.content[0].text)
                        page = data['pages'][0]
                        output['current_page'] = {**page, 'text': page['text'][:4000],
                            'truncated_for_display': len(page['text']) > 4000}
                print(json.dumps(output, ensure_ascii=False, indent=2))
                return 'page_error' not in output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pages', action='store_true', help='Also read the current physical page')
    args = parser.parse_args()
    if not anyio.run(probe, args.pages):
        raise SystemExit(1)
