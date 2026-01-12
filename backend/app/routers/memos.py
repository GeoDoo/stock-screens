"""Investment memo endpoints for thesis tracking and post-mortems."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from app.schemas.memos import (
    CreateMemoRequest,
    AddPostMortemRequest,
    CloseMemoRequest,
    MemoMarket,
)
from app.services.memo_repository import MemoRepository, get_memo_repository
from app.models.memo import (
    InvestmentMemo,
    AssumptionsSnapshot,
    ScenarioSnapshot,
    MarketSnapshot,
    PostMortem,
    Conviction,
    MemoStatus,
    PostMortemAction,
)

router = APIRouter(prefix="/api/memos", tags=["memos"])


@router.post("", status_code=201)
async def create_memo(
    request: CreateMemoRequest,
    repo: MemoRepository = Depends(get_memo_repository),
):
    """
    Create a new investment memo.
    
    Captures thesis, assumptions, scenarios, and market context at creation time.
    """
    try:
        conviction = Conviction(request.conviction)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid conviction. Valid: {[c.value for c in Conviction]}"
        )
    
    memo = InvestmentMemo(
        id=None,
        symbol=request.symbol.upper(),
        title=request.title,
        thesis=request.thesis,
        conviction=conviction,
        time_horizon_months=request.time_horizon_months,
        created_at=datetime.now(timezone.utc),
        assumptions=AssumptionsSnapshot(
            revenue_growth=request.assumptions.revenue_growth,
            operating_margin=request.assumptions.operating_margin,
            terminal_growth_rate=request.assumptions.terminal_growth_rate,
            discount_rate=request.assumptions.discount_rate,
            projection_years=request.assumptions.projection_years,
            da_ratio=request.assumptions.da_ratio,
            capex_ratio=request.assumptions.capex_ratio,
            wc_ratio=request.assumptions.wc_ratio,
        ),
        scenarios=[
            ScenarioSnapshot(
                name=s.name,
                revenue_growth=s.revenue_growth,
                operating_margin=s.operating_margin,
                intrinsic_value=s.intrinsic_value,
                upside_percent=s.upside_percent,
            )
            for s in request.scenarios
        ],
        initial_market=MarketSnapshot(
            price=request.initial_market.price,
            intrinsic_value=request.initial_market.intrinsic_value,
            pe_ratio=request.initial_market.pe_ratio,
        ),
        target_price=request.target_price,
        risks=request.risks,
        catalysts=request.catalysts,
        what_would_change_mind=request.what_would_change_mind,
    )
    
    saved = await repo.save_memo(memo)
    return saved.to_dict()


@router.get("")
async def list_memos(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    repo: MemoRepository = Depends(get_memo_repository),
):
    """
    List investment memos with optional filtering.
    
    Args:
        symbol: Filter by stock symbol
        status: Filter by status (active, closed_win, closed_loss, closed_neutral)
    """
    status_filter = None
    if status:
        try:
            status_filter = MemoStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Valid: {[s.value for s in MemoStatus]}"
            )
    
    memos = await repo.list_memos(symbol=symbol, status=status_filter)
    return [m.to_dict() for m in memos]


@router.get("/{memo_id}")
async def get_memo(
    memo_id: int,
    repo: MemoRepository = Depends(get_memo_repository),
):
    """Get a single investment memo by ID."""
    memo = await repo.get_memo(memo_id)
    if memo is None:
        raise HTTPException(status_code=404, detail=f"Memo {memo_id} not found")
    return memo.to_dict()


@router.put("/{memo_id}")
async def update_memo(
    memo_id: int,
    request: CreateMemoRequest,
    repo: MemoRepository = Depends(get_memo_repository),
):
    """Update an existing memo."""
    existing = await repo.get_memo(memo_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Memo {memo_id} not found")
    
    try:
        conviction = Conviction(request.conviction)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid conviction. Valid: {[c.value for c in Conviction]}"
        )
    
    existing.title = request.title
    existing.thesis = request.thesis
    existing.conviction = conviction
    existing.time_horizon_months = request.time_horizon_months
    existing.target_price = request.target_price
    existing.risks = request.risks
    existing.catalysts = request.catalysts
    existing.what_would_change_mind = request.what_would_change_mind
    
    updated = await repo.update_memo(existing)
    return updated.to_dict()


@router.delete("/{memo_id}")
async def delete_memo(
    memo_id: int,
    repo: MemoRepository = Depends(get_memo_repository),
):
    """Delete an investment memo."""
    existing = await repo.get_memo(memo_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Memo {memo_id} not found")
    
    await repo.delete_memo(memo_id)
    return {"deleted": True, "id": memo_id}


@router.post("/{memo_id}/post-mortems", status_code=201)
async def add_post_mortem(
    memo_id: int,
    request: AddPostMortemRequest,
    repo: MemoRepository = Depends(get_memo_repository),
):
    """
    Add a post-mortem review to a memo.
    
    Post-mortems track how reality is unfolding vs the original thesis.
    """
    existing = await repo.get_memo(memo_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Memo {memo_id} not found")
    
    try:
        action = PostMortemAction(request.action)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Valid: {[a.value for a in PostMortemAction]}"
        )
    
    post_mortem = PostMortem(
        id=None,
        memo_id=memo_id,
        created_at=datetime.now(timezone.utc),
        note=request.note,
        action=action,
        price_at_time=request.price_at_time,
        iv_at_time=request.iv_at_time,
    )
    
    saved = await repo.add_post_mortem(post_mortem)
    return saved.to_dict()


@router.post("/{memo_id}/close")
async def close_memo(
    memo_id: int,
    request: CloseMemoRequest,
    repo: MemoRepository = Depends(get_memo_repository),
):
    """
    Close a memo with final status and reason.
    
    Status should reflect whether the thesis played out:
    - closed_win: Thesis was correct
    - closed_loss: Thesis was wrong
    - closed_neutral: Closed for other reasons
    """
    existing = await repo.get_memo(memo_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Memo {memo_id} not found")
    
    try:
        status = MemoStatus(request.status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid: {[s.value for s in MemoStatus if s != MemoStatus.ACTIVE]}"
        )
    
    if status == MemoStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Cannot close memo with 'active' status")
    
    closed = await repo.close_memo(memo_id, status, request.reason)
    return closed.to_dict()


@router.post("/{memo_id}/snapshots", status_code=201)
async def add_market_snapshot(
    memo_id: int,
    request: MemoMarket,
    repo: MemoRepository = Depends(get_memo_repository),
):
    """
    Add a market snapshot to track performance over time.
    
    Call this periodically to track how price and intrinsic value evolve.
    """
    existing = await repo.get_memo(memo_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Memo {memo_id} not found")
    
    snapshot = MarketSnapshot(
        price=request.price,
        intrinsic_value=request.intrinsic_value,
        pe_ratio=request.pe_ratio,
    )
    
    saved = await repo.add_market_snapshot(memo_id, snapshot)
    return saved.to_dict()
