import re
import json
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://steamrip.com"

# Precompile regex to remove unwanted words and extra spaces
TITLE_CLEAN_RE = re.compile(r"\b(?:Direct|Download|Free|Link|Game)\b", re.IGNORECASE)
MULTISPACE_RE = re.compile(r"\s+")

# Create a session for faster repeated requests
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
})

def fetch_games_list(page_url=f"{BASE_URL}/games-list-page/"):
    """Fetch and clean the SteamRip games list quickly."""
    response = session.get(page_url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.find(class_="az-link-posts-block")
    if not container:
        print("[WARNING] Container with class 'az-link-posts-block' not found.")
        return []

    results = []
    for a in container.select("a[href]"):
        href = a["href"]
        if href.startswith("/"):
            href = BASE_URL + href

        # Clean title: remove unwanted words, trim, and normalize spaces
        title = TITLE_CLEAN_RE.sub("", a.get_text(strip=True))
        title = MULTISPACE_RE.sub(" ", title).strip()

        results.append({"title": title, "url": href})

    return results

if __name__ == "__main__":
    games = fetch_games_list()
    print(json.dumps(games, indent=4, ensure_ascii=False))
