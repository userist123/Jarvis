from datetime import date

from jarvis.runtime.temporal import TemporalQuery, filter_temporal, matches_temporal


def note(**kwargs):
    base = {
        "id": "n1",
        "valid_from": "2024-01-01",
        "valid_until": "2025-12-31",
        "provenance": {"extraction_date": "2024-06-01"},
    }
    base.update(kwargs)
    return base


def test_as_of_filters_by_validity_interval():
    query = TemporalQuery(as_of=date(2023, 12, 31))
    assert matches_temporal(note(), query) is False


def test_as_of_inside_validity_interval_matches():
    query = TemporalQuery(as_of=date(2025, 1, 1))
    assert matches_temporal(note(), query) is True


def test_known_as_of_filters_future_extraction():
    query = TemporalQuery(known_as_of=date(2024, 1, 1))
    assert matches_temporal(note(), query) is False


def test_missing_temporal_fields_remain_backward_compatible():
    query = TemporalQuery(as_of=date(2020, 1, 1), known_as_of=date(2020, 1, 1))
    assert matches_temporal({"id": "n2", "provenance": {}}, query) is True


def test_filter_temporal_preserves_input_order():
    notes = [note(id="a"), note(id="b", valid_from="2026-01-01")]
    filtered = filter_temporal(notes, TemporalQuery(as_of=date(2025, 1, 1)))
    assert [item["id"] for item in filtered] == ["a"]
