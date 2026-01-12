import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_routing_order_sections():
    """
    Regression test: Ensure /api/filings/sections reaches the correct endpoint
    and is not caught by the /{ticker} route.
    """
    # If the bug exists, this will likely return a 404 because it tries to 
    # find a ticker named 'sections' in the SEC database.
    # If fixed, it should return a 200 (assuming mock or success) or at least 
    # not a 404 from the ticker logic if we use a valid URL.
    
    # We use a dummy URL to trigger the /sections logic
    response = client.get("/api/filings/sections", params={"document_url": "https://example.com"})
    
    # If caught by /{ticker}, ticker='sections', it calls sec_filings_service.get_filings('sections')
    # which will raise a 404 because 'sections' is not a valid ticker.
    
    # If it hits /sections correctly, it might fail later due to the dummy URL, 
    # but the error code or response shape would be different.
    # In the current implementation, it tries to fetch HTML from the URL.
    
    # A clear indicator of the bug is if ticker-based logic is executed.
    # Let's check the response.
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # With the bug, it returns 404: "Ticker 'SECTIONS' not found in SEC database"
    assert response.status_code != 404 or "sections" not in response.json().get("detail", "").lower()

def test_routing_order_analyze_section():
    """Regression test: Ensure /api/filings/analyze-section is reachable."""
    response = client.post(
        "/api/filings/analyze-section", 
        params={
            "ticker": "AAPL", 
            "document_url": "https://example.com",
            "section_name": "Item 7"
        }
    )
    # If caught by /{ticker}, it's a POST to a GET route -> 405 Method Not Allowed
    assert response.status_code != 405
