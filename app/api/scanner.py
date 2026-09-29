from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies.scanner import (
    get_backtest_service,
    get_scan_run_repository,
    get_scanner_service,
)
from app.auth.constants import UserRole
from app.auth.dependencies import require_user
from app.models.user import User
from app.repositories.scan_run_repository import ScanRunRepository
from app.scanner.backtest import DEFAULT_HOLDING_PERIODS
from app.scanner.schemas import (
    BacktestEventResponse,
    BacktestResponse,
    HoldingPeriodStatsResponse,
    ScanRequest,
    ScanResult,
    ScanRunDetail,
    ScanRunListResponse,
    ScanRunSummary,
    ScanStrategySummary,
)
from app.scanner.strategies import (
    BreakdownStrategy,
    BreakoutStrategy,
    ScanStrategy,
    SwingStrategy,
)
from app.services.backtest_service import BacktestService
from app.services.scanner_service import ScannerService

router = APIRouter(
    prefix="/scanner",
    tags=["Scanner"],
    dependencies=[Depends(require_user)],
)

# Named, ready-to-run strategies. Keyed by a URL-friendly slug.
AVAILABLE_STRATEGIES: dict[str, ScanStrategy] = {
    "breakout": BreakoutStrategy(),
    "breakdown": BreakdownStrategy(),
    "swing": SwingStrategy(),
}

# When no explicit symbol list is given to a backtest, cap how many
# instruments get walked. Backtesting reads each instrument's FULL
# history (not just the latest day), so an unbounded run across the
# whole real dataset could take a very long time.
DEFAULT_BACKTEST_INSTRUMENT_LIMIT = 100


@router.post(
    "/scan",
    response_model=list[ScanResult],
)
def scan(
    request: ScanRequest,
    current_user: User = Depends(require_user),
    service: ScannerService = Depends(
        get_scanner_service,
    ),
) -> list[ScanResult]:
    """
    Execute a custom stock scan from a raw expression tree. The run
    and its matched results are persisted for later lookup.
    """

    return service.scan(request, user_id=current_user.id)


@router.get(
    "/strategies",
    response_model=list[ScanStrategySummary],
)
def list_strategies() -> list[ScanStrategySummary]:
    """
    List the available named strategies (e.g. "breakout",
    "breakdown") that can be run via POST /scanner/strategies/{key}/scan
    without building a custom expression tree.
    """

    return [
        ScanStrategySummary(key=key, name=strategy.name)
        for key, strategy in AVAILABLE_STRATEGIES.items()
    ]


@router.post(
    "/strategies/{key}/scan",
    response_model=list[ScanResult],
)
def scan_with_strategy(
    key: str,
    current_user: User = Depends(require_user),
    service: ScannerService = Depends(
        get_scanner_service,
    ),
) -> list[ScanResult]:
    """
    Run a named strategy (see GET /scanner/strategies for the
    available keys) without needing to build the expression JSON
    yourself.
    """

    strategy = AVAILABLE_STRATEGIES.get(key)

    if strategy is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown strategy '{key}'. "
                f"See GET /scanner/strategies for available keys."
            ),
        )

    return service.scan(strategy.build_request(), user_id=current_user.id)


@router.get(
    "/runs",
    response_model=ScanRunListResponse,
)
def list_runs(
    limit: int = 20,
    offset: int = 0,
    strategy: str | None = None,
    symbol: str | None = None,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
    current_user: User = Depends(require_user),
    repository: ScanRunRepository = Depends(
        get_scan_run_repository,
    ),
) -> ScanRunListResponse:
    """
    List scan runs, most recent first.

    Regular users only see their own runs. Admins see every user's
    runs (pass no extra parameter to opt into this -- it's implicit
    in the role).

    Supports pagination (limit/offset) and optional filtering by
    strategy name, a matched symbol, or a started_at date range.
    """

    # Admins aren't scoped to a single owner; everyone else only
    # ever sees runs they started themselves.
    scoped_user_id = (
        None
        if current_user.role == UserRole.ADMIN.value
        else current_user.id
    )

    filters = dict(
        strategy=strategy,
        symbol=symbol,
        started_after=started_after,
        started_before=started_before,
        user_id=scoped_user_id,
    )

    runs = repository.get_recent_runs(
        limit=limit,
        offset=offset,
        **filters,
    )

    total = repository.count_runs(**filters)

    return ScanRunListResponse(
        total=total,
        limit=limit,
        offset=offset,
        runs=[
            ScanRunSummary.model_validate(run)
            for run in runs
        ],
    )


@router.get(
    "/runs/{run_id}",
    response_model=ScanRunDetail,
)
def get_run(
    run_id: int,
    current_user: User = Depends(require_user),
    repository: ScanRunRepository = Depends(
        get_scan_run_repository,
    ),
) -> ScanRunDetail:
    """
    Get a single scan run, including which stocks matched and why.

    Regular users can only fetch their own runs; a run belonging to
    someone else is reported as 404 (not 403), so its existence
    isn't revealed to non-owners. Admins can fetch any run.
    """

    scoped_user_id = (
        None
        if current_user.role == UserRole.ADMIN.value
        else current_user.id
    )

    run = repository.get_run_with_results(
        run_id,
        user_id=scoped_user_id,
    )

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Scan run not found.",
        )

    return ScanRunDetail(
        id=run.id,
        user_id=run.user_id,
        strategy=run.strategy,
        stocks_scanned=run.stocks_scanned,
        matches_found=run.matches_found,
        started_at=run.started_at,
        completed_at=run.completed_at,
        results=[
            ScanResult(
                symbol=result.symbol,
                reasons=result.reasons,
            )
            for result in run.results
        ],
    )

@router.post(
    "/strategies/{key}/backtest",
    response_model=BacktestResponse,
)
def backtest_strategy(
    key: str,
    symbols: list[str] | None = Query(
        default=None,
        description=(
            "Symbols to backtest. Omit to backtest a capped subset "
            "of the whole universe (see instrument_limit)."
        ),
    ),
    instrument_limit: int = Query(
        default=DEFAULT_BACKTEST_INSTRUMENT_LIMIT,
        description=(
            "Max instruments to scan when 'symbols' isn't given. "
            "Ignored if 'symbols' is provided."
        ),
    ),
    holding_periods: list[int] | None = Query(
        default=None,
        description=(
            "Forward-return windows to measure, in trading days. "
            f"Defaults to {list(DEFAULT_HOLDING_PERIODS)}."
        ),
    ),
    sort_events_by: str = Query(
        default="recent",
        description=(
            "How to select which events to return (capped at 200): "
            "'recent' (default, most recent signals first), "
            "'worst' (most negative return first -- useful for "
            "spot-checking extreme losses, e.g. for data quality "
            "issues like unadjusted stock splits), or "
            "'best' (most positive return first)."
        ),
    ),
    sort_events_holding_period: int = Query(
        default=20,
        description=(
            "Which holding period's return to sort by, when "
            "sort_events_by is 'worst' or 'best'. Ignored for "
            "'recent'. Events with no return measured for this "
            "period (not enough subsequent history yet) are "
            "excluded from 'worst'/'best' sorting."
        ),
    ),
    include_baseline: bool = Query(
        default=True,
        description=(
            "Also compute the 'buy anything, any day' universe "
            "baseline for comparison. Set to false for a cheaper, "
            "lower-memory pass (useful on memory-constrained "
            "machines at large instrument counts) -- baseline_stats "
            "will be empty in that case."
        ),
    ),
    backtest_service: BacktestService = Depends(
        get_backtest_service,
    ),
) -> BacktestResponse:
    """
    Backtest a named strategy: find every historical occurrence of
    its signal across instruments' full history, and measure what
    actually happened to price in the days/weeks afterward.

    This is different from /scan or /strategies/{key}/scan, which
    only look at the most recent day. A backtest answers whether the
    signal has historically had real edge, not just whether it's
    firing right now.
    """

    strategy = AVAILABLE_STRATEGIES.get(key)

    if strategy is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown strategy '{key}'. "
                f"See GET /scanner/strategies for available keys."
            ),
        )

    periods = (
        tuple(holding_periods)
        if holding_periods
        else DEFAULT_HOLDING_PERIODS
    )

    events, stats, baseline_stats, instruments_scanned = backtest_service.run(
        expression=strategy.build_request().expression,
        symbols=symbols,
        holding_periods=periods,
        limit=instrument_limit,
        include_baseline=include_baseline,
    )

    total_signals_found = len(events)

    if sort_events_by in ("worst", "best"):

        events = [
            e
            for e in events
            if sort_events_holding_period in e.forward_returns
        ]

        events.sort(
            key=lambda e: e.forward_returns[sort_events_holding_period],
            reverse=(sort_events_by == "best"),
        )

    def _to_response(s) -> HoldingPeriodStatsResponse:
        return HoldingPeriodStatsResponse(
            holding_period=s.holding_period,
            sample_size=s.sample_size,
            win_rate=s.win_rate,
            average_return=s.average_return,
            median_return=s.median_return,
            best_return=s.best_return,
            worst_return=s.worst_return,
            trimmed_mean_return=s.trimmed_mean_return,
            outlier_count=s.outlier_count,
            outlier_share=s.outlier_share,
        )

    return BacktestResponse(
        strategy_name=strategy.name,
        instruments_scanned=instruments_scanned,
        total_signals_found=total_signals_found,
        stats=[_to_response(s) for s in stats],
        baseline_stats=[_to_response(s) for s in baseline_stats],
        events=[
            BacktestEventResponse(
                symbol=e.symbol,
                trade_date=e.trade_date,
                entry_price=e.entry_price,
                reasons=e.reasons,
                forward_returns={
                    str(period): value
                    for period, value in e.forward_returns.items()
                },
            )
            for e in events[:200]
        ],
    )