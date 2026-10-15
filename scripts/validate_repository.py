"""Offline packaging checks; official HACS and Hassfest checks run in CI."""
import ast
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]


def validate():
    components = [p for p in (ROOT / 'custom_components').iterdir() if p.is_dir() and not p.name.startswith(('.', '__'))]
    assert len(components) == 1, 'HACS requires one integration per repository'
    integration = components[0]
    manifest = json.loads((integration / 'manifest.json').read_text())
    for key in ('domain', 'name', 'version', 'documentation', 'issue_tracker', 'codeowners'):
        assert manifest.get(key), f'Missing manifest field: {key}'
    assert manifest['domain'] == integration.name
    assert list(manifest) == ['domain', 'name'] + sorted(set(manifest) - {'domain', 'name'})
    hacs = json.loads((ROOT / 'hacs.json').read_text())
    assert hacs['name'] == manifest['name']
    assert not hacs.get('content_in_root', False)
    assert not hacs.get('zip_release', False), 'Source installs must not require release ZIP files'
    assert (ROOT / 'README.md').is_file()
    icon = (integration / 'brand/icon.png').read_bytes()
    assert icon[:8] == b'\x89PNG\r\n\x1a\n'
    width, height = struct.unpack('>II', icon[16:24])
    assert width == height and width >= 256
    for name in ('parser.py', 'schedule.py', 'cache.py'):
        assert (integration / 'lib' / name).read_bytes() == (ROOT / 'src/diablo_events' / name).read_bytes(), f'Regenerate bundled {name}'
    for path in integration.rglob('*.py'):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or '').startswith('diablo_events'), f'CLI import outside HACS package: {path}'
    assert json.loads((integration / 'strings.json').read_text()) == json.loads((integration / 'translations/en.json').read_text())
    print('Offline HACS packaging checks passed')


if __name__ == '__main__':
    validate()
