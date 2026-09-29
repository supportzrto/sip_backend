from app.scanner.strategies import SwingStrategy


def test_strategy_name():

    strategy = SwingStrategy()

    assert strategy.name == "Swing Strategy"


def test_strategy_request():

    strategy = SwingStrategy()

    request = strategy.build_request()

    assert len(request.expression.children) == 3