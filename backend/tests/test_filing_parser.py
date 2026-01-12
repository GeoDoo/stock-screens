import pytest
from app.services.filing_parser import FilingParser

def test_extract_sections_basic():
    """Test extracting standard 10-K sections from a dummy HTML."""
    html = """
    <html>
        <body>
            <div id="item1">ITEM 1. BUSINESS</div>
            <p>Our business is great.</p>
            <div id="item1a">ITEM 1A. RISK FACTORS</div>
            <p>Our business is risky.</p>
            <div id="item7">ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS</div>
            <p>We discussed and analyzed.</p>
            <div id="item8">ITEM 8. FINANCIAL STATEMENTS</div>
            <p>Numbers go here.</p>
        </body>
    </html>
    """
    
    parser = FilingParser()
    sections = parser.extract_sections(html)
    
    assert "item1" in sections or "Item 1" in sections
    assert "item1a" in sections or "Item 1A" in sections
    assert "item7" in sections or "Item 7" in sections
    
    # Check content
    content_7 = parser.get_section(html, "Item 7")
    assert "discussed and analyzed" in content_7

def test_clean_html_to_text():
    """Ensures parser removes HTML tags and extra whitespace."""
    html = "<div>  Hello   <p>World</p>  </div>"
    parser = FilingParser()
    text = parser.clean_html(html)
    assert text == "Hello World"

def test_extract_ixbrl_facts_basic():
    """Test extracting numerical facts from dummy iXBRL tags."""
    html = """
    <html>
        <body>
            <ix:nonFraction name="us-gaap:NetIncomeLoss" scale="6" unitRef="usd" contextRef="c1">1,234.5</ix:nonFraction>
            <ix:nonFraction name="us-gaap:Revenues" scale="6" unitRef="usd" contextRef="c1">10,000</ix:nonFraction>
            <ix:nonFraction name="us-gaap:Assets" scale="6" unitRef="usd" contextRef="c1">50,000</ix:nonFraction>
            <ix:nonFraction name="us-gaap:Liabilities" scale="6" unitRef="usd" contextRef="c1">20,000</ix:nonFraction>
        </body>
    </html>
    """
    parser = FilingParser()
    facts = parser.extract_ixbrl_facts(html)
    
    assert facts["net_income"] == 1234500000.0
    assert facts["revenue"] == 10000000000.0
    assert facts["total_assets"] == 50000000000.0
    assert facts["total_liabilities"] == 20000000000.0

def test_extract_ixbrl_facts_negative_and_sign():
    """Test handling of negative numbers in iXBRL."""
    html = """
    <html>
        <body>
            <ix:nonFraction name="us-gaap:NetIncomeLoss" scale="3" sign="-" unitRef="usd">(500)</ix:nonFraction>
        </body>
    </html>
    """
    parser = FilingParser()
    facts = parser.extract_ixbrl_facts(html)
    assert facts["net_income"] == -500000.0
