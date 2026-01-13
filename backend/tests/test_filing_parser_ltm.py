import pytest
from app.services.filing_parser import FilingParser

def test_extract_ixbrl_facts_with_durations():
    parser = FilingParser()
    
    # Mock HTML with iXBRL nonFraction tags and contexts
    html = """
    <html>
        <ix:nonFraction name="us-gaap:Revenues" contextRef="c1" unitRef="u1" decimals="-6" scale="6">900</ix:nonFraction>
        <ix:nonFraction name="us-gaap:Assets" contextRef="c2" unitRef="u1" decimals="-6" scale="6">1000</ix:nonFraction>
        
        <xbrli:context id="c1">
            <xbrli:period>
                <xbrli:startDate>2025-01-01</xbrli:startDate>
                <xbrli:endDate>2025-09-30</xbrli:endDate>
            </xbrli:period>
        </xbrli:context>
        
        <xbrli:context id="c2">
            <xbrli:period>
                <xbrli:instant>2025-09-30</xbrli:instant>
            </xbrli:period>
        </xbrli:context>
    </html>
    """
    
    facts = parser.extract_ixbrl_facts(html)
    
    # We expect 2 periods
    assert len(facts) == 2
    
    # Period 1: Flow (Revenue)
    flow_period = next(f for f in facts if f["duration"] > 0)
    assert flow_period["date"] == "2025-09-30"
    assert flow_period["revenue"] == 900000000.0 # 900 * 10^6
    assert 270 <= flow_period["duration"] <= 275 # ~9 months
    
    # Period 2: Instant (Assets)
    instant_period = next(f for f in facts if f["duration"] == 0)
    assert instant_period["date"] == "2025-09-30"
    assert instant_period["total_assets"] == 1000000000.0
