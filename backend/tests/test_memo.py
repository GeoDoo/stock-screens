"""
Tests for Investment Memo feature.
TDD: Tests written before implementation.
"""
import pytest
from datetime import datetime, timedelta, timezone
import tempfile
import os

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


class TestMemoModels:
    """Test memo data models."""
    
    def test_assumptions_snapshot_to_dict(self):
        """AssumptionsSnapshot should serialize to dict."""
        snapshot = AssumptionsSnapshot(
            revenue_growth=0.10,
            operating_margin=0.25,
            terminal_growth_rate=0.03,
            discount_rate=0.09,
            projection_years=10,
        )
        
        d = snapshot.to_dict()
        assert d["revenue_growth"] == 0.10
        assert d["operating_margin"] == 0.25
        assert d["discount_rate"] == 0.09
    
    def test_assumptions_snapshot_from_dict(self):
        """AssumptionsSnapshot should deserialize from dict."""
        data = {
            "revenue_growth": 0.10,
            "operating_margin": 0.25,
            "terminal_growth_rate": 0.03,
            "discount_rate": 0.09,
            "projection_years": 10,
        }
        
        snapshot = AssumptionsSnapshot.from_dict(data)
        assert snapshot.revenue_growth == 0.10
        assert snapshot.projection_years == 10
    
    def test_memo_calculates_performance(self):
        """Memo should calculate performance vs thesis."""
        memo = InvestmentMemo(
            id=1,
            symbol="AAPL",
            title="AI iPhone Cycle",
            thesis="Apple will benefit from AI features",
            conviction=Conviction.HIGH,
            time_horizon_months=12,
            created_at=datetime.now(timezone.utc),
            assumptions=AssumptionsSnapshot(
                revenue_growth=0.10,
                operating_margin=0.30,
                terminal_growth_rate=0.03,
                discount_rate=0.09,
                projection_years=10,
            ),
            scenarios=[],
            initial_market=MarketSnapshot(
                price=150.0,
                intrinsic_value=200.0,  # 33% upside
            ),
        )
        
        # Add a market snapshot showing price went up
        memo.market_snapshots.append(MarketSnapshot(
            price=175.0,  # +16.7%
            intrinsic_value=210.0,
        ))
        
        perf = memo._calculate_performance()
        assert perf["price_change_percent"] == pytest.approx(16.67, rel=0.1)
        assert perf["original_upside_percent"] == pytest.approx(33.33, rel=0.1)
        # Thesis 50% realized (16.67/33.33)
        assert perf["thesis_realized_percent"] == pytest.approx(50.0, rel=0.1)
    
    def test_memo_to_dict_complete(self):
        """Memo should serialize completely."""
        memo = InvestmentMemo(
            id=1,
            symbol="MSFT",
            title="Cloud Dominance",
            thesis="Azure will continue gaining share",
            conviction=Conviction.MEDIUM,
            time_horizon_months=18,
            created_at=datetime(2024, 1, 15),
            assumptions=AssumptionsSnapshot(
                revenue_growth=0.12,
                operating_margin=0.40,
                terminal_growth_rate=0.03,
                discount_rate=0.085,
                projection_years=10,
            ),
            scenarios=[
                ScenarioSnapshot(
                    name="Bull",
                    revenue_growth=0.15,
                    operating_margin=0.42,
                    intrinsic_value=450.0,
                    upside_percent=20.0,
                ),
                ScenarioSnapshot(
                    name="Base",
                    revenue_growth=0.12,
                    operating_margin=0.40,
                    intrinsic_value=400.0,
                    upside_percent=7.0,
                ),
            ],
            initial_market=MarketSnapshot(
                price=375.0,
                intrinsic_value=400.0,
                pe_ratio=32.0,
            ),
            target_price=420.0,
            risks="Cloud competition from AWS/GCP",
            catalysts="AI integration across products",
        )
        
        d = memo.to_dict()
        assert d["symbol"] == "MSFT"
        assert d["title"] == "Cloud Dominance"
        assert d["conviction"] == "medium"
        assert len(d["scenarios"]) == 2
        assert d["target_price"] == 420.0
        assert "current_performance" in d


class TestMemoRepository:
    """Test memo persistence."""
    
    @pytest.fixture
    def repo(self):
        """Create a memo repository with temp database."""
        from app.services.memo_repository import MemoRepository
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        repo = MemoRepository(db_path=db_path)
        yield repo
        
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def sample_memo(self) -> InvestmentMemo:
        """Create a sample memo for testing."""
        return InvestmentMemo(
            id=None,
            symbol="AAPL",
            title="AI iPhone Cycle",
            thesis="Apple's integration of AI will drive upgrade cycle",
            conviction=Conviction.HIGH,
            time_horizon_months=12,
            created_at=datetime.now(timezone.utc),
            assumptions=AssumptionsSnapshot(
                revenue_growth=0.08,
                operating_margin=0.30,
                terminal_growth_rate=0.03,
                discount_rate=0.095,
                projection_years=10,
            ),
            scenarios=[
                ScenarioSnapshot(
                    name="Bull",
                    revenue_growth=0.12,
                    operating_margin=0.32,
                    intrinsic_value=250.0,
                    upside_percent=35.0,
                ),
                ScenarioSnapshot(
                    name="Base",
                    revenue_growth=0.08,
                    operating_margin=0.30,
                    intrinsic_value=220.0,
                    upside_percent=19.0,
                ),
                ScenarioSnapshot(
                    name="Bear",
                    revenue_growth=0.04,
                    operating_margin=0.28,
                    intrinsic_value=175.0,
                    upside_percent=-5.0,
                ),
            ],
            initial_market=MarketSnapshot(
                price=185.0,
                intrinsic_value=220.0,
                pe_ratio=28.5,
            ),
            target_price=220.0,
            risks="China regulatory risk, smartphone saturation",
            catalysts="iPhone 16 AI features, Vision Pro adoption",
            what_would_change_mind="Services growth stalls below 10%",
        )
    
    def test_save_and_retrieve_memo(self, repo, sample_memo):
        """Should save memo and retrieve it with ID."""
        saved = repo.save_memo(sample_memo)
        
        assert saved.id is not None
        assert saved.symbol == "AAPL"
        assert saved.title == "AI iPhone Cycle"
        
        # Retrieve it
        retrieved = repo.get_memo(saved.id)
        assert retrieved is not None
        assert retrieved.symbol == "AAPL"
        assert retrieved.conviction == Conviction.HIGH
        assert len(retrieved.scenarios) == 3
    
    def test_list_memos_for_symbol(self, repo, sample_memo):
        """Should list all memos for a symbol."""
        # Save two memos for AAPL
        repo.save_memo(sample_memo)
        
        sample_memo.title = "Services Growth Story"
        sample_memo.id = None
        repo.save_memo(sample_memo)
        
        memos = repo.list_memos(symbol="AAPL")
        assert len(memos) == 2
    
    def test_list_all_memos(self, repo, sample_memo):
        """Should list all memos across symbols."""
        repo.save_memo(sample_memo)
        
        sample_memo.symbol = "MSFT"
        sample_memo.title = "Cloud Growth"
        sample_memo.id = None
        repo.save_memo(sample_memo)
        
        all_memos = repo.list_memos()
        assert len(all_memos) == 2
    
    def test_list_active_memos_only(self, repo, sample_memo):
        """Should filter by status."""
        saved = repo.save_memo(sample_memo)
        
        # Close the memo
        repo.close_memo(saved.id, MemoStatus.CLOSED_WIN, "Thesis played out")
        
        active = repo.list_memos(status=MemoStatus.ACTIVE)
        assert len(active) == 0
        
        closed = repo.list_memos(status=MemoStatus.CLOSED_WIN)
        assert len(closed) == 1
    
    def test_add_post_mortem(self, repo, sample_memo):
        """Should add post-mortem to memo."""
        saved = repo.save_memo(sample_memo)
        
        post_mortem = PostMortem(
            id=None,
            memo_id=saved.id,
            created_at=datetime.now(timezone.utc),
            note="Q1 earnings beat, AI features resonating",
            action=PostMortemAction.HOLD,
            price_at_time=195.0,
            iv_at_time=225.0,
        )
        
        saved_pm = repo.add_post_mortem(post_mortem)
        assert saved_pm.id is not None
        
        # Retrieve memo with post-mortems
        memo = repo.get_memo(saved.id)
        assert len(memo.post_mortems) == 1
        assert memo.post_mortems[0].action == PostMortemAction.HOLD
    
    def test_add_market_snapshot(self, repo, sample_memo):
        """Should track market snapshots over time."""
        saved = repo.save_memo(sample_memo)
        
        # Add weekly snapshots
        repo.add_market_snapshot(saved.id, MarketSnapshot(
            price=190.0,
            intrinsic_value=222.0,
            pe_ratio=29.0,
        ))
        repo.add_market_snapshot(saved.id, MarketSnapshot(
            price=195.0,
            intrinsic_value=225.0,
            pe_ratio=29.5,
        ))
        
        memo = repo.get_memo(saved.id)
        assert len(memo.market_snapshots) == 2
        assert memo.market_snapshots[-1].price == 195.0
    
    def test_close_memo(self, repo, sample_memo):
        """Should close memo with reason."""
        saved = repo.save_memo(sample_memo)
        
        repo.close_memo(
            saved.id, 
            MemoStatus.CLOSED_WIN, 
            "Target reached, thesis fully realized"
        )
        
        memo = repo.get_memo(saved.id)
        assert memo.status == MemoStatus.CLOSED_WIN
        assert memo.closed_at is not None
        assert "fully realized" in memo.closed_reason
    
    def test_update_memo(self, repo, sample_memo):
        """Should update memo fields."""
        saved = repo.save_memo(sample_memo)
        
        saved.target_price = 240.0
        saved.risks = "Updated risk assessment"
        
        updated = repo.update_memo(saved)
        
        retrieved = repo.get_memo(saved.id)
        assert retrieved.target_price == 240.0
        assert "Updated" in retrieved.risks
    
    def test_delete_memo(self, repo, sample_memo):
        """Should delete memo and all related data."""
        saved = repo.save_memo(sample_memo)
        
        # Add some related data
        repo.add_post_mortem(PostMortem(
            id=None,
            memo_id=saved.id,
            created_at=datetime.now(timezone.utc),
            note="Test",
            action=PostMortemAction.REVIEW,
            price_at_time=185.0,
            iv_at_time=220.0,
        ))
        
        repo.delete_memo(saved.id)
        
        assert repo.get_memo(saved.id) is None
    
    def test_memos_ordered_by_created_at(self, repo, sample_memo):
        """Memos should be returned newest first."""
        # Save first memo
        sample_memo.created_at = datetime.now(timezone.utc) - timedelta(days=30)
        repo.save_memo(sample_memo)
        
        # Save second memo (newer)
        sample_memo.id = None
        sample_memo.title = "Newer Memo"
        sample_memo.created_at = datetime.now(timezone.utc)
        repo.save_memo(sample_memo)
        
        memos = repo.list_memos()
        assert memos[0].title == "Newer Memo"


class TestMemoAPI:
    """Test memo API endpoints."""
    
    @pytest.fixture
    def client(self, tmp_path):
        """Create test client with isolated database."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.services.memo_repository import MemoRepository, get_memo_repository
        
        # Create isolated test repository
        test_db = str(tmp_path / "test_memos.db")
        test_repo = MemoRepository(db_path=test_db)
        
        # Override dependency
        app.dependency_overrides[get_memo_repository] = lambda: test_repo
        
        yield TestClient(app)
        
        # Cleanup
        app.dependency_overrides.clear()
    
    def test_create_memo(self, client):
        """POST /api/memos should create memo."""
        response = client.post("/api/memos", json={
            "symbol": "NVDA",
            "title": "AI Chip Dominance",
            "thesis": "NVIDIA will maintain GPU leadership in AI training",
            "conviction": "high",
            "time_horizon_months": 24,
            "assumptions": {
                "revenue_growth": 0.25,
                "operating_margin": 0.55,
                "terminal_growth_rate": 0.04,
                "discount_rate": 0.10,
                "projection_years": 10,
            },
            "scenarios": [
                {
                    "name": "Bull",
                    "revenue_growth": 0.35,
                    "operating_margin": 0.58,
                    "intrinsic_value": 180.0,
                    "upside_percent": 50.0,
                },
            ],
            "initial_market": {
                "price": 120.0,
                "intrinsic_value": 150.0,
                "pe_ratio": 65.0,
            },
            "target_price": 160.0,
            "risks": "Competition from AMD, custom chips",
            "catalysts": "Data center buildout, AI model scaling",
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["symbol"] == "NVDA"
    
    def test_get_memo(self, client):
        """GET /api/memos/{id} should return memo."""
        # First create one
        create_resp = client.post("/api/memos", json={
            "symbol": "GOOG",
            "title": "Search Moat",
            "thesis": "Google maintains search dominance",
            "conviction": "medium",
            "time_horizon_months": 12,
            "assumptions": {
                "revenue_growth": 0.10,
                "operating_margin": 0.28,
                "terminal_growth_rate": 0.03,
                "discount_rate": 0.09,
                "projection_years": 10,
            },
            "scenarios": [],
            "initial_market": {
                "price": 140.0,
                "intrinsic_value": 165.0,
            },
        })
        memo_id = create_resp.json()["id"]
        
        # Then get it
        response = client.get(f"/api/memos/{memo_id}")
        assert response.status_code == 200
        assert response.json()["symbol"] == "GOOG"
    
    def test_list_memos(self, client):
        """GET /api/memos should list memos."""
        response = client.get("/api/memos")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_add_post_mortem(self, client):
        """POST /api/memos/{id}/post-mortems should add post-mortem."""
        # Create memo first
        create_resp = client.post("/api/memos", json={
            "symbol": "META",
            "title": "Reels Monetization",
            "thesis": "Meta will successfully monetize Reels",
            "conviction": "medium",
            "time_horizon_months": 18,
            "assumptions": {
                "revenue_growth": 0.15,
                "operating_margin": 0.35,
                "terminal_growth_rate": 0.03,
                "discount_rate": 0.095,
                "projection_years": 10,
            },
            "scenarios": [],
            "initial_market": {
                "price": 350.0,
                "intrinsic_value": 420.0,
            },
        })
        memo_id = create_resp.json()["id"]
        
        # Add post-mortem
        response = client.post(f"/api/memos/{memo_id}/post-mortems", json={
            "note": "Q2 showed Reels engagement up 30%",
            "action": "hold",
            "price_at_time": 380.0,
            "iv_at_time": 430.0,
        })
        
        assert response.status_code == 201
        assert response.json()["action"] == "hold"
    
    def test_close_memo(self, client):
        """POST /api/memos/{id}/close should close memo."""
        # Create memo first
        create_resp = client.post("/api/memos", json={
            "symbol": "AMZN",
            "title": "AWS Growth",
            "thesis": "AWS will re-accelerate",
            "conviction": "low",
            "time_horizon_months": 6,
            "assumptions": {
                "revenue_growth": 0.12,
                "operating_margin": 0.08,
                "terminal_growth_rate": 0.03,
                "discount_rate": 0.09,
                "projection_years": 10,
            },
            "scenarios": [],
            "initial_market": {
                "price": 180.0,
                "intrinsic_value": 200.0,
            },
        })
        memo_id = create_resp.json()["id"]
        
        # Close it
        response = client.post(f"/api/memos/{memo_id}/close", json={
            "status": "closed_loss",
            "reason": "AWS growth continued to decelerate",
        })
        
        assert response.status_code == 200
        assert response.json()["status"] == "closed_loss"
