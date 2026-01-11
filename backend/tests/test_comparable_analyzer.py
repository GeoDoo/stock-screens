"""
Tests for ComparableAnalyzer service.

Focus on EBITDA wiring regression test - ensuring D&A is read from 
cash_flow, not income_statement.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.comparable_analyzer import ComparableAnalyzer, CompanyMetrics, ImpliedValuation


class TestComparableAnalyzerEBITDAWiring:
    """
    Regression tests for EBITDA calculation in ComparableAnalyzer.
    
    Bug: D&A was being read from income_statement (financials), but 
    stock_data_to_legacy() places it in cash_flow. This caused EBITDA
    to equal operating_income (D&A treated as 0), making EV/EBITDA incorrect.
    """

    def test_extract_metrics_reads_da_from_cash_flow(self):
        """
        _extract_metrics should read D&A from cash_flow, not income_statement.
        """
        # Create analyzer with mock client
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Realistic data structure: D&A in cash_flow only (as produced by stock_data_to_legacy)
        data = {
            "profile": {
                "price": 150.0,
                "marketCap": 2400000000000,  # 2.4T
                "sharesOutstanding": 16000000000,
            },
            "income_statement": [
                {
                    "revenue": 400000000000,  # 400B
                    "netIncome": 100000000000,  # 100B
                    "operatingIncome": 120000000000,  # 120B
                    # NOTE: No depreciationAndAmortization here!
                }
            ],
            "balance_sheet": [
                {
                    "totalDebt": 100000000000,  # 100B
                    "cashAndCashEquivalents": 25000000000,  # 25B
                    "totalStockholdersEquity": 60000000000,  # 60B
                }
            ],
            "cash_flow": [
                {
                    # D&A is in cash_flow, as produced by stock_data_to_legacy()
                    "depreciationAndAmortization": 10000000000,  # 10B
                }
            ],
        }
        
        metrics = analyzer._extract_metrics("AAPL", data)
        
        # EBITDA = Operating Income (120B) + D&A (10B) = 130B
        # EV = 2.4T + 100B - 25B = 2.475T
        # EV/EBITDA = 2.475T / 130B = 19.04
        
        # If bug exists: EBITDA = 120B (D&A=0 because read from wrong location)
        # EV/EBITDA would be 2.475T / 120B = 20.625 (WRONG)
        
        assert metrics.ev_to_ebitda == pytest.approx(19.04, rel=0.01), (
            f"EV/EBITDA should be ~19.04 but got {metrics.ev_to_ebitda}. "
            "D&A is being read from income_statement instead of cash_flow."
        )

    def test_extract_metrics_handles_missing_da_gracefully(self):
        """
        If D&A is missing from cash_flow, should still calculate EBITDA 
        (just without D&A component, i.e. EBITDA = operating_income).
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        data = {
            "profile": {
                "price": 100.0,
                "marketCap": 1000000000000,  # 1T
                "sharesOutstanding": 10000000000,
            },
            "income_statement": [
                {
                    "operatingIncome": 50000000000,  # 50B
                }
            ],
            "balance_sheet": [
                {
                    "totalDebt": 0,
                    "cashAndCashEquivalents": 0,
                }
            ],
            "cash_flow": [
                {
                    # No D&A at all
                }
            ],
        }
        
        metrics = analyzer._extract_metrics("TEST", data)
        
        # EBITDA = 50B + 0 = 50B
        # EV = 1T
        # EV/EBITDA = 1T / 50B = 20
        
        assert metrics.ev_to_ebitda == pytest.approx(20.0, rel=0.01)


class TestEVEBITDAImpliedValuation:
    """
    Regression tests for EV/EBITDA implied price calculation.
    
    Bug: The old code used "ratio of ratios" shortcut:
        implied_price = current_price × (peer_multiple / target_multiple)
    
    This is financially invalid because it assumes Net Debt scales with
    stock price, but debt is a fixed contract. The correct approach:
        1. Implied EV = Peer EV/EBITDA × Target EBITDA
        2. Implied Equity = Implied EV - Target Net Debt
        3. Implied Price = Implied Equity / Shares
    """
    
    def test_ev_ebitda_implied_price_correct_method(self):
        """
        EV/EBITDA implied price should use proper EV-to-equity bridge.
        
        Example with significant leverage:
        - Target: Price $100, EV/EBITDA 10x, EBITDA $100B, Net Debt $500B
        - Peer Median: EV/EBITDA 15x
        
        WRONG (ratio of ratios):
            implied = $100 × (15/10) = $150 (50% upside)
        
        CORRECT (EV bridge):
            Implied EV = 15 × $100B = $1.5T
            Current EV = 10 × $100B = $1.0T
            Current Equity = $1.0T - $500B = $500B
            Implied Equity = $1.5T - $500B = $1.0T (2x, not 1.5x!)
            Implied Price = $100 × ($1.0T / $500B) = $200 (100% upside!)
        
        For leveraged companies, the correct method shows MORE upside
        because debt amplifies equity returns.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Create target with significant leverage
        target = CompanyMetrics(
            symbol="LEVCO",
            name="Leveraged Company",
            price=100.0,
            market_cap=500_000_000_000,  # $500B market cap (equity)
            ev_to_ebitda=10.0,
            # Additional fields needed for proper calculation
            ebitda=100_000_000_000,  # $100B EBITDA
            net_debt=500_000_000_000,  # $500B net debt (EV = 1T)
            shares_outstanding=5_000_000_000,  # 5B shares → $100/share
        )
        
        peer_medians = {
            "ev_to_ebitda": 15.0,  # Peers trade at 15x
        }
        
        valuations = analyzer._calculate_implied_valuations(target, peer_medians)
        
        # Find EV/EBITDA valuation
        ev_ebitda_val = next(
            (v for v in valuations if v.metric_name == "EV/EBITDA"), 
            None
        )
        
        assert ev_ebitda_val is not None, "Should have EV/EBITDA implied valuation"
        
        # Correct calculation:
        # Implied EV = 15x × $100B = $1.5T
        # Implied Equity = $1.5T - $500B = $1.0T
        # Implied Price = $1.0T / 5B shares = $200
        expected_implied_price = 200.0
        
        # Wrong calculation would give: $100 × (15/10) = $150
        wrong_implied_price = 150.0
        
        assert ev_ebitda_val.implied_price == pytest.approx(expected_implied_price, rel=0.01), (
            f"EV/EBITDA implied price should be ${expected_implied_price} "
            f"(correct EV bridge), got ${ev_ebitda_val.implied_price}. "
            f"If got ${wrong_implied_price}, the 'ratio of ratios' bug is present."
        )
        
        # Upside should be 100%, not 50%
        assert ev_ebitda_val.upside_percent == pytest.approx(100.0, rel=1), (
            f"Upside should be ~100% for leveraged company, got {ev_ebitda_val.upside_percent}%"
        )
    
    def test_ev_ebitda_implied_price_no_debt(self):
        """
        With zero net debt, both methods should give same result.
        This validates the math converges in the simple case.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Debt-free company: EV = Equity
        target = CompanyMetrics(
            symbol="NODET",
            name="No Debt Corp",
            price=100.0,
            market_cap=1_000_000_000_000,  # $1T
            ev_to_ebitda=10.0,
            ebitda=100_000_000_000,  # $100B
            net_debt=0,  # No debt!
            shares_outstanding=10_000_000_000,
        )
        
        peer_medians = {"ev_to_ebitda": 15.0}
        
        valuations = analyzer._calculate_implied_valuations(target, peer_medians)
        ev_ebitda_val = next((v for v in valuations if v.metric_name == "EV/EBITDA"), None)
        
        # With no debt: Implied EV = Implied Equity
        # Implied EV = 15 × $100B = $1.5T
        # Implied Price = $1.5T / 10B = $150
        assert ev_ebitda_val.implied_price == pytest.approx(150.0, rel=0.01)
        assert ev_ebitda_val.upside_percent == pytest.approx(50.0, rel=1)
    
    def test_ev_ebitda_with_net_cash(self):
        """
        Companies with net cash (negative net debt) should also work correctly.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Company with net cash: Market cap > EV
        target = CompanyMetrics(
            symbol="CASHCO",
            name="Cash Rich Corp",
            price=100.0,
            market_cap=1_200_000_000_000,  # $1.2T market cap
            ev_to_ebitda=10.0,
            ebitda=100_000_000_000,  # $100B
            net_debt=-200_000_000_000,  # -$200B (net cash)
            shares_outstanding=12_000_000_000,
        )
        
        peer_medians = {"ev_to_ebitda": 15.0}
        
        valuations = analyzer._calculate_implied_valuations(target, peer_medians)
        ev_ebitda_val = next((v for v in valuations if v.metric_name == "EV/EBITDA"), None)
        
        # Implied EV = 15 × $100B = $1.5T
        # Implied Equity = $1.5T - (-$200B) = $1.7T
        # Implied Price = $1.7T / 12B = $141.67
        assert ev_ebitda_val.implied_price == pytest.approx(141.67, rel=0.01)


class TestDynamicIndustryPeers:
    """
    Tests for dynamic sub-industry peer selection.
    
    Problem: Static SECTOR_PEERS groups all Technology companies together,
    but Apple (Consumer Electronics) shouldn't be compared to Salesforce (CRM).
    
    Solution: Use industry-level peers when available, fall back to sector.
    """
    
    def test_get_peers_prefers_industry_over_sector(self):
        """
        When industry peers are available, use them instead of sector peers.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Apple's industry is "Consumer Electronics" (not just "Technology")
        peers = analyzer._get_peers(
            symbol="AAPL",
            sector="Technology",
            industry="Consumer Electronics",
        )
        
        # Should get Consumer Electronics peers, NOT broad Technology
        # (Microsoft, Google, etc. are NOT Consumer Electronics)
        assert "MSFT" not in peers, "MSFT is Software, not Consumer Electronics"
        assert "GOOGL" not in peers, "GOOGL is Internet Services, not Consumer Electronics"
        
        # Should include actual Consumer Electronics peers
        # SNE (Sony), HPQ (HP), DELL, LGI.F (LG) are Consumer Electronics
        # Note: At minimum we expect SOME peers from the industry mapping
        assert len(peers) >= 1, "Should find at least one industry peer"
    
    def test_falls_back_to_sector_when_no_industry_peers(self):
        """
        When industry has no defined peers, fall back to sector peers.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Use an obscure industry that won't have specific peers
        peers = analyzer._get_peers(
            symbol="TEST",
            sector="Technology",
            industry="Obscure Niche Tech",  # Not in INDUSTRY_PEERS
        )
        
        # Should fall back to Technology sector peers
        assert len(peers) > 0, "Should fall back to sector peers"
        # Verify we get sector-level peers
        tech_peers = analyzer.SECTOR_PEERS.get("Technology", [])
        assert any(p in tech_peers for p in peers), "Should include sector peers"
    
    def test_industry_peers_exist_for_common_industries(self):
        """
        INDUSTRY_PEERS should cover common industries for better granularity.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # These industries should have specific peer groups
        expected_industries = [
            "Consumer Electronics",
            "Software—Infrastructure",
            "Software—Application",
            "Internet Content & Information",
            "Semiconductors",
            "Banks—Diversified",
            "Drug Manufacturers—General",
            "Auto Manufacturers",
        ]
        
        for industry in expected_industries:
            assert industry in analyzer.INDUSTRY_PEERS, (
                f"INDUSTRY_PEERS should include '{industry}' for proper comparable analysis"
            )
    
    def test_industry_peers_handles_naming_variations(self):
        """
        P1 Bug: Industry names from different providers may use hyphens vs em-dashes.
        The peer lookup should handle common variations.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Get the expected industry peers using the canonical name
        expected_peers = analyzer.INDUSTRY_PEERS.get("Software—Infrastructure", [])
        assert len(expected_peers) > 0, "Test setup: Software—Infrastructure should have peers"
        
        # Test hyphen variation gets matched to em-dash entry
        peers = analyzer._get_peers(
            symbol="MSFT",
            sector="Technology",
            industry="Software-Infrastructure",  # Regular hyphen, not em-dash
        )
        
        # Should get the SAME industry peers as the canonical name, not sector fallback
        # Verify by checking that we got industry-specific peers, not generic sector peers
        sector_peers = analyzer.SECTOR_PEERS.get("Technology", [])
        
        # The returned peers should match industry peers (minus MSFT), not sector peers
        assert set(peers) == set(p for p in expected_peers if p != "MSFT"), (
            f"Hyphen variant 'Software-Infrastructure' should return same peers as "
            f"em-dash variant 'Software—Infrastructure'. Got {peers}, expected {expected_peers}"
        )
    
    def test_basic_materials_industries_covered(self):
        """
        Basic Materials sector should have industry-level peer groups.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        basic_materials_industries = [
            "Specialty Chemicals",
            "Agricultural Inputs",
            "Steel",
            "Gold",
            "Copper",
        ]
        
        covered = sum(1 for ind in basic_materials_industries if ind in analyzer.INDUSTRY_PEERS)
        assert covered >= 3, (
            f"Basic Materials should have at least 3 industry groups covered, got {covered}"
        )
    
    def test_excludes_target_from_peers(self):
        """
        Target company should never appear in its own peer list.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        peers = analyzer._get_peers(
            symbol="AAPL",
            sector="Technology",
            industry="Consumer Electronics",
        )
        
        assert "AAPL" not in peers, "Target should not be in its own peer list"
    
    def test_result_indicates_peer_source(self):
        """
        ComparableResult should indicate if industry or sector peers were used.
        """
        # This helps users understand the quality of the comparison
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Method to check peer source
        source = analyzer._get_peer_source(
            sector="Technology",
            industry="Consumer Electronics",
        )
        assert source == "industry", "Should use industry peers when available"
        
        source = analyzer._get_peer_source(
            sector="Technology",
            industry="Unknown Niche",
        )
        assert source == "sector", "Should fall back to sector"


class TestCurrencyNormalization:
    """
    Tests for P2: Currency normalization in comparable analysis.
    
    Problem: When comparing companies across different reporting currencies
    (e.g., US company vs UK company), market caps and EBITDAs are in different
    currencies, making direct comparison incorrect.
    
    Solution: Normalize all peer values to the target's reporting currency
    using exchange rates before calculating medians and implied valuations.
    """
    
    def test_company_metrics_includes_currency(self):
        """
        CompanyMetrics should track the reporting currency for each company.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        data = {
            "profile": {
                "price": 150.0,
                "marketCap": 2400000000000,
                "sharesOutstanding": 16000000000,
                "currency": "GBP",  # British Pounds
            },
            "income_statement": [
                {"revenue": 400000000000, "operatingIncome": 120000000000}
            ],
            "balance_sheet": [
                {"totalDebt": 0, "cashAndCashEquivalents": 0}
            ],
            "cash_flow": [{}],
        }
        
        metrics = analyzer._extract_metrics("BP", data)
        
        assert hasattr(metrics, "currency"), "CompanyMetrics should have currency field"
        assert metrics.currency == "GBP", "Should extract currency from profile"
    
    def test_currency_defaults_to_usd(self):
        """
        When currency is not specified, default to USD.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        data = {
            "profile": {
                "price": 150.0,
                "marketCap": 2400000000000,
                "sharesOutstanding": 16000000000,
                # No currency field
            },
            "income_statement": [{}],
            "balance_sheet": [{}],
            "cash_flow": [{}],
        }
        
        metrics = analyzer._extract_metrics("AAPL", data)
        
        assert metrics.currency == "USD", "Should default to USD when no currency"
    
    def test_normalize_peer_values_to_target_currency(self):
        """
        When calculating medians, peer values should be converted to target's currency.
        
        Example:
        - Target: AAPL (USD)
        - Peer: SNE (Sony, JPY)
        - Sony's EV/EBITDA is calculated in JPY, but should be same ratio
          The market cap and EBITDA both need conversion for absolute values
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Create target in USD
        target = CompanyMetrics(
            symbol="AAPL",
            name="Apple",
            price=190.0,
            market_cap=3_000_000_000_000,  # $3T
            ebitda=130_000_000_000,  # $130B
            currency="USD",
        )
        
        # Create peer in JPY (Sony)
        # At 150 JPY/USD: ¥45T = $300B, ¥3T = $20B
        sony_jpy = CompanyMetrics(
            symbol="SNE",
            name="Sony",
            price=14_000,  # ¥14,000
            market_cap=45_000_000_000_000,  # ¥45T
            ebitda=3_000_000_000_000,  # ¥3T
            ev_to_ebitda=15.0,  # This ratio is currency-agnostic
            currency="JPY",
        )
        
        # Provide exchange rates
        exchange_rates = {"JPY": 150.0}  # 150 JPY = 1 USD
        
        # Normalize Sony's values to USD
        normalized = analyzer._normalize_to_currency(sony_jpy, "USD", exchange_rates)
        
        # Market cap should convert: ¥45T / 150 = $300B
        assert normalized.market_cap == pytest.approx(300_000_000_000, rel=0.01)
        
        # EBITDA should convert: ¥3T / 150 = $20B
        assert normalized.ebitda == pytest.approx(20_000_000_000, rel=0.01)
        
        # EV/EBITDA ratio should remain same (it's a ratio!)
        assert normalized.ev_to_ebitda == 15.0
        
        # Currency should now be USD
        assert normalized.currency == "USD"
    
    def test_comparable_result_includes_currency_info(self):
        """
        ComparableResult should indicate what currencies were involved
        and which peers required conversion.
        """
        from app.services.comparable_analyzer import ComparableResult
        
        # The result should have fields showing currency normalization
        # Check that ComparableResult can accept currency metadata
        # (This is a structural test for the dataclass)
        
        # This test validates the interface exists - actual implementation
        # will happen in the integration test
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Verify analyzer has method to normalize
        assert hasattr(analyzer, "_normalize_to_currency"), (
            "ComparableAnalyzer should have _normalize_to_currency method"
        )
    
    def test_currency_conversion_marks_approximate_rates(self):
        """
        P1.3 (NOTES.md): FX rates should be marked as approximate when
        using fallback rates (not a live FX API).
        
        This ensures users know the currency conversion is an estimate.
        """
        from app.services.comparable_analyzer import CurrencyConversion, ComparableResult
        
        # Create a conversion with approximate rate
        conversion = CurrencyConversion(
            symbol="SONY",
            original_currency="JPY",
            converted_to="USD",
            rate=0.00667,  # Approximate 1/150
            is_approximate=True,
        )
        
        assert conversion.is_approximate is True, (
            "Currency conversions using fallback rates should be marked as approximate"
        )
        
        # Create a ComparableResult with approximate conversions
        result = ComparableResult(
            target=None,  # type: ignore
            peers=[],
            sector="Technology",
            industry="Consumer Electronics",
            peer_medians={},
            implied_valuations=[],
            average_implied_price=None,
            average_upside=None,
            base_currency="USD",
            currency_conversions=[conversion],
            fx_rates_approximate=True,
        )
        
        assert result.fx_rates_approximate is True, (
            "ComparableResult should have fx_rates_approximate=True when any conversion is approximate"
        )


class TestBusinessTypeGating:
    """
    P2 #8: Business-type gating for comparable analysis.
    
    For financial companies:
    - EV/EBITDA is less meaningful (balance sheet IS the product)
    - Price/Book should be the primary valuation metric
    
    For cyclical companies:
    - Current multiples may be at cycle peaks/troughs
    - Should note need for mid-cycle normalization
    """
    
    def test_financial_company_adds_valuation_note(self):
        """
        Financial sector companies should get a note about P/B being preferred.
        """
        from app.services.comparable_analyzer import ComparableResult, CompanyMetrics
        
        # ComparableResult should have a valuation_notes field
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Create a mock target in Financial Services sector
        target = CompanyMetrics(
            symbol="JPM",
            name="JPMorgan Chase",
            price=180.0,
            market_cap=500_000_000_000,
            ev_to_ebitda=None,  # Often not meaningful for banks
            price_to_book=1.5,
            currency="USD",
        )
        
        # Get valuation notes for a financial company
        notes = analyzer._get_valuation_notes(
            sector="Financial Services",
            industry="Banks—Diversified"
        )
        
        assert len(notes) >= 1, "Financial companies should have valuation notes"
        assert any("P/B" in note or "Price/Book" in note for note in notes), (
            "Financial companies should have a note recommending P/B as primary metric"
        )
        assert any("EV/EBITDA" in note or "enterprise value" in note.lower() for note in notes), (
            "Financial companies should have a note about EV/EBITDA being less meaningful"
        )
    
    def test_cyclical_company_adds_valuation_note(self):
        """
        Cyclical sector companies should get a note about mid-cycle normalization.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        notes = analyzer._get_valuation_notes(
            sector="Energy",
            industry="Oil & Gas E&P"
        )
        
        assert len(notes) >= 1, "Cyclical companies should have valuation notes"
        assert any("cycle" in note.lower() or "cyclical" in note.lower() for note in notes), (
            "Cyclical companies should have a note about cycle-adjusted multiples"
        )
    
    def test_normal_company_no_special_notes(self):
        """
        Non-financial, non-cyclical companies should have no special valuation notes.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        notes = analyzer._get_valuation_notes(
            sector="Technology",
            industry="Software—Application"
        )
        
        # Tech company should not have financial or cyclical warnings
        assert not any("P/B" in note and "financial" in note.lower() for note in notes), (
            "Tech companies should not get financial sector notes"
        )
        assert not any("cyclical" in note.lower() for note in notes), (
            "Software companies should not get cyclical notes"
        )
    
    def test_comparable_result_includes_valuation_notes(self):
        """
        ComparableResult should include valuation_notes field.
        """
        from app.services.comparable_analyzer import ComparableResult
        
        # Verify the field exists
        result = ComparableResult(
            target=None,  # type: ignore
            peers=[],
            sector="Financial Services",
            industry="Banks—Diversified",
            peer_medians={},
            implied_valuations=[],
            average_implied_price=None,
            average_upside=None,
            valuation_notes=["P/B is preferred for financial companies"],
        )
        
        assert hasattr(result, "valuation_notes"), "ComparableResult should have valuation_notes field"
        assert len(result.valuation_notes) > 0, "Financial sector should have notes"


class TestMarketCapFiltering:
    """
    P2 #9: Improve peer selection with market cap bands.
    
    Problem: Static peer lists can include vastly different-sized companies.
    Apple ($3T) shouldn't be compared to GoPro ($300M) just because both
    are "Consumer Electronics".
    
    Solution: Filter peers to those within a reasonable market cap range
    (e.g., 0.1x to 10x of target's market cap).
    """
    
    def test_filter_peers_by_market_cap_range(self):
        """
        Peers should be filtered to those within a market cap band.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        # Target: $100B market cap
        target = CompanyMetrics(
            symbol="TARGET",
            name="Target Co",
            market_cap=100_000_000_000,  # $100B
            currency="USD",
        )
        
        # Peers with various market caps
        peers = [
            CompanyMetrics(symbol="HUGE", name="Huge Corp", market_cap=500_000_000_000, currency="USD"),  # $500B - 5x, within range
            CompanyMetrics(symbol="BIG", name="Big Corp", market_cap=200_000_000_000, currency="USD"),   # $200B - 2x, within range
            CompanyMetrics(symbol="SIMILAR", name="Similar Corp", market_cap=80_000_000_000, currency="USD"),  # $80B - 0.8x, within range
            CompanyMetrics(symbol="SMALL", name="Small Corp", market_cap=5_000_000_000, currency="USD"),  # $5B - 0.05x, TOO SMALL
            CompanyMetrics(symbol="TINY", name="Tiny Corp", market_cap=500_000_000, currency="USD"),  # $500M - 0.005x, TOO SMALL
            CompanyMetrics(symbol="GIANT", name="Giant Corp", market_cap=2_000_000_000_000, currency="USD"),  # $2T - 20x, TOO BIG
        ]
        
        # Filter by market cap band (0.1x to 10x)
        filtered = analyzer._filter_peers_by_market_cap(target, peers, min_ratio=0.1, max_ratio=10.0)
        
        # Should include: HUGE (5x), BIG (2x), SIMILAR (0.8x)
        # Should exclude: SMALL (0.05x), TINY (0.005x), GIANT (20x)
        filtered_symbols = [p.symbol for p in filtered]
        
        assert "HUGE" in filtered_symbols, "HUGE (5x) should be included"
        assert "BIG" in filtered_symbols, "BIG (2x) should be included"
        assert "SIMILAR" in filtered_symbols, "SIMILAR (0.8x) should be included"
        assert "SMALL" not in filtered_symbols, "SMALL (0.05x) is too small"
        assert "TINY" not in filtered_symbols, "TINY (0.005x) is too small"
        assert "GIANT" not in filtered_symbols, "GIANT (20x) is too big"
    
    def test_no_filter_when_target_has_no_market_cap(self):
        """
        If target has no market cap, don't filter (return all peers).
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        target = CompanyMetrics(
            symbol="TARGET",
            name="Target Co",
            market_cap=None,  # No market cap data
            currency="USD",
        )
        
        peers = [
            CompanyMetrics(symbol="A", name="A", market_cap=100_000_000_000, currency="USD"),
            CompanyMetrics(symbol="B", name="B", market_cap=1_000_000_000, currency="USD"),
        ]
        
        filtered = analyzer._filter_peers_by_market_cap(target, peers)
        
        # Should return all peers unfiltered
        assert len(filtered) == 2, "Should return all peers when target has no market cap"
    
    def test_peers_without_market_cap_excluded(self):
        """
        Peers without market cap data should be excluded from filtered results.
        """
        mock_client = MagicMock()
        analyzer = ComparableAnalyzer(mock_client, provider="fmp")
        
        target = CompanyMetrics(
            symbol="TARGET",
            name="Target Co",
            market_cap=100_000_000_000,
            currency="USD",
        )
        
        peers = [
            CompanyMetrics(symbol="GOOD", name="Good", market_cap=80_000_000_000, currency="USD"),
            CompanyMetrics(symbol="NODATA", name="No Data", market_cap=None, currency="USD"),  # No market cap
        ]
        
        filtered = analyzer._filter_peers_by_market_cap(target, peers)
        
        assert len(filtered) == 1, "Should exclude peers without market cap"
        assert filtered[0].symbol == "GOOD"
    
    def test_comparable_result_includes_peer_selection_info(self):
        """
        ComparableResult should include info about peer selection/filtering.
        """
        from app.services.comparable_analyzer import ComparableResult
        
        result = ComparableResult(
            target=None,  # type: ignore
            peers=[],
            sector="Technology",
            industry="Consumer Electronics",
            peer_medians={},
            implied_valuations=[],
            average_implied_price=None,
            average_upside=None,
            peer_selection_info={
                "source": "industry",
                "total_candidates": 7,
                "after_market_cap_filter": 4,
                "market_cap_range": "0.1x - 10x of target",
            },
        )
        
        assert hasattr(result, "peer_selection_info"), "Should have peer_selection_info field"
        assert result.peer_selection_info["source"] == "industry"
        assert result.peer_selection_info["total_candidates"] == 7
        assert result.peer_selection_info["after_market_cap_filter"] == 4
