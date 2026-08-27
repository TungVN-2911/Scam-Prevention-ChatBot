from app.scam_connector.mock_connector import MockScamConnector


def test_search_patterns_returns_all_when_no_query():
    connector = MockScamConnector()
    assert len(connector.search_patterns()) == 23


def test_search_patterns_filters_by_query():
    connector = MockScamConnector()
    results = connector.search_patterns("deepfake")
    assert len(results) >= 1
    assert all("deepfake" in r.slug.lower() or "deepfake" in r.name.lower() for r in results)


def test_list_hotlines_includes_police_emergency_number():
    connector = MockScamConnector()
    hotlines = connector.list_hotlines()
    assert any(h.contact == "113" for h in hotlines)
