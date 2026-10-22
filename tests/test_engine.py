from app.allocation_engine import allocate

REQS = [dict(id=1, quantity=100, urgency=5, population=1000, severity=5),
        dict(id=2, quantity=100, urgency=2, population=200, severity=2),
        dict(id=3, quantity=50, urgency=4, population=500, severity=4)]


def test_never_exceeds_supply_or_request():
    for mode in ("priority", "proportional"):
        for supply in (0, 1, 37, 120, 250, 1000):
            plan = allocate(REQS, supply, mode)
            assert sum(p["allocated"] for p in plan) <= supply
            assert all(0 <= p["allocated"] <= p["quantity"] for p in plan)
            assert sum(p["allocated"] for p in plan) == min(supply, 250)


def test_priority_order_and_ranking():
    plan = allocate(REQS, 120, "priority")
    assert [p["id"] for p in plan] == [1, 3, 2]
    assert plan[0]["allocated"] == 100 and plan[1]["allocated"] == 20 and plan[2]["allocated"] == 0


def test_proportional_shares_between_all():
    plan = allocate(REQS, 120, "proportional")
    assert all(p["allocated"] > 0 for p in plan)


def test_explanations_present():
    assert all("Rank" in p["explanation"] for p in allocate(REQS, 50))


def test_empty_requests():
    assert allocate([], 100) == []
