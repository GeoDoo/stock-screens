"""
Memo Repository - SQLite persistence for investment memos.

Stores and retrieves investment memos with post-mortems and market snapshots.
"""
import json
from datetime import datetime, timezone
from typing import List, Optional

from app.services.database import get_connection, DEFAULT_DB_PATH
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


class MemoRepository:
    """
    SQLite-based repository for investment memos.
    
    Tables:
    - memos: Core memo data
    - memo_scenarios: Scenarios at creation time
    - memo_market_snapshots: Periodic market tracking
    - memo_post_mortems: Post-mortem reviews
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize repository with database path."""
        self.db_path = db_path or str(DEFAULT_DB_PATH)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with get_connection(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS memos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    title TEXT NOT NULL,
                    thesis TEXT NOT NULL,
                    conviction TEXT NOT NULL,
                    time_horizon_months INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    
                    -- Assumptions snapshot (JSON)
                    assumptions_json TEXT NOT NULL,
                    
                    -- Initial market data
                    initial_price REAL NOT NULL,
                    initial_iv REAL NOT NULL,
                    initial_pe REAL,
                    initial_captured_at TEXT NOT NULL,
                    
                    -- Optional fields
                    target_price REAL,
                    risks TEXT,
                    catalysts TEXT,
                    what_would_change_mind TEXT,
                    
                    -- Status
                    status TEXT NOT NULL DEFAULT 'active',
                    closed_at TEXT,
                    closed_reason TEXT
                );
                
                CREATE TABLE IF NOT EXISTS memo_scenarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memo_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    revenue_growth REAL NOT NULL,
                    operating_margin REAL NOT NULL,
                    intrinsic_value REAL NOT NULL,
                    upside_percent REAL NOT NULL,
                    FOREIGN KEY (memo_id) REFERENCES memos(id) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS memo_market_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memo_id INTEGER NOT NULL,
                    price REAL NOT NULL,
                    intrinsic_value REAL NOT NULL,
                    pe_ratio REAL,
                    captured_at TEXT NOT NULL,
                    FOREIGN KEY (memo_id) REFERENCES memos(id) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS memo_post_mortems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memo_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    note TEXT NOT NULL,
                    action TEXT NOT NULL,
                    price_at_time REAL NOT NULL,
                    iv_at_time REAL NOT NULL,
                    FOREIGN KEY (memo_id) REFERENCES memos(id) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_memos_symbol ON memos(symbol);
                CREATE INDEX IF NOT EXISTS idx_memos_status ON memos(status);
                CREATE INDEX IF NOT EXISTS idx_memos_created ON memos(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_scenarios_memo ON memo_scenarios(memo_id);
                CREATE INDEX IF NOT EXISTS idx_snapshots_memo ON memo_market_snapshots(memo_id);
                CREATE INDEX IF NOT EXISTS idx_postmortems_memo ON memo_post_mortems(memo_id);
            """)
            conn.commit()
    
    def save_memo(self, memo: InvestmentMemo) -> InvestmentMemo:
        """Save a new investment memo."""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert main memo
            cursor.execute("""
                INSERT INTO memos (
                    symbol, title, thesis, conviction, time_horizon_months, created_at,
                    assumptions_json, initial_price, initial_iv, initial_pe, initial_captured_at,
                    target_price, risks, catalysts, what_would_change_mind, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memo.symbol.upper(),
                memo.title,
                memo.thesis,
                memo.conviction.value,
                memo.time_horizon_months,
                memo.created_at.isoformat(),
                json.dumps(memo.assumptions.to_dict()),
                memo.initial_market.price,
                memo.initial_market.intrinsic_value,
                memo.initial_market.pe_ratio,
                memo.initial_market.captured_at.isoformat(),
                memo.target_price,
                memo.risks,
                memo.catalysts,
                memo.what_would_change_mind,
                memo.status.value,
            ))
            
            memo_id = cursor.lastrowid
            
            # Insert scenarios
            for scenario in memo.scenarios:
                cursor.execute("""
                    INSERT INTO memo_scenarios (
                        memo_id, name, revenue_growth, operating_margin, 
                        intrinsic_value, upside_percent
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    memo_id,
                    scenario.name,
                    scenario.revenue_growth,
                    scenario.operating_margin,
                    scenario.intrinsic_value,
                    scenario.upside_percent,
                ))
            
            conn.commit()
            
            memo.id = memo_id
            return memo
    
    def get_memo(self, memo_id: int) -> Optional[InvestmentMemo]:
        """Get a memo by ID with all related data."""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get main memo
            cursor.execute("SELECT * FROM memos WHERE id = ?", (memo_id,))
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            # Get scenarios
            cursor.execute(
                "SELECT * FROM memo_scenarios WHERE memo_id = ? ORDER BY id",
                (memo_id,)
            )
            scenarios = [
                ScenarioSnapshot(
                    name=s["name"],
                    revenue_growth=s["revenue_growth"],
                    operating_margin=s["operating_margin"],
                    intrinsic_value=s["intrinsic_value"],
                    upside_percent=s["upside_percent"],
                )
                for s in cursor.fetchall()
            ]
            
            # Get market snapshots
            cursor.execute(
                "SELECT * FROM memo_market_snapshots WHERE memo_id = ? ORDER BY captured_at",
                (memo_id,)
            )
            snapshots = [
                MarketSnapshot(
                    price=s["price"],
                    intrinsic_value=s["intrinsic_value"],
                    pe_ratio=s["pe_ratio"],
                    captured_at=datetime.fromisoformat(s["captured_at"]),
                )
                for s in cursor.fetchall()
            ]
            
            # Get post-mortems
            cursor.execute(
                "SELECT * FROM memo_post_mortems WHERE memo_id = ? ORDER BY created_at",
                (memo_id,)
            )
            post_mortems = [
                PostMortem(
                    id=p["id"],
                    memo_id=p["memo_id"],
                    created_at=datetime.fromisoformat(p["created_at"]),
                    note=p["note"],
                    action=PostMortemAction(p["action"]),
                    price_at_time=p["price_at_time"],
                    iv_at_time=p["iv_at_time"],
                )
                for p in cursor.fetchall()
            ]
            
            return self._row_to_memo(row, scenarios, snapshots, post_mortems)
    
    def _row_to_memo(
        self, 
        row, 
        scenarios: List[ScenarioSnapshot],
        snapshots: List[MarketSnapshot],
        post_mortems: List[PostMortem],
    ) -> InvestmentMemo:
        """Convert database row to InvestmentMemo."""
        assumptions_data = json.loads(row["assumptions_json"])
        
        return InvestmentMemo(
            id=row["id"],
            symbol=row["symbol"],
            title=row["title"],
            thesis=row["thesis"],
            conviction=Conviction(row["conviction"]),
            time_horizon_months=row["time_horizon_months"],
            created_at=datetime.fromisoformat(row["created_at"]),
            assumptions=AssumptionsSnapshot.from_dict(assumptions_data),
            scenarios=scenarios,
            initial_market=MarketSnapshot(
                price=row["initial_price"],
                intrinsic_value=row["initial_iv"],
                pe_ratio=row["initial_pe"],
                captured_at=datetime.fromisoformat(row["initial_captured_at"]),
            ),
            target_price=row["target_price"],
            risks=row["risks"],
            catalysts=row["catalysts"],
            what_would_change_mind=row["what_would_change_mind"],
            status=MemoStatus(row["status"]),
            closed_at=datetime.fromisoformat(row["closed_at"]) if row["closed_at"] else None,
            closed_reason=row["closed_reason"],
            market_snapshots=snapshots,
            post_mortems=post_mortems,
        )
    
    def list_memos(
        self,
        symbol: Optional[str] = None,
        status: Optional[MemoStatus] = None,
        limit: int = 50,
    ) -> List[InvestmentMemo]:
        """List memos with optional filtering."""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM memos WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol.upper())
            
            if status:
                query += " AND status = ?"
                params.append(status.value)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            memos = []
            for row in rows:
                memo = self.get_memo(row["id"])
                if memo:
                    memos.append(memo)
            
            return memos
    
    def update_memo(self, memo: InvestmentMemo) -> InvestmentMemo:
        """Update an existing memo."""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE memos SET
                    title = ?,
                    thesis = ?,
                    conviction = ?,
                    time_horizon_months = ?,
                    target_price = ?,
                    risks = ?,
                    catalysts = ?,
                    what_would_change_mind = ?
                WHERE id = ?
            """, (
                memo.title,
                memo.thesis,
                memo.conviction.value,
                memo.time_horizon_months,
                memo.target_price,
                memo.risks,
                memo.catalysts,
                memo.what_would_change_mind,
                memo.id,
            ))
            
            conn.commit()
            
            return self.get_memo(memo.id)
    
    def close_memo(
        self, 
        memo_id: int, 
        status: MemoStatus, 
        reason: str,
    ) -> InvestmentMemo:
        """Close a memo with final status and reason."""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE memos SET
                    status = ?,
                    closed_at = ?,
                    closed_reason = ?
                WHERE id = ?
            """, (
                status.value,
                datetime.now(timezone.utc).isoformat(),
                reason,
                memo_id,
            ))
            
            conn.commit()
            
            return self.get_memo(memo_id)
    
    def delete_memo(self, memo_id: int) -> None:
        """Delete a memo and all related data."""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Delete related data first (foreign key cascade should handle this,
            # but being explicit for SQLite compatibility)
            cursor.execute("DELETE FROM memo_post_mortems WHERE memo_id = ?", (memo_id,))
            cursor.execute("DELETE FROM memo_market_snapshots WHERE memo_id = ?", (memo_id,))
            cursor.execute("DELETE FROM memo_scenarios WHERE memo_id = ?", (memo_id,))
            cursor.execute("DELETE FROM memos WHERE id = ?", (memo_id,))
            
            conn.commit()
    
    def add_post_mortem(self, post_mortem: PostMortem) -> PostMortem:
        """Add a post-mortem review to a memo."""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO memo_post_mortems (
                    memo_id, created_at, note, action, price_at_time, iv_at_time
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                post_mortem.memo_id,
                post_mortem.created_at.isoformat(),
                post_mortem.note,
                post_mortem.action.value,
                post_mortem.price_at_time,
                post_mortem.iv_at_time,
            ))
            
            conn.commit()
            
            post_mortem.id = cursor.lastrowid
            return post_mortem
    
    def add_market_snapshot(self, memo_id: int, snapshot: MarketSnapshot) -> MarketSnapshot:
        """Add a market snapshot for tracking."""
        with get_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO memo_market_snapshots (
                    memo_id, price, intrinsic_value, pe_ratio, captured_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                memo_id,
                snapshot.price,
                snapshot.intrinsic_value,
                snapshot.pe_ratio,
                snapshot.captured_at.isoformat(),
            ))
            
            conn.commit()
            
            return snapshot


# Singleton instance
_memo_repo: Optional[MemoRepository] = None


def get_memo_repository() -> MemoRepository:
    """Get the singleton memo repository instance."""
    global _memo_repo
    if _memo_repo is None:
        _memo_repo = MemoRepository()
    return _memo_repo
