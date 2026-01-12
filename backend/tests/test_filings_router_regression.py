import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_filings_router_bugfixes():
    """
    Regression test for:
    1. Duplicate @router.get("/{ticker}") decorator.
    2. Missing Query() for ticker in analyze-section.
    3. Missing Query() for ticker in compare-sections.
    """
    # 1. Duplicate decorator check: 
    # If the duplicate existed, the route would still function, 
    # but cleaning it up ensures code quality. 
    # We just verify the route works.
    # Note: We need a ticker that might exist or mock the service.
    # For a pure routing test, we can just check if it returns 404 vs 405/500.
    response = test_response = client.get("/api/filings/INVALID_TICKER_FOR_TEST")
    # Should be 404 if route exists but ticker not found
    assert response.status_code == 404
    
    # 2. analyze-section ticker as Query param
    # If ticker was missing Query(), FastAPI would expect it in Body.
    # Sending it as Query should now work (or at least get past validation).
    response = client.post(
        "/api/filings/analyze-section",
        params={
            "ticker": "AAPL",
            "document_url": "https://example.com/filing.htm",
            "section_name": "Item 7"
        }
    )
    # Since we aren't mocking the LLM/SEC calls here, we expect 500 or 404, 
    # but NOT 422 Unprocessable Entity (which is what a validation error would be).
    assert response.status_code != 422
    
    # 3. compare-sections ticker as Query param
    response = client.post(
        "/api/filings/compare-sections",
        params={
            "ticker": "AAPL",
            "current_url": "https://example.com/now.htm",
            "previous_url": "https://example.com/then.htm",
            "section_name": "Item 7"
        }
    )
    assert response.status_code != 422
