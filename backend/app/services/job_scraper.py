import re

import httpx
from bs4 import BeautifulSoup

from app.models.errors import APIError, ErrorCode
from app.utils.logging import get_logger

logger = get_logger(__name__)

_TIMEOUT = 20.0
_MAX_CHARS = 12_000

# Domains known to block scrapers
_BLOCKED_DOMAINS = {"linkedin.com", "www.linkedin.com"}


async def scrape_jd(url: str) -> str:
    """Fetch a job description URL and return the visible text content.

    Raises APIError(SCRAPE_BLOCKED) for known anti-scraper sites.
    Raises APIError(SCRAPE_FAILED) on network errors or empty content.
    """
    from urllib.parse import urlparse

    domain = urlparse(url).netloc.lower()
    if domain in _BLOCKED_DOMAINS:
        raise APIError(
            ErrorCode.SCRAPE_BLOCKED,
            "LinkedIn blocks automated access. Please paste the job description text directly.",
            retry_possible=False,
        )

    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ResumeTailor/1.0)"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise APIError(
            ErrorCode.SCRAPE_FAILED,
            f"Job posting returned HTTP {exc.response.status_code}. Check the URL.",
            retry_possible=False,
        ) from exc
    except httpx.RequestError as exc:
        raise APIError(
            ErrorCode.SCRAPE_FAILED,
            "Could not reach the job posting URL. Check your connection and the URL.",
            retry_possible=True,
        ) from exc

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove navigation, header, footer, scripts, styles
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    text = re.sub(r"[ \t]+", " ", text)

    if len(text) < 100:
        raise APIError(
            ErrorCode.SCRAPE_FAILED,
            "Job posting page appears empty or uses JavaScript rendering. Paste the text directly.",
            retry_possible=False,
        )

    logger.info(f"Scraped JD url={url!r} chars={len(text)}")
    return text[:_MAX_CHARS]
