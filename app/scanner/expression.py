from app.scanner.evaluator import evaluate_condition_on_stock
from app.scanner.enums import LogicalOperator
from app.scanner.reasoning import describe_condition
from app.scanner.schemas import (
    ScanCondition,
    ScanExpression,
    StockSnapshot,
)


def evaluate_expression(
    stock: StockSnapshot,
    expression: ScanExpression,
) -> bool:
    """
    Evaluate a logical expression tree.
    """

    results = []

    for child in expression.children:

        if isinstance(
            child,
            ScanCondition,
        ):

            results.append(
                evaluate_condition_on_stock(
                    stock,
                    child,
                )
            )

        else:

            results.append(
                evaluate_expression(
                    stock,
                    child,
                )
            )

    match expression.operator:

        case LogicalOperator.AND:
            return all(results)

        case LogicalOperator.OR:
            return any(results)

        case LogicalOperator.NOT:

            if len(results) != 1:

                raise ValueError(
                    "NOT expects exactly one child."
                )

            return not results[0]

    raise ValueError(
        f"Unknown operator: {expression.operator}"
    )


def evaluate_expression_with_reasons(
    stock: StockSnapshot,
    expression: ScanExpression,
) -> tuple[bool, list[str]]:
    """
    Same evaluation as evaluate_expression, but also returns a list
    of human-readable reasons for every condition that matched
    (e.g. "RSI14 (28.40) < 35", "EMA20 crossed above EMA50 ...").

    For AND: if the whole expression matches, every child matched,
    so every child's reason(s) are included.
    For OR: only the reasons of the specific child(ren) that matched
    are included.
    For NOT: no reason is generated (a negation doesn't describe a
    single triggering event on its own).
    """

    child_matches: list[bool] = []
    child_reasons: list[str] = []

    for child in expression.children:

        if isinstance(
            child,
            ScanCondition,
        ):

            matched = evaluate_condition_on_stock(
                stock,
                child,
            )

            child_matches.append(matched)

            if matched:
                child_reasons.append(
                    describe_condition(stock, child)
                )

        else:

            matched, reasons = evaluate_expression_with_reasons(
                stock,
                child,
            )

            child_matches.append(matched)

            if matched:
                child_reasons.extend(reasons)

    match expression.operator:

        case LogicalOperator.AND:

            overall = all(child_matches)

            return overall, (child_reasons if overall else [])

        case LogicalOperator.OR:

            overall = any(child_matches)

            return overall, child_reasons

        case LogicalOperator.NOT:

            if len(child_matches) != 1:

                raise ValueError(
                    "NOT expects exactly one child."
                )

            return not child_matches[0], []

    raise ValueError(
        f"Unknown operator: {expression.operator}"
    )