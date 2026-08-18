import pytest

from remis_aventine.v03_budget import V03BudgetError, estimate_v03_campaign


def test_two_contestants_expected_call_volume_is_explicit() -> None:
    result = estimate_v03_campaign(contestants=2)

    assert result["assumptions"]["pair_count"] == 1
    assert result["expected_calls"] == {
        "contestant": 740,
        "soft_judges": 1532,
        "structural_judges": 48,
        "total": 2320,
    }
    assert result["reserve_cost_usd"]["total_expected"] == 8.76


def test_anchor_topologies_avoid_quadratic_pair_growth() -> None:
    round_robin = estimate_v03_campaign(contestants=9)
    single_anchor = estimate_v03_campaign(contestants=9, topology="single-anchor")
    double_anchor = estimate_v03_campaign(contestants=9, topology="double-anchor")

    assert round_robin["assumptions"]["pair_count"] == 36
    assert single_anchor["assumptions"]["pair_count"] == 8
    assert double_anchor["assumptions"]["pair_count"] == 15
    assert round_robin["expected_calls"]["soft_judges"] > 4 * single_anchor[
        "expected_calls"
    ]["soft_judges"]


def test_invalid_rates_and_topology_are_rejected() -> None:
    with pytest.raises(V03BudgetError, match="between 0 and 1"):
        estimate_v03_campaign(contestants=2, audit_rate=2)
    with pytest.raises(V03BudgetError, match="Unknown pairing"):
        estimate_v03_campaign(contestants=2, topology="mystery")
