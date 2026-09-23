"""Optional scraper stub for myScheme.gov.in. MVP uses data/schemes_seed.json."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "schemes_seed.json"


def scrape_myscheme(limit: int = 50) -> list[dict]:
    # Placeholder: myScheme has no stable public API; keep seed data as source of truth.
    # Future: use requests + BeautifulSoup on https://www.myscheme.gov.in/search
    print("Scraper stub: using existing seed data.")
    with open(OUT, encoding="utf-8") as f:
        return json.load(f)[:limit]


if __name__ == "__main__":
    print(f"{len(scrape_myscheme())} schemes available.")
