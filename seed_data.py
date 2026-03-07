"""Seed the database with sample reflections through the full pipeline."""
import os
import glob
from reflect.agent import build_reflection_graph, _init

def main():
    sample_dir = os.path.join(os.path.dirname(__file__), "data", "sample_reflections")
    files = sorted(glob.glob(os.path.join(sample_dir, "*.txt")))

    print(f"Found {len(files)} sample reflections to seed.\n")

    for i, filepath in enumerate(files):
        filename = os.path.basename(filepath)
        with open(filepath) as f:
            text = f.read().strip()

        print(f"[{i+1}/{len(files)}] Processing: {filename}")
        config = {"configurable": {"thread_id": f"seed-{i}"}}

        try:
            # Reconnect each time to avoid websocket timeout
            _init(force_reconnect=True)
            graph = build_reflection_graph()

            result = graph.invoke(
                {
                    "reflection_text": text,
                    "daily_prompt": None,
                    "messages": [],
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
