import json
from pathlib import Path
from backend.main import app
Path('frontend/openapi.json').write_text(json.dumps(app.openapi(),indent=2))
