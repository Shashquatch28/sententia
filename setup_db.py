"""
setup_db.py

One-time script: initialises the SQLite knowledge store and
imports all precomputed JSON artifacts into it.

Run from the project root:
    .venv\Scripts\python setup_db.py
"""

from knowledge.storage import initialize_database, table_counts
from knowledge.ingest import ingest_all

print("Creating database schema...")
initialize_database()

print("Ingesting precomputed data...")
stats = ingest_all()

print("\n--- Done ---")
for table, count in stats.items():
    print(f"  {table}: {count} rows")

print("\nVerifying...")
counts = table_counts()
for table, count in counts.items():
    print(f"  {table}: {count} rows")

print("\nSQLite knowledge store is ready at data/hireiq.db")
