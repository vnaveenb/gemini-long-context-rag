"""Test configuration and shared fixtures."""

import os
import sys
from pathlib import Path

import pytest

# Ensure the project root is on PYTHONPATH
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Set test environment variables before anything else imports config
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-real")
