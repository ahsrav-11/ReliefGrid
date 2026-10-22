"""Pure-Python allocation engine: no Flask, no database. Easy to test and reuse in simulation.

Priority score (0-100) = 100 * ( 0.40*urgency/5 + 0.25*population/max_population
                               + 0.15*location_severity/5 + 0.20*quantity/max_quantity )
Modes:
  priority     - fill requests in rank order until stock runs out
  proportional - share stock in proportion to score x quantity (capped at each request)
"""

DEFAULT_WEIGHTS = {"urgency": 0.40, "population": 0.25, "severity": 0.15, "shortage": 0.20}


def score_requests(requests, weights=None):
    w = weights or DEFAULT_WEIGHTS
    max_pop = max([r["population"] for r in requests] or [1]) or 1
    max_qty = max([r["quantity"] for r in requests] or [1]) or 1
    rows = []
    for r in requests:
        s = 100 * (w["urgency"] * r["urgency"] / 5 + w["population"] * r["population"] / max_pop
                   + w["severity"] * r["severity"] / 5 + w["shortage"] * r["quantity"] / max_qty)
        rows.append({**r, "score": round(s, 1), "allocated": 0})
    rows.sort(key=lambda x: (-x["score"], x["id"]))
    return rows


def allocate(requests, supply, mode="priority", weights=None):
    supply = max(0, int(supply))
    rows = score_requests(requests, weights)
    remaining = supply
    if mode == "priority":
        for row in rows:
            give = min(row["quantity"], remaining)
            row["allocated"], remaining = give, remaining - give
    else:
        if sum(r["quantity"] for r in rows) <= supply:
            for r in rows:
                r["allocated"] = r["quantity"]
        else:
            active = list(rows)
            while remaining > 0 and active:
                weight = {r["id"]: r["score"] * (r["quantity"] - r["allocated"]) for r in active}
                total, snapshot, given = sum(weight.values()), remaining, 0
                if total <= 0:
                    break
                for r in active:
                    share = min(r["quantity"] - r["allocated"], int(snapshot * weight[r["id"]] / total))
                    r["allocated"] += share
                    given += share
                remaining -= given
                if given == 0:  # hand out leftovers one unit at a time, best score first
                    for r in active:
                        if remaining > 0 and r["allocated"] < r["quantity"]:
                            r["allocated"] += 1
                            remaining -= 1
                    break
                active = [r for r in active if r["allocated"] < r["quantity"]]
    n = len(rows)
    for i, r in enumerate(rows, 1):
        r["rank"] = i
        r["unmet"] = r["quantity"] - r["allocated"]
        base = (f"Rank {i} of {n}, score {r['score']}: urgency {r['urgency']}/5, "
                f"{r['population']} people, area severity {r['severity']}/5, {r['quantity']} requested. ")
        if r["unmet"] == 0:
            why = "Fully met because stock covered it."
        elif mode == "priority":
            why = (f"Gets {r['allocated']}; stock ran out after higher-ranked requests." if r["allocated"]
                   else "Nothing left once higher-ranked requests were filled.")
        else:
            why = f"Gets {r['allocated']}: stock was shared in proportion to score x quantity."
        r["explanation"] = base + why
    return rows
