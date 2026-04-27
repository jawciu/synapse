"""One-shot migration: collapse near-duplicate themes for a user.

Uses the same vector-KNN approach as `upsert_theme`'s runtime dedup.
For each cluster of themes within the cosine-distance threshold, picks a canonical
theme (highest mentions → shortest name → alphabetic) and re-points all `about`
edges from the duplicates to the canonical, then deletes the duplicate theme nodes.

DEFAULT IS DRY RUN. Use --apply to actually mutate the DB.

Usage:
    uv run python scripts/dedup_themes.py --user-id app_user:vlt4gahyig9r8erdmjge
    uv run python scripts/dedup_themes.py --user-id <id> --apply
    uv run python scripts/dedup_themes.py --user-id <id> --threshold 0.40 --apply
"""
from __future__ import annotations

import argparse
import sys
from reflect.db import get_connection


def _theme_rank(t: dict) -> tuple:
    """Higher mentions → shorter name → alphabetic comes first."""
    return (-int(t.get("mentions") or 0), len(t["name"]), t["name"])


def find_clusters(themes: list[dict], threshold: float, conn) -> list[list[dict]]:
    """Greedy non-transitive clustering.

    Sort themes from most-established to least. The first theme starts a cluster
    as its own canonical. Each subsequent theme T runs one KNN to find its top-K
    neighbors; if any of those neighbors is already a canonical AND within
    threshold, T joins the closest such canonical. Otherwise T becomes a new
    canonical.

    This deliberately avoids transitive chains: theme T only joins canonical C
    if direct distance(T, C) ≤ threshold, never via an intermediate hop. Cost
    is O(N) KNN queries instead of O(N²) pairwise.
    """
    sorted_themes = sorted(themes, key=_theme_rank)
    user_id = themes[0]["user_id"]

    canonicals: list[dict] = []
    canonical_names: set[str] = set()
    cluster_of: dict[str, dict] = {}

    for t in sorted_themes:
        if not t.get("embedding"):
            canonicals.append(t)
            canonical_names.add(t["name"])
            cluster_of[t["name"]] = t
            continue
        if not canonicals:
            canonicals.append(t)
            canonical_names.add(t["name"])
            cluster_of[t["name"]] = t
            continue

        # One KNN call: top-K nearest themes overall, then filter in Python to
        # canonicals only. K=15 is plenty — even with hundreds of themes, the
        # nearest match is virtually always in the first few.
        neighbors = conn.query(
            """SELECT name, vector::distance::knn() AS dist FROM theme
               WHERE embedding <|15,COSINE|> $embedding AND user_id = $user_id
               ORDER BY dist""",
            {"embedding": t["embedding"], "user_id": user_id},
        )
        neighbors = neighbors if neighbors and not isinstance(neighbors, str) else []

        best_canon = None
        for n in neighbors:
            if n["name"] == t["name"]:
                continue
            if n["name"] not in canonical_names:
                continue
            d = n.get("dist")
            if d is None or d > threshold:
                # Neighbors are sorted by dist; once we exceed threshold we can stop.
                break
            best_canon = next(c for c in canonicals if c["name"] == n["name"])
            break

        if best_canon is not None:
            cluster_of[t["name"]] = best_canon
        else:
            canonicals.append(t)
            canonical_names.add(t["name"])
            cluster_of[t["name"]] = t

    grouped: dict[str, list[dict]] = {c["name"]: [] for c in canonicals}
    for t in sorted_themes:
        canon = cluster_of[t["name"]]
        grouped[canon["name"]].append(t)
    return [members for members in grouped.values() if len(members) > 1]


def pick_canonical(cluster: list[dict]) -> dict:
    """Most mentions, tie-break shortest name, tie-break alphabetic."""
    return sorted(cluster, key=_theme_rank)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-id", required=True, help="user_id record (e.g. app_user:xxx)")
    ap.add_argument("--threshold", type=float, default=0.42, help="cosine distance threshold")
    ap.add_argument("--apply", action="store_true", help="actually mutate the DB (default is dry-run)")
    ap.add_argument(
        "--skip-canonical",
        default="",
        help="comma-separated canonical names to exclude from the plan",
    )
    args = ap.parse_args()

    conn = get_connection()
    user_id = args.user_id

    rows = conn.query(
        """SELECT id, name, description, embedding, array::len(<-about) AS mentions
           FROM theme WHERE user_id = $user_id""",
        {"user_id": user_id},
    )
    if not rows or isinstance(rows, str):
        print(f"No themes found for user_id={user_id}.")
        return
    themes = [{**r, "user_id": user_id} for r in rows]
    print(f"Loaded {len(themes)} themes for user_id={user_id}")

    missing_emb = [t["name"] for t in themes if not t.get("embedding")]
    if missing_emb:
        print(f"WARN: {len(missing_emb)} themes have no embedding and will be skipped: {missing_emb[:5]}…")

    clusters = find_clusters(themes, args.threshold, conn)
    skip_set = {s.strip() for s in args.skip_canonical.split(",") if s.strip()}
    print(f"\nFound {len(clusters)} cluster(s) of duplicates at threshold ≤ {args.threshold}\n")

    total_to_collapse = 0
    plan = []  # list of (canonical_theme, [duplicate_themes])
    skipped_clusters = []
    for cluster in sorted(clusters, key=lambda c: -len(c)):
        canonical = pick_canonical(cluster)
        dups = [t for t in cluster if t["name"] != canonical["name"]]
        if canonical["name"] in skip_set:
            skipped_clusters.append(canonical["name"])
            print(f"  SKIPPED canonical: '{canonical['name']}' (excluded via --skip-canonical)")
            for d in dups:
                print(f"     × would have merged: '{d['name']}'")
            print()
            continue
        plan.append((canonical, dups))
        total_to_collapse += len(dups)
        print(f"  canonical: '{canonical['name']}' ({canonical.get('mentions', 0)} mentions)")
        for d in dups:
            print(f"     ← merge: '{d['name']}' ({d.get('mentions', 0)} mentions)")
        print()

    if skipped_clusters:
        print(f"Skipped {len(skipped_clusters)} cluster(s): {', '.join(skipped_clusters)}\n")

    print(f"Summary: {len(themes)} themes → {len(themes) - total_to_collapse} after merge "
          f"(collapsing {total_to_collapse})")

    if not args.apply:
        print("\nDRY RUN. Re-run with --apply to commit these merges.")
        return

    print("\nApplying merges…")
    for canonical, dups in plan:
        # IMPORTANT: pass RecordID objects directly to the Surreal client — DO NOT
        # str() them. The client's RecordID.__str__() renders as "theme:abc", but
        # when bound as a parameter Surreal treats that as a string literal and
        # the WHERE clause never matches. Pass the RecordID object itself.
        canon_id = canonical["id"]

        existing = conn.query(
            "SELECT in AS rid FROM about WHERE out = $canon",
            {"canon": canon_id},
        )
        already_linked = {str(r["rid"]) for r in (existing or []) if isinstance(r, dict)}
        canon_count_before = len(already_linked)

        expected_new_links = 0
        for d in dups:
            dup_id = d["id"]
            dup_edges = conn.query(
                "SELECT id, in AS rid FROM about WHERE out = $dup",
                {"dup": dup_id},
            )
            dup_edges = dup_edges or []
            new_links = 0
            for edge in dup_edges:
                rid = edge["rid"]
                if str(rid) in already_linked:
                    continue
                # RELATE syntax requires literal record IDs, not parameters.
                conn.query(f"RELATE {rid}->about->{canon_id}")
                already_linked.add(str(rid))
                new_links += 1
            expected_new_links += new_links
            conn.query("DELETE about WHERE out = $dup", {"dup": dup_id})
            conn.query(f"DELETE {dup_id}")
            print(f"  merged '{d['name']}' → '{canonical['name']}' "
                  f"(added {new_links} new reflection links, deleted {len(dup_edges)} old edges)")

        # Post-merge sanity check — abort if the canonical didn't actually grow
        # by the expected amount. Catches the parameter-binding bug from session
        # history that silently shed edges on the demo account.
        verify = conn.query(
            "SELECT count() AS c FROM about WHERE out = $canon GROUP ALL",
            {"canon": canon_id},
        )
        canon_count_after = verify[0]["c"] if verify and not isinstance(verify, str) else 0
        expected_after = canon_count_before + expected_new_links
        if canon_count_after != expected_after:
            print(f"  !! VERIFY FAILED for '{canonical['name']}': "
                  f"expected {expected_after} edges, found {canon_count_after}. ABORTING.")
            raise SystemExit(2)
        print(f"     ✓ verified canonical now has {canon_count_after} reflection edge(s) "
              f"(was {canon_count_before}, +{expected_new_links})")

    print(f"\nDone. Collapsed {total_to_collapse} duplicate themes.")


if __name__ == "__main__":
    main()
