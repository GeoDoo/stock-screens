"""Audit endpoints for tracking assumption changes."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response

from app.schemas.audit import AuditRequest
from app.services.audit_repository import AuditRepository, get_audit_repository
from app.models.assumption_audit import (
    AssumptionField,
    AuditEntry,
    AssumptionSnapshot,
)

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.post("/{symbol}", status_code=201)
async def record_assumptions(
    symbol: str,
    request: AuditRequest,
    response: Response,
    repo: AuditRepository = Depends(get_audit_repository),
):
    """
    Record assumption changes for a stock.
    
    Args:
        symbol: Stock ticker symbol
        request: New assumptions and optional note
    
    On first call for a symbol, creates an initial entry (baseline).
    On subsequent calls, only records fields that changed from previous snapshot.
    
    Returns:
        - 201 with saved audit entry when changes recorded
        - 200 with empty changes if nothing changed
    """
    symbol = symbol.upper()
    
    # Get previous snapshot (or empty if first analysis)
    previous = repo.get_latest_snapshot(symbol)
    is_initial = previous is None
    
    if previous is None:
        previous = AssumptionSnapshot(symbol=symbol)
    
    # Detect what changed
    changes = previous.diff(request.assumptions)
    
    if not changes and not is_initial:
        # Nothing changed - don't create an entry
        response.status_code = 200
        return {"message": "No changes detected", "changes": []}
    
    # Create and save the entry
    entry = AuditEntry(
        id=None,
        symbol=symbol,
        timestamp=datetime.now(),
        changes=changes,
        note=request.note,
        is_initial=is_initial,
        price_at_time=request.price_at_time,
        intrinsic_value_at_time=request.intrinsic_value_at_time,
        pe_ratio_at_time=request.pe_ratio_at_time,
    )
    
    saved = repo.save_entry(entry)
    
    return saved.to_dict()


@router.get("/{symbol}/history")
async def get_audit_history(
    symbol: str,
    limit: int = 50,
    repo: AuditRepository = Depends(get_audit_repository),
):
    """
    Get assumption change history for a stock.
    
    Args:
        symbol: Stock ticker symbol
        limit: Maximum entries to return (default 50)
    
    Returns:
        List of audit entries, most recent first.
    """
    history = repo.get_history(symbol.upper(), limit=limit)
    return [entry.to_dict() for entry in history]


@router.get("/{symbol}/snapshot")
async def get_audit_snapshot(
    symbol: str,
    repo: AuditRepository = Depends(get_audit_repository),
):
    """
    Get the current assumption snapshot for a stock.
    
    Reconstructs the current state by replaying all changes.
    
    Returns:
        Current assumption values, or 404 if no history exists.
    """
    snapshot = repo.get_latest_snapshot(symbol.upper())
    
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"No audit history for {symbol}")
    
    return {
        "symbol": snapshot.symbol,
        "revenue_growth": snapshot.revenue_growth,
        "operating_margin": snapshot.operating_margin,
        "terminal_growth": snapshot.terminal_growth,
        "discount_rate": snapshot.discount_rate,
        "projection_years": snapshot.projection_years,
        "market_risk_premium": snapshot.market_risk_premium,
    }


@router.get("/{symbol}/field/{field}")
async def get_field_history(
    symbol: str,
    field: str,
    repo: AuditRepository = Depends(get_audit_repository),
):
    """
    Get change history for a specific assumption field.
    
    Args:
        symbol: Stock ticker symbol
        field: Field name (revenue_growth, operating_margin, etc.)
    
    Returns:
        List of changes for that field, most recent first.
    """
    # Validate field name
    try:
        field_enum = AssumptionField(field)
    except ValueError:
        valid_fields = [f.value for f in AssumptionField]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid field '{field}'. Valid fields: {valid_fields}"
        )
    
    changes = repo.get_field_history(symbol.upper(), field_enum)
    
    return [
        {
            "field": c.field.value,
            "old_value": c.old_value,
            "new_value": c.new_value,
        }
        for c in changes
    ]
