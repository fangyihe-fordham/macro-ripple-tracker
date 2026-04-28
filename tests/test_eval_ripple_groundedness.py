import pytest

from eval import ripple_groundedness


def test_match_sectors_exact_and_fuzzy():
    tree = {"event": "x", "nodes": [
        {"sector": "Oil Supply", "children": [
            {"sector": "Jet Fuel / Airlines", "children": []},
        ]},
        {"sector": "Shipping", "children": []},
        {"sector": "Crypto Moon Lambo", "children": []},
    ]}
    truth = ["Oil Supply", "Shipping", "Fertilizer", "Airlines / Jet fuel"]

    result = ripple_groundedness.score(tree, truth)

    assert set(result["matched"]) == {"Oil Supply", "Shipping", "Airlines / Jet fuel"}
    assert set(result["missed"]) == {"Fertilizer"}
    assert set(result["hallucinated"]) == {"Crypto Moon Lambo"}
    assert result["precision"] == pytest.approx(3 / 4)
    assert result["recall"] == pytest.approx(3 / 4)


def test_multiple_ai_sectors_can_match_one_truth_sector():
    tree = {"event": "x", "nodes": [
        {"sector": "Fertilizer / Ammonia", "children": []},
        {"sector": "Fertilizer Industry", "children": []},
        {"sector": "Crypto Moon Lambo", "children": []},
    ]}
    truth = ["Fertilizer / Ammonia"]

    result = ripple_groundedness.score(tree, truth)

    assert set(result["matched"]) == {"Fertilizer / Ammonia"}
    assert set(result["hallucinated"]) == {"Crypto Moon Lambo"}
    assert result["precision"] == pytest.approx(2 / 3)
    assert result["recall"] == pytest.approx(1 / 1)


def test_score_credits_singular_plural_paraphrase():
    tree = {"event": "x", "nodes": [
        {"sector": "Airline & Aviation Industry", "children": []},
    ]}
    truth = ["Airlines / Jet fuel"]

    result = ripple_groundedness.score(tree, truth)

    assert "Airlines / Jet fuel" in result["matched"]
    assert "Airline & Aviation Industry" not in result["hallucinated"]
    assert result["precision"] == pytest.approx(1.0)


def test_score_credits_paraphrased_subsector_via_shared_content_token():
    tree = {"event": "x", "nodes": [
        {"sector": "Industrial Metals & Materials", "children": []},
        {"sector": "Marine Insurance & War Risk Underwriting", "children": []},
    ]}
    truth = ["Aluminum / energy-intensive metals", "Shipping / Tanker insurance"]

    result = ripple_groundedness.score(tree, truth)

    assert set(result["matched"]) == {
        "Aluminum / energy-intensive metals",
        "Shipping / Tanker insurance",
    }
    assert result["hallucinated"] == []


def test_score_does_not_match_on_generic_words_alone():
    tree = {"event": "x", "nodes": [
        {"sector": "Global Energy Supply", "children": []},
    ]}
    truth = ["Oil Supply"]

    result = ripple_groundedness.score(tree, truth)

    assert "Oil Supply" not in result["matched"]
    assert "Global Energy Supply" in result["hallucinated"]


def test_price_change_matches_real_data():
    tree = {"event": "x", "nodes": [
        {"sector": "Oil", "price_change": 49.6, "price_details": [
            {"symbol": "BZ=F", "pct_change": 49.6}], "children": []},
        {"sector": "Gas", "price_change": 50.1, "price_details": [
            {"symbol": "NG=F", "pct_change": 50.1}], "children": []},
    ]}
    actual = {"BZ=F": {"pct_change": 49.60}, "NG=F": {"pct_change": 12.0}}

    report = ripple_groundedness.check_price_integrity(tree, actual, tolerance=0.5)

    assert report["ok_count"] == 1
    assert report["mismatch_count"] == 1
    assert report["mismatches"][0]["symbol"] == "NG=F"
