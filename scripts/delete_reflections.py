"""Delete specific reflections cleanly: edges first, then the reflection rows,
then any extracted-entity nodes that would otherwise be left orphaned (zero
remaining edges) for that user.

DEFAULT IS DRY RUN. Use --apply to actually mutate the DB.

Usage:
    uv run python -m scripts.delete_reflections \\
        --user-id app_user:xxx \\
        --reflection-id reflection:abc \\
        --reflection-id reflection:def

    uv run python -m scripts.delete_reflections \\
        --user-id app_user:xxx \\
        --reflection-id reflection:abc --apply
"""
from __future__ import annotations

import argparse

from reflect.db import get_connection


# Edge tables and which side of the edge points at the reflection.
# All seven reflection-attached edge types defined in reflect/db.py SCHEMA_STATEMENTS.
REFLECTION_EDGE_TABLES = [
    "reveals",        # reflection -> pattern
    "expresses",      # reflection -> emotion
    "about",          # reflection -> theme
    "activates",      # reflection -> ifs_part
    "triggers_schema",# reflection -> schema_pattern
    "mentions",       # reflection -> person
    "feels_in_body",  # reflection -> body_signal
]

# Node tables that may become orphaned (no incoming reflection edge).
# Each entry: (node_table, edge_table_pointing_in)
NODE_INCOMING = [
    ("pattern", "reveals"),
    ("emotion", "expresses"),
    ("theme", "about"),
    ("ifs_part", "activates"),
    ("schema_pattern", "triggers_schema"),
    ("person", "mentions"),
    ("body_signal", "feels_in_body"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-id", required=True)
    ap.add_argument("--reflection-id", action="append", required=True,
                    help="Reflection record id, e.g. reflection:abc. Repeatable.")
    ap.add_argument("--apply", action="store_true",
                    help="actually mutate (default is dry-run)")
    args = ap.parse_args()

    conn = get_connection()
    user_id_str = args.user_id
    targets = args.reflection_id

    # --- Verify each reflection exists and belongs to the user. ---
    print(f"=== Verifying {len(targets)} reflection(s) for user {user_id_str} ===\n")
    valid_targets = []
    for rid in targets:
        rows = conn.query(
            f"SELECT id, user_id, source, daily_prompt, text FROM {rid}"
        )
        if not rows or isinstance(rows, str):
            print(f"  SKIP {rid}: not found")
            continue
        row = rows[0]
        if row.get("user_id") != user_id_str:
            print(f"  SKIP {rid}: belongs to user_id={row.get('user_id')}, not {user_id_str}")
            continue
        valid_targets.append(row)
        text_preview = (row.get("text") or "")[:80].replace("\n", " ")
        print(f"  OK  {rid}")
        print(f"      source: {row.get('source')}  prompt: {row.get('daily_prompt')!r}")
        print(f"      text: {text_preview}…")
    print()

    if not valid_targets:
        print("No valid targets. Exiting.")
        return

    target_ids = [r["id"] for r in valid_targets]  # RecordID objects

    # --- Inventory edges we'd delete. ---
    print("=== Edges that will be deleted ===")
    edge_inventory: dict[str, list] = {}
    for tbl in REFLECTION_EDGE_TABLES:
        all_edges = []
        for rid in target_ids:
            edges = conn.query(
                f"SELECT id, in, out FROM {tbl} WHERE in = $rid",
                {"rid": rid},
            )
            all_edges.extend(edges or [])
        edge_inventory[tbl] = all_edges
        print(f"  {tbl}: {len(all_edges)} edge(s)")
    print()

    # --- Determine which extracted-entity nodes would become orphaned. ---
    print("=== Nodes that would become orphaned (0 edges remaining) and be deleted ===")
    orphan_plan: dict[str, list] = {}
    for node_tbl, edge_tbl in NODE_INCOMING:
        # Collect distinct outgoing endpoints of edges we're about to delete.
        endpoints = {str(e["out"]) for e in edge_inventory.get(edge_tbl, [])}
        becoming_orphan = []
        for ep in endpoints:
            # Total incoming edges of this type for that node, scoped to this user.
            total = conn.query(
                f"SELECT count() AS c FROM {edge_tbl} WHERE out = {ep} GROUP ALL"
            )
            total_count = total[0]["c"] if total and not isinstance(total, str) else 0
            # Edges from our targets pointing to this endpoint.
            from_targets = sum(
                1 for e in edge_inventory.get(edge_tbl, []) if str(e["out"]) == ep
            )
            if total_count == from_targets:
                node = conn.query(f"SELECT id, name FROM {ep}")
                if node and not isinstance(node, str):
                    becoming_orphan.append(node[0])
        orphan_plan[node_tbl] = becoming_orphan
        print(f"  {node_tbl}: {len(becoming_orphan)} would be deleted")
        for n in becoming_orphan:
            print(f"     - {n['name']!r}  ({n['id']})")
    print()

    print(f"Summary: would delete {len(target_ids)} reflection(s), "
          f"{sum(len(v) for v in edge_inventory.values())} edge(s), "
          f"{sum(len(v) for v in orphan_plan.values())} orphaned node(s)")

    if not args.apply:
        print("\nDRY RUN. Re-run with --apply to commit.")
        return

    # --- Apply: delete edges, then reflections, then orphaned nodes. ---
    print("\nApplying deletes…")
    for tbl, edges in edge_inventory.items():
        for e in edges:
            conn.query(f"DELETE {e['id']}")
        if edges:
            print(f"  deleted {len(edges)} {tbl} edge(s)")

    for rid in target_ids:
        conn.query(f"DELETE {rid}")
    print(f"  deleted {len(target_ids)} reflection(s)")

    # Also try to remove the corresponding vector-store documents so semantic
    # search doesn't keep returning text for deleted reflections.
    for rid in target_ids:
        # The vector-store docs typically reference reflection_id in metadata.
        try:
            conn.query(
                "DELETE documents WHERE metadata.reflection_id = $rid",
                {"rid": str(rid)},
            )
        except Exception as exc:
            print(f"  (vector-store cleanup skipped for {rid}: {exc})")

    for node_tbl, nodes in orphan_plan.items():
        for n in nodes:
            conn.query(f"DELETE {n['id']}")
        if nodes:
            print(f"  deleted {len(nodes)} orphaned {node_tbl} node(s)")

    print("\nDone.")


if __name__ == "__main__":
    main()
