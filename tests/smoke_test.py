import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'src'))
from app import default_project, parse_patch, apply_changes, recommend_profile

p = default_project('Test')
assert p['room']['units'] == 'mm'
changes, clean = parse_patch('Тест\n<KITCHEN_PATCH>[{"target":"ROOM_01","property":"room.width","value":4200}]</KITCHEN_PATCH>')
p, applied = apply_changes(p, changes)
assert applied and p['room']['width'] == 4200
assert recommend_profile({'ram_gb': 8, 'gpu': ''}) == 'Lite'
assert recommend_profile({'ram_gb': 16, 'gpu': ''}) == 'Standard'
assert recommend_profile({'ram_gb': 64, 'gpu': ''}) == 'Pro'
print('SMOKE OK')
