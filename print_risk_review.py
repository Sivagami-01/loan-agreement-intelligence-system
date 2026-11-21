import csv, random
from pathlib import Path
csv.field_size_limit(2**31 - 1)
D = Path(r"data\processed\labels\llm_assisted")

def load(name):
    with (D / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

rev = load("risk_revisions.csv")
orig = {}
for fn in ("risk_llm.csv", "risk_indian_llm.csv"):
    for r in load(fn):
        orig[(r["doc_id"], r["clause_id"])] = (fn, r)
key = lambda r: (r["doc_id"], r["clause_id"])
revmap = {key(r): r for r in rev}

def show(n, k):
    fn, row = orig[k]
    rv = revmap.get(k)
    print(f"--- {n}. {k[0]} {k[1]} ({fn})")
    if rv:
        print(f"   CHANGED: {rv['old_category']}/{rv['old_severity']} -> "
              f"{rv['new_category']}/{rv['new_severity']} | {rv['reason'][:200]}")
    else:
        print("   unchanged")
    for c, v in row.items():
        if c in ("doc_id", "clause_id") or not str(v).strip():
            continue
        print(f"   {c}: {str(v)[:220]}")

crit = [r for r in rev if r["old_severity"] == "Critical" and r["new_severity"] != "Critical"]
print(f"CRITICAL ROWS LOWERED: {len(crit)}")
for r in crit:
    print(f"  {r['doc_id']} {r['clause_id']}: {r['old_category']}/{r['old_severity']} -> {r['new_category']}/{r['new_severity']}")

print("\n=== ROWS I APPROVED AS CRITICAL EARLIER (should still be Critical) ===")
pinned = [("000081/810113/0000950116-04-002411_4.txt", "R12"),
          ("000081/810113/0000950116-04-002411_4.txt", "R12"),
          ("000084/849547/0000950128-00-000940_5.txt", "R16")]
for i, k in enumerate(pinned, 1):
    if k in orig:
        show(i, k)
    else:
        print(f"--- not found: {k}")

print("\n=== 20 SAMPLE ROWS (seed 42) ===")
rng = random.Random(42)
seen = set(pinned)
chosen = []
def take(pool, n):
    pool = [k for k in pool if k in orig and k not in seen]
    rng.shuffle(pool)
    for k in pool[:n]:
        seen.add(k)
        chosen.append(k)
crit_keys = [key(r) for r in crit]
ind_changed = [key(r) for r in rev if key(r) in orig and orig[key(r)][0] == "risk_indian_llm.csv"]
others = [key(r) for r in rev]
ind_unchanged = [k for k, (fn, _) in orig.items() if fn == "risk_indian_llm.csv" and k not in revmap]
take(crit_keys, 8)
take(ind_changed, 4)
take(others, 4)
take(ind_unchanged, 4)
take(others, 20 - len(chosen))
for i, k in enumerate(chosen, 1):
    show(i, k)