import os
import sys

# Ensure project root is on sys.path when running: python scripts/test_models.py
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from models.base import Base
from models import rag_models  # noqa: F401  (forces model import/registration)
from db import engine  # <-- this must point to your SQLAlchemy engine


def main():
    Base.metadata.create_all(bind=engine)
    print("✅ RAG tables verified (SQLAlchemy models imported + create_all ran)")


if __name__ == "__main__":
    main()
