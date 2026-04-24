"""Seed the database with sample reflections through the full pipeline.

Usage:
    uv run python seed_data.py                         # seeds for first user found in DB
    uv run python seed_data.py --user-id 'app_user:xxx' # seeds for a specific user
"""
import argparse
import os
import glob
from reflect.agent import build_reflection_graph, _init

def _resolve_user_id(explicit: str | None) -> str | None:
    """Return an explicit user_id, or look up the first registered user."""
    if explicit:
        return explicit
    _init()
    from reflect.agent import _conn
    if _conn is None:
        return None
    rows = _conn.query("SELECT id FROM app_user LIMIT 1")
    if rows and isinstance(rows, list) and rows[0].get("id"):
        uid = str(rows[0]["id"])
        print(f"Auto-resolved user: {uid}")
        return uid
    print("WARNING: No users found in DB — seeding without user_id (data won't appear in dashboard)")
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", default=None, help="SurrealDB user record id (e.g. 'app_user:abc123')")
    args = parser.parse_args()

    user_id = _resolve_user_id(args.user_id)

    sample_dir = os.path.join(os.path.dirname(__file__), "data", "sample_reflections")
    files = sorted(glob.glob(os.path.join(sample_dir, "*.txt")))

    print(f"Found {len(files)} sample reflections to seed (user_id={user_id}).\n")

    for i, filepath in enumerate(files):
        filename = os.path.basename(filepath)
        with open(filepath) as f:
            text = f.read().strip()

        print(f"[{i+1}/{len(files)}] Processing: {filename}")
        config = {"configurable": {"thread_id": f"seed-{i}"}}

        try:
            _init(force_reconnect=True)
            graph = build_reflection_graph()

            result = graph.invoke(
                {
                    "reflection_text": text,
                    "daily_prompt": None,
                    "messages": [],
                    "user_id": user_id,
                },
                config=config,
            )

            patterns = [p["name"] for p in result.get("extracted", {}).get("patterns", [])]
            emotions = [e["name"] for e in result.get("extracted", {}).get("emotions", [])]
            print(f"  Patterns: {patterns}")
            print(f"  Emotions: {emotions}")
            print(f"  Insights: {result.get('insights', '')[:100]}...")
            print()
        except Exception as e:
            print(f"  ERROR: {e}")
            print()

    print("Seeding complete!")


if __name__ == "__main__":
    main()
