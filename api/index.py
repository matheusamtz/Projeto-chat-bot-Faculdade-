"""Entrypoint serverless da Vercel. Expoe o Flask `app` para o runtime @vercel/python."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app  # noqa: E402,F401
