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
