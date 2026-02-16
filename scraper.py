import httpx
import time
import logging
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path
from bs4 import BeautifulSoup
from readability import Document
import html2text
import argparse
import json
from datetime import datetime


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper.log')
    ]
)
logger = logging.getLogger(__name__)


class ScraperConfig:
    """Configuration for the scraper"""
    def __init__(self, 
                 base_url: str = "https://helpcenter.pure.elsevier.com/{}",
                 headers: Optional[Dict[str, str]] = None,
                 timeout: float = 15.0,
                 delay: float = 0.5,
                 max_retries: int = 3,
                 user_agent: str = "Mozilla/5.0 (compatible; PureReleaseNotesScraper/1.0)"):
        self.base_url = base_url
        self.headers = headers or {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        self.timeout = timeout
        self.delay = delay
        self.max_retries = max_retries


class ScraperStats:
    """Statistics tracking for scraping session"""
    def __init__(self):
        self.total_pages_checked = 0
        self.successful_scrapes = 0
        self.failed_scrapes = 0
        self.not_found = 0
        self.start_time = datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        duration = (datetime.now() - self.start_time).total_seconds()
        return {
            'total_pages_checked': self.total_pages_checked,
            'successful_scrapes': self.successful_scrapes,
            'failed_scrapes': self.failed_scrapes,
            'not_found': self.not_found,
            'duration_seconds': duration,
            'success_rate': self.successful_scrapes / self.total_pages_checked if self.total_pages_checked > 0 else 0
        }


class ScrapeResult:
    """Result of a single page scrape"""
    def __init__(self, page_id: int, url: str, success: bool, 
                 title: Optional[str] = None, 
                 content: Optional[str] = None, 
                 error: Optional[str] = None):
        self.page_id = page_id
        self.url = url
        self.success = success
        self.title = title
        self.content = content
        self.error = error
        self.timestamp = datetime.now()


# ----------------------------
# Fetching with Retry Logic
# ----------------------------

def fetch_with_retry(client: httpx.Client, url: str, max_retries: int = 3) -> Optional[str]:
    """Fetch URL with retry logic and better error handling"""
    for attempt in range(max_retries):
        try:
            response = client.get(url)
            
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                logger.debug(f"Page not found (404): {url}")
                return None
            elif response.status_code == 429:
                logger.warning(f"Rate limited (429), attempt {attempt + 1}/{max_retries}: {url}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # exponential backoff
                    continue
            elif response.status_code >= 500:
                logger.warning(f"Server error ({response.status_code}), attempt {attempt + 1}/{max_retries}: {url}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            else:
                logger.warning(f"Unexpected status code {response.status_code}: {url}")
                return None
                
        except httpx.TimeoutException:
            logger.warning(f"Timeout error, attempt {attempt + 1}/{max_retries}: {url}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
        except httpx.NetworkError as e:
            logger.warning(f"Network error, attempt {attempt + 1}/{max_retries}: {url} - {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
        except httpx.HTTPError as e:
            logger.warning(f"HTTP error, attempt {attempt + 1}/{max_retries}: {url} - {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {str(e)}", exc_info=True)
            return None
    
    return None


# ----------------------------
# Content Extraction with Validation
# ----------------------------

def extract_main_content(html: str) -> Optional[str]:
    """Extract main content with validation"""
    try:
        doc = Document(html)
        content = doc.summary(html_partial=True)
        
        # Basic validation - content should not be too short
        if content and len(content.strip()) < 100:
            logger.warning("Extracted content appears too short, may be invalid")
            return None
            
        return content
    except Exception as e:
        logger.error(f"Error extracting main content: {str(e)}", exc_info=True)
        return None


def html_to_markdown(html: str) -> str:
    """Convert HTML to markdown with improved configuration"""
    try:
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = False
        converter.body_width = 0
        converter.ignore_emphasis = False
        converter.ignore_anchors = False
        converter.reference_links = True
        
        markdown = converter.handle(html)
        
        # Clean up excessive whitespace
        markdown = '\n'.join(line.strip() for line in markdown.split('\n') if line.strip())
        markdown = '\n\n'.join(paragraph for paragraph in markdown.split('\n\n') if paragraph)
        
        return markdown
    except Exception as e:
        logger.error(f"Error converting HTML to markdown: {str(e)}", exc_info=True)
        return f"Error converting content: {str(e)}"


def extract_title(html: str) -> str:
    """Extract title with fallback"""
    try:
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            # Clean up title
            title = ' '.join(title.split())  # Remove extra whitespace
            return title if title else "Untitled"
        
        # Try to find h1 as fallback
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True) or "Untitled"
            
        return "Untitled"
    except Exception as e:
        logger.error(f"Error extracting title: {str(e)}", exc_info=True)
        return "Untitled"


def validate_content(content: str) -> bool:
    """Validate that extracted content is meaningful"""
    if not content or len(content.strip()) < 50:
        return False
    
    # Check for common error messages
    error_indicators = [
        "404 not found",
        "page not found", 
        "access denied",
        "forbidden",
        "error occurred"
    ]
    
    content_lower = content.lower()
    return not any(indicator in content_lower for indicator in error_indicators)


# ----------------------------
# Main Scraper with Better Structure
# ----------------------------

def scrape_release_notes(
    start_id: int, 
    end_id: int, 
    output_file: str = "pure_release_notes.md",
    config: Optional[ScraperConfig] = None,
    stats: Optional[ScraperStats] = None
) -> List[ScrapeResult]:
    """
    Scrape release notes from a range of page IDs
    
    Args:
        start_id: First page ID to scrape
        end_id: Last page ID to scrape
        output_file: Output markdown file path
        config: Scraper configuration
        stats: Statistics tracker
        
    Returns:
        List of ScrapeResult objects
    """
    if config is None:
        config = ScraperConfig()
    if stats is None:
        stats = ScraperStats()
        
    results: List[ScrapeResult] = []
    sections: List[Tuple[int, str]] = []

    logger.info(f"Starting scrape from {start_id} to {end_id}")
    logger.info(f"Output will be saved to: {output_file}")

    with httpx.Client(headers=config.headers, timeout=config.timeout, http2=True, verify=False) as client:
        for page_id in range(start_id, end_id + 1):
            stats.total_pages_checked += 1
            url = config.base_url.format(page_id)
            
            logger.info(f"Processing page {page_id}: {url}")

            # Fetch with retry
            html = fetch_with_retry(client, url, config.max_retries)
            
            if not html:
                error_msg = "Page not found or failed to fetch"
                logger.warning(f"{error_msg}: {url}")
                stats.not_found += 1
                results.append(ScrapeResult(page_id, url, False, error=error_msg))
                continue

            # Extract title
            title = extract_title(html)
            logger.info(f"Found title: {title}")

            # Extract main content
            main_html = extract_main_content(html)
            if not main_html:
                error_msg = "Failed to extract meaningful content"
                logger.warning(f"{error_msg}: {url}")
                stats.failed_scrapes += 1
                results.append(ScrapeResult(page_id, url, False, title=title, error=error_msg))
                continue

            # Convert to markdown
            markdown = html_to_markdown(main_html)
            
            # Validate content
            if not validate_content(markdown):
                error_msg = "Extracted content failed validation"
                logger.warning(f"{error_msg}: {url}")
                stats.failed_scrapes += 1
                results.append(ScrapeResult(page_id, url, False, title=title, error=error_msg))
                continue

            # Success!
            stats.successful_scrapes += 1
            logger.info(f"Successfully scraped: {url}")

            section = (
                f"# {title}\n\n"
                f"*Source: [{url}]({url})*\n\n"
                f"*Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
                f"---\n\n"
                f"{markdown}\n\n"
                f"---\n\n"
            )

            sections.append((page_id, section))
            results.append(ScrapeResult(page_id, url, True, title=title, content=markdown))

            # Polite delay
            time.sleep(config.delay)

    # Sort by page ID
    sections.sort(key=lambda x: x[0])

    # Write output
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Release Notes Archive\n\n")
            f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write(f"*Pages scraped: {start_id} to {end_id}*\n\n")
            f.write("---\n\n")
            f.write("\n".join(section for _, section in sections))
        
        logger.info(f"Successfully saved to {output_file}")
        
        # Save stats
        stats_dict = stats.to_dict()
        with open('scraper_stats.json', 'w') as f:
            json.dump(stats_dict, f, indent=2)
        
        logger.info(f"Statistics: {stats_dict}")
        
    except Exception as e:
        logger.error(f"Failed to write output file: {str(e)}", exc_info=True)
        
    return results


# ----------------------------
# Command Line Interface
# ----------------------------

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Pure Release Notes Scraper - Scrape release notes from Pure help center"
    )
    
    parser.add_argument(
        "--start", 
        type=int, 
        default=5290,
        help="Starting page ID (default: 5290)"
    )
    
    parser.add_argument(
        "--end", 
        type=int, 
        default=5350,
        help="Ending page ID (default: 5350)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="pure_release_notes.md",
        help="Output file path (default: pure_release_notes.md)"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds (default: 0.5)"
    )
    
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Request timeout in seconds (default: 15.0)"
    )
    
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Maximum retries for failed requests (default: 3)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


# ----------------------------
# Entry Point
# ----------------------------

if __name__ == "__main__":
    args = parse_arguments()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('httpx').setLevel(logging.DEBUG)
    
    config = ScraperConfig(
        delay=args.delay,
        timeout=args.timeout,
        max_retries=args.retries
    )
    
    stats = ScraperStats()
    
    try:
        results = scrape_release_notes(
            start_id=args.start,
            end_id=args.end,
            output_file=args.output,
            config=config,
            stats=stats
        )
        
        logger.info(f"Scraping completed. Success rate: {stats.successful_scrapes}/{stats.total_pages_checked}")
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error during scraping: {str(e)}", exc_info=True)
        exit(1)