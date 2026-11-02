"""Save the API description, so the frontend can generate matching types."""

import json
import sys
from pathlib import Path

from costpilot.main import create_app

Path(sys.argv[1]).write_text(json.dumps(create_app().openapi(), indent=2) + "\n")
