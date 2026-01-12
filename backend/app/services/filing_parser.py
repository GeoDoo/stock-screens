import re
import bs4
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from app.services.logging_config import logger

class FilingParser:
    """
    Parses SEC HTML filings to extract specific sections (Items).
    Uses a combination of BeautifulSoup and robust regex to handle
    the variability in EDGAR HTML documents.
    """
    
    # Standard 10-K sections of interest
    SECTIONS = {
        "Item 1": r"ITEM\s+1\.\s+BUSINESS",
        "Item 1A": r"ITEM\s+1A\.\s+RISK\s+FACTORS",
        "Item 3": r"ITEM\s+3\.\s+LEGAL\s+PROCEEDINGS",
        "Item 7": r"ITEM\s+7\.\s+MANAGEMENT(?:\'S|\u2019S)\s+DISCUSSION\s+AND\s+ANALYSIS",
        "Item 7A": r"ITEM\s+7A\.\s+QUANTITATIVE\s+AND\s+QUALITATIVE\s+DISCLOSURES\s+ABOUT\s+MARKET\s+RISK",
        "Item 8": r"ITEM\s+8\.\s+FINANCIAL\s+STATEMENTS",
        "Item 9A": r"ITEM\s+9A\.\s+CONTROLS\s+AND\s+PROCEDURES",
    }

    def clean_html(self, html: str) -> str:
        """Removes HTML tags and normalizes whitespace."""
        if not html:
            return ""
        
        soup = BeautifulSoup(html, "lxml")
        
        # Remove script and style elements
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
            
        # Get text
        text = soup.get_text(separator=" ")
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def extract_sections(self, html: str) -> Dict[str, str]:
        """
        Extracts major 10-K items as raw HTML chunks.
        Note: This returns the HTML for each section so we can do 
        further processing if needed.
        """
        sections = {}
        
        # Use a more efficient approach for large filings: 
        # identify indices of section headers and split.
        
        # We search for the pattern in the text to find where they start
        text = self.clean_html(html)
        
        positions = []
        for name, pattern in self.SECTIONS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                positions.append((match.start(), name))
        
        # Sort by position in document
        positions.sort()
        
        for i in range(len(positions)):
            start_pos, name = positions[i]
            end_pos = positions[i+1][0] if i + 1 < len(positions) else len(text)
            
            sections[name] = text[start_pos:end_pos].strip()
            
        return sections

    def get_section(self, html: str, section_name: str) -> Optional[str]:
        """Convenience method to get a single section's text."""
        sections = self.extract_sections(html)
        return sections.get(section_name)
