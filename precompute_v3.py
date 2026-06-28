"""
precompute_v3.py

Builds the V3.10 SQLite Knowledge Store from the
existing precomputed JSON artifacts.

Usage
-----
python precompute_v3.py
"""

from knowledge.storage import initialize_database, table_counts
from knowledge.ingest import ingest_all


def main() -> None:
    print("\n=== Sententia V3 Knowledge Builder ===\n")

    print("[1/3] Initializing database...")
    initialize_database()

    print("[2/3] Importing artifacts...")
    stats = ingest_all()

    print("\nImported:")
    for name, count in stats.items():
        print(f"  {name:<24} {count}")

    print("\n[3/3] Verifying database...")

    counts = table_counts()

    print("\nSQLite Row Counts")
    print("-" * 40)

    for table, count in counts.items():
        print(f"{table:<24} {count}")

    print("\nKnowledge Store ready.\n")


if __name__ == "__main__":
    main()