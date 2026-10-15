"""Bundle canonical CLI modules for a self-contained custom integration."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for name in ('parser.py', 'schedule.py', 'cache.py'):
    source = root / 'src/diablo_events' / name
    target = root / 'custom_components/diablo_worldboss/lib' / name
    target.write_text(source.read_text())
