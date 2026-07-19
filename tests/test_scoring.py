from catch_domain.models import DomainStatus, NameResult
from catch_domain.scoring import score_name


def d(domain, tld, is_base, status):
    return DomainStatus(domain=domain, tld=tld, is_base=is_base, status=status)


def test_nothing_found_is_clean():
    result = NameResult(name="zetavolve",
                        domains=[d("zetavolve.com", "com", True, "unregistered")])
    assert score_name(result) == (0, "CLEAN")


def test_live_base_com_is_hard_taken():
    result = NameResult(name="enlance",
                        domains=[d("enlance.com", "com", True, "live")])
    score, verdict = score_name(result)
    assert score == 50
    assert verdict == "TAKEN"


def test_mixed_signals_are_risky():
    # base registered on .io (8) + variant registered on .com (6) + 1 lookalike (3) = 17
    result = NameResult(
        name="flintlogic",
        domains=[
            d("flintlogic.io", "io", True, "registered"),
            d("flintlogicit.com", "com", False, "registered"),
        ],
        lookalikes=["flintlogics.com"],
    )
    assert score_name(result) == (17, "RISKY")


def test_lookalike_score_is_capped():
    result = NameResult(name="enlance",
                        lookalikes=[f"enlance{i}.com" for i in range(10)])
    score, verdict = score_name(result)
    assert score == 15  # 10 * 3 capped at 15
    assert verdict == "RISKY"


def test_search_hits_scored_by_base_vs_variant_with_caps():
    result = NameResult(
        name="enlance",
        search_hits=(
            [{"title": "t", "url": "u", "is_base": True} for _ in range(10)]
            + [{"title": "t", "url": "u", "is_base": False} for _ in range(10)]
        ),
    )
    score, verdict = score_name(result)
    assert score == 40  # base capped at 30 + variant capped at 10
    assert verdict == "RISKY"


def test_unknown_checks_add_caution_points():
    result = NameResult(
        name="enlance",
        domains=[d("enlance.com", "com", True, "unknown")],
        ct_status="unknown",
    )
    assert score_name(result) == (4, "CLEAN")


def test_score_at_taken_threshold_is_taken():
    # base registered .com (25) + base registered .in (25) = 50
    result = NameResult(
        name="enlance",
        domains=[
            d("enlance.com", "com", True, "registered"),
            d("enlance.in", "in", True, "registered"),
        ],
    )
    assert score_name(result) == (50, "TAKEN")
