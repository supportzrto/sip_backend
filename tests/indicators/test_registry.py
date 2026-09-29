from app.indicators.registry import IndicatorRegistry


def test_registry_not_empty():

    registry = IndicatorRegistry()

    assert len(registry.indicators) > 0


def test_registry_contains_ema():

    registry = IndicatorRegistry()

    names = [
        indicator.__class__.__name__
        for indicator in registry.indicators
    ]

    assert "EMAIndicator" in names


def test_registry_contains_rsi():

    registry = IndicatorRegistry()

    names = [
        indicator.__class__.__name__
        for indicator in registry.indicators
    ]

    assert "RSIIndicator" in names