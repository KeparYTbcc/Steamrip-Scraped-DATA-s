import os
import json
import re
import difflib
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from bin import gamelistparser, gamedataextractor
import tkinter as tk
from tkinter import filedialog

DATA_DIR = os.path.join("data", "clones")
os.makedirs(DATA_DIR, exist_ok=True)

MAX_WORKERS = 10  # Number of concurrent threads

# Regex for cleaning titles
TITLE_CLEAN_RE = re.compile(r"\b(?:Direct|Download|Free|Link|Game)\b", re.IGNORECASE)
MULTISPACE_RE = re.compile(r"\s+")


def slugify(text: str) -> str:
    """Convert text into a safe filename slug."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "game"


def clean_title(title: str) -> str:
    """Clean unwanted words and extra spaces from title."""
    if not title:
        return ""
    title = TITLE_CLEAN_RE.sub("", title)
    title = MULTISPACE_RE.sub(" ", title)
    return title.strip()


def scrape_and_save(title: str, page_url: str, filepath: str):
    """
    Scrape game data from page_url and save it to filepath.
    If page_url is found exactly in download_links, delete the file and skip saving.
    Returns (title, success_bool, message).
    """
    try:
        data = gamedataextractor.scrape_game_data(page_url)
        download_links = data.get("download_links", [])
        if not download_links:
            raise ValueError("No download_links found in scraped data")

        if page_url in download_links:
            if os.path.exists(filepath):
                os.remove(filepath)
            return title, False, f"[SKIPPED] Removed '{title}' because page_url is in download_links"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return title, True, f"[SUCCESS] Saved data for '{title}'"
    except Exception as e:
        return title, False, f"[ERROR] Failed scraping/saving '{title}': {e}"


FAILED_GAMES_PATH = os.path.join(DATA_DIR, "failed_games.json")


class SteamRipScraper:
    def __init__(self):
        self.failed_games = []
        self.load_failed()

    def add_failed_game(self, title: str, url: str) -> bool:
        """Add a failed game entry if not already present."""
        clean_t = clean_title(title)
        exists = any(clean_title(fg["title"]) == clean_t and fg.get("url") == url for fg in self.failed_games)
        if not exists:
            self.failed_games.append({"title": title, "url": url})
            return True
        return False

    def save_failed(self):
        try:
            with open(FAILED_GAMES_PATH, "w", encoding="utf-8") as f:
                json.dump(self.failed_games, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] Could not save failed games file: {e}")

    def load_failed(self):
        if os.path.exists(FAILED_GAMES_PATH):
            try:
                with open(FAILED_GAMES_PATH, "r", encoding="utf-8") as f:
                    self.failed_games = json.load(f)
                print(f"[INFO] Loaded {len(self.failed_games)} failed game(s) from previous session.")
            except Exception as e:
                print(f"[ERROR] Could not load failed games file: {e}")
                self.failed_games = []
        else:
            self.failed_games = []

    def update_database(self, use_multithread=True):
        print("\n[INFO] Starting scraping process...")

        all_game_urls = gamelistparser.fetch_games_list()
        if not all_game_urls:
            print("[WARNING] No games found on listing page.")
            return

        file_map = {}
        for game in all_game_urls:
            title = game["title"]
            filename = slugify(title) + ".json"
            filepath = os.path.join(DATA_DIR, filename)
            file_map[title] = filepath
            if not os.path.exists(filepath):
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write("{}")
                except Exception as e:
                    print(f"[ERROR] Failed creating placeholder for {title}: {e}")

        self.failed_games.clear()
        success_count = 0

        if use_multithread:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {
                    executor.submit(scrape_and_save, game["title"], game["url"], file_map[game["title"]]): game["title"]
                    for game in all_game_urls
                }

                for idx, future in enumerate(as_completed(futures), 1):
                    title, success, message = future.result()
                    print(f"[{idx}/{len(all_game_urls)}] {message}")
                    if not success:
                        failed_url = next((g["url"] for g in all_game_urls if g["title"] == title), None)
                        if failed_url:
                            self.add_failed_game(title, failed_url)
                    else:
                        success_count += 1
        else:
            for idx, game in enumerate(all_game_urls, 1):
                title = game["title"]
                url = game["url"]
                filepath = file_map[title]
                print(f"[{idx}/{len(all_game_urls)}] Scraping '{title}' from {url}")
                try:
                    data = gamedataextractor.scrape_game_data(url)
                    if not data.get("download_links"):
                        raise ValueError("No download_links found in scraped data")
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                    print(f"[SUCCESS] Saved data to {filepath}")
                    success_count += 1
                except Exception as e:
                    print(f"[ERROR] Failed scraping/saving {title}: {e}")
                    self.add_failed_game(title, url)

        self.save_failed()
        print(f"\n[INFO] Scraping finished. Successes: {success_count}, Failures: {len(self.failed_games)}")

    def retry_failed(self):
        if not self.failed_games:
            print("[INFO] No failed games to retry.")
            return

        print(f"[INFO] Retrying {len(self.failed_games)} failed game(s) sequentially...")

        still_failed = []
        file_map = {}
        for game in self.failed_games:
            title = game["title"]
            filename = slugify(title) + ".json"
            filepath = os.path.join(DATA_DIR, filename)
            file_map[title] = filepath
            if not os.path.exists(filepath):
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write("{}")
                except Exception as e:
                    print(f"[ERROR] Failed creating placeholder for {title}: {e}")

        for idx, game in enumerate(self.failed_games, 1):
            title = game["title"]
            url = game["url"]
            filepath = file_map[title]
            print(f"[Retry {idx}/{len(self.failed_games)}] Scraping '{title}' from {url}")
            try:
                data = gamedataextractor.scrape_game_data(url)
                if not data.get("download_links"):
                    raise ValueError("No download_links found in scraped data")
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                print(f"[SUCCESS] Saved data to {filepath}")
            except Exception as e:
                print(f"[ERROR] Failed scraping/saving {title}: {e}")
                still_failed.append({"title": title, "url": url})

        self.failed_games = still_failed
        self.save_failed()
        print(f"\n[INFO] Retry finished. Still failed: {len(self.failed_games)}")

    def quickcheck(self):
        print("\n[INFO] Starting quickcheck of all database files...")
        suspect_files = []
        for file in os.listdir(DATA_DIR):
            if not file.endswith(".json") or file == "failed_games.json":
                continue
            path = os.path.join(DATA_DIR, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                title = data.get("title")
                downloads = data.get("download_links", [])
                if not title or not downloads:
                    suspect_files.append((file, title, downloads))
            except Exception as e:
                print(f"[ERROR] Failed reading {path}: {e}")

        if not suspect_files:
            print("[INFO] No suspicious or incomplete files found.")
            return

        print(f"\n[INFO] Found {len(suspect_files)} suspicious/incomplete file(s):")
        for idx, (filename, title, downloads) in enumerate(suspect_files, 1):
            print(f"{idx}. File: {filename}, Title: {title}, Download links: {len(downloads)}")

        confirm = input("Mark these as failed for retry? (y/n): ").strip().lower()
        if confirm != "y":
            print("[INFO] Quickcheck cancelled.")
            return

        print("[INFO] Fetching latest game list to recover missing URLs...")
        all_game_urls = gamelistparser.fetch_games_list()

        cleaned_title_to_url = {}
        slug_to_title = {}
        for game in all_game_urls:
            clean_t = clean_title(game["title"])
            cleaned_title_to_url[clean_t] = game["url"]
            slug_to_title[slugify(game["title"])] = game["title"]

        new_failed_count = 0
        for file, title, _ in suspect_files:
            if not title:
                filename_slug = os.path.splitext(file)[0]
                inferred_title = slug_to_title.get(filename_slug)
                if not inferred_title:
                    close_matches = difflib.get_close_matches(filename_slug, slug_to_title.keys(), n=1, cutoff=0.6)
                    if close_matches:
                        inferred_title = slug_to_title[close_matches[0]]

                if not inferred_title:
                    print(f"[WARNING] Missing title in {file}, skipping adding to failed.")
                    continue

                title = inferred_title

            url = None
            file_path = os.path.join(DATA_DIR, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                url = data.get("page_url")
            except Exception as e:
                print(f"[ERROR] Could not read page_url from {file}: {e}")

            if not url:
                clean_t = clean_title(title)
                for g in self.failed_games:
                    if clean_title(g["title"]) == clean_t:
                        url = g.get("url")
                        break

            if not url:
                clean_t = clean_title(title)
                url = cleaned_title_to_url.get(clean_t)

            if not url:
                print(f"[WARNING] URL not found for '{title}', skipping adding to failed.")
                continue

            if self.add_failed_game(title, url):
                new_failed_count += 1

        self.save_failed()
        print(f"[INFO] Updated failed games list with {new_failed_count} entries.")

    def search_games(self, query: str):
        results = []
        for file in os.listdir(DATA_DIR):
            if not file.endswith(".json") or file == "failed_games.json":
                continue
            path = os.path.join(DATA_DIR, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                title = data.get("title", "")
                if query.lower() in title.lower():
                    results.append(data)
            except Exception:
                continue
        return results

    def clean_database(self):
        print("[INFO] Cleaning database...")
        count = 0
        for file in os.listdir(DATA_DIR):
            if file.endswith(".json"):
                try:
                    os.remove(os.path.join(DATA_DIR, file))
                    count += 1
                except Exception as e:
                    print(f"[ERROR] Failed to delete {file}: {e}")
        print(f"[INFO] Deleted {count} files.")

    def check_for_updates(self):
        print("\n[INFO] Checking for updated or new game versions...")
        all_game_urls = gamelistparser.fetch_games_list()
        if not all_game_urls:
            print("[WARNING] No games found on listing page.")
            return

        local_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json") and f != "failed_games.json"]
        local_slugs = set(os.path.splitext(f)[0] for f in local_files)

        updates_count = 0
        for game in all_game_urls:
            title = game["title"]
            slug = slugify(title)
            if slug not in local_slugs:
                print(f"[UPDATE] Detected new or updated version: '{title}' (slug: {slug})")
                filepath = os.path.join(DATA_DIR, slug + ".json")
                try:
                    data = gamedataextractor.scrape_game_data(game["url"])
                    if not data.get("download_links"):
                        raise ValueError("No download_links found in scraped data")
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                    print(f"[SUCCESS] Updated '{title}' saved.")
                    updates_count += 1
                except Exception as e:
                    print(f"[ERROR] Failed updating '{title}': {e}")
                    self.add_failed_game(title, game["url"])

        if updates_count == 0:
            print("[INFO] No new or updated game versions found.")
        else:
            print(f"[INFO] Finished updating {updates_count} game(s).")
        self.save_failed()


def download_file(url: str, output_path: str) -> bool:
    """Download a file with progress bar and better error handling."""
    
    def attempt_download(download_url: str, attempt_num: int) -> bool:
        """Attempt to download from a specific URL"""
        try:
            print(f"[INFO] Attempt {attempt_num}: Starting download from: {download_url}")
            print(f"[INFO] Saving to: {output_path}")
            
            # Set up headers to mimic a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            session = requests.Session()
            session.headers.update(headers)
            
            # For first attempt, follow redirects to get final URL
            if attempt_num == 1:
                print("[INFO] Following redirects to get final download URL...")
                response = session.head(download_url, allow_redirects=True, timeout=30)
                final_url = response.url
                print(f"[INFO] Final URL after redirects: {final_url}")
                download_url = final_url
            
            # Now download the file
            with session.get(download_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                
                # Check content type to ensure it's actually a file
                content_type = r.headers.get('content-type', '').lower()
                if 'text/html' in content_type:
                    print(f"[WARNING] Response appears to be HTML, not a file download")
                    print(f"[INFO] Content-Type: {content_type}")
                    
                    # Read a small amount to check if it's an error page
                    content_preview = r.content[:1000].decode('utf-8', errors='ignore')
                    error_indicators = ['error', 'not found', '404', 'forbidden', 'unauthorized', 
                                      '<html', '<!doctype', 'gofile.io', 'page not found']
                    if any(indicator in content_preview.lower() for indicator in error_indicators):
                        print("[ERROR] Download URL returned an error page")
                        print(f"[DEBUG] Content preview: {content_preview[:200]}...")
                        return False
                    
                    # Even if it doesn't contain obvious errors, HTML is not a valid download
                    print("[ERROR] Response is HTML, not a downloadable file")
                    return False
                
                total_length = r.headers.get('content-length')
                total_length = int(total_length) if total_length is not None else None

                with open(output_path, "wb") as f:
                    if total_length is None:
                        print("[INFO] Content length unknown, downloading without progress bar...")
                        f.write(r.content)
                        print(f"[DOWNLOAD] Completed: {output_path}")
                    else:
                        downloaded = 0
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                done = int(50 * downloaded / total_length)
                                print(f"\r[DOWNLOAD] [{'=' * done}{' ' * (50 - done)}] "
                                      f"{downloaded / 1024 / 1024:.2f}MB/{total_length / 1024 / 1024:.2f}MB", end="")
                        print(f"\n[DOWNLOAD] Completed: {output_path}")
            
            # Verify file was downloaded and has reasonable size
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"[INFO] File size: {file_size / 1024 / 1024:.2f} MB")
                
                            # Check if file is too small (likely an error page)
            # Game files should be much larger than a few KB
            if file_size < 1024 * 100:  # Less than 100KB
                print(f"[WARNING] Downloaded file is very small ({file_size} bytes), may be an error page")
                print("[INFO] Checking file content...")
                
                try:
                    with open(output_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(2000)  # Read more content to be sure
                        # Check for common error indicators
                        error_indicators = ['error', 'not found', '404', 'forbidden', 'unauthorized', 
                                          '<html', '<!doctype', 'gofile.io', 'page not found']
                        if any(indicator in content.lower() for indicator in error_indicators):
                            print("[ERROR] File contains error message or HTML, download failed")
                            print(f"[DEBUG] Content preview: {content[:200]}...")
                            os.remove(output_path)
                            return False
                except Exception as e:
                    print(f"[DEBUG] Error reading file content: {e}")
                    # If we can't read it as text, it might be a binary file
                    # But if it's too small, it's still suspicious
                    if file_size < 1024 * 10:  # Less than 10KB
                        print("[ERROR] File is too small to be a valid game file")
                        os.remove(output_path)
                        return False
                
                return True
            else:
                print("[ERROR] File was not created")
                return False
                
        except requests.exceptions.Timeout:
            print(f"\n[ERROR] Download timed out")
            return False
        except requests.exceptions.RequestException as e:
            print(f"\n[ERROR] Network error during download: {e}")
            return False
        except Exception as e:
            print(f"\n[ERROR] Download failed: {e}")
            return False
    
    # First attempt: follow redirects
    if attempt_download(url, 1):
        return True
    
    # Second attempt: try the original direct URL without following redirects
    print("[INFO] First attempt failed, trying original direct URL...")
    if os.path.exists(output_path):
        os.remove(output_path)  # Remove the failed download
    
    return attempt_download(url, 2)


def get_direct_download_url(page_url: str):
    """
    Import and use getgamedownloadurl.py as a module to extract direct download URL.
    Returns the direct download URL string if successful, else None.
    """
    try:
        print(f"[INFO] Extracting direct download URL for: {page_url}")
        print("[INFO] Browser will open in visible mode - you may need to interact with it")
        
        # Import the module directly
        from bin.getgamedownloadurl import get_direct_download_url as extract_url
        
        # Call the function directly
        direct_url = extract_url(page_url)
        
        if direct_url:
            print(f"[SUCCESS] Retrieved direct download URL: {direct_url}")
            return direct_url
        else:
            print("[ERROR] No direct download URL was extracted.")
            return None

    except ImportError as e:
        print(f"[ERROR] Failed to import getgamedownloadurl module: {e}")
        print("[INFO] Make sure the script exists in bin/ directory")
        return None
    except Exception as e:
        print(f"[ERROR] Exception while extracting download URL: {e}")
        return None


def prompt_download(scraper: SteamRipScraper):
    query = input("\nEnter game title or part of it to download: ").strip()
    if not query:
        print("[WARNING] Title cannot be empty.")
        return

    matches = scraper.search_games(query)
    if not matches:
        print("[INFO] No matching games found.")
        return

    print(f"\nFound {len(matches)} match(es):")
    for idx, game in enumerate(matches, 1):
        print(f"{idx}. {game.get('title','N/A')}")

    try:
        choice = int(input(f"Select a game to download (1-{len(matches)}): ").strip())
        if not (1 <= choice <= len(matches)):
            print("[WARNING] Invalid choice.")
            return
    except ValueError:
        print("[WARNING] Invalid input.")
        return

    game = matches[choice - 1]
    download_links = game.get("download_links", [])
    if not download_links:
        print("[INFO] No download links found for this game.")
        return

    print("\nAvailable download links:")
    for i, link in enumerate(download_links, 1):
        print(f"{i}. {link}")

    try:
        link_choice = int(input(f"Select a download link (1-{len(download_links)}): ").strip())
        if not (1 <= link_choice <= len(download_links)):
            print("[WARNING] Invalid choice.")
            return
    except ValueError:
        print("[WARNING] Invalid input.")
        return

    page_url = download_links[link_choice - 1]

    print(f"[INFO] Retrieving direct download URL for: {page_url}")
    
    # Check if it's a pixeldrain URL that can be converted directly
    if 'pixeldrain.com' in page_url and '/u/' in page_url:
        print("[INFO] Detected pixeldrain URL - converting directly without browser...")
    else:
        print("[INFO] Browser will open to extract download URL...")
        print("[INFO] IMPORTANT: You will have 10 seconds to interact with the page!")
        print("[INFO] Look for download buttons, wait for countdowns, or solve any captchas.")
    
    direct_url = get_direct_download_url(page_url)
    if not direct_url:
        print("[ERROR] Could not retrieve direct download URL.")
        print("[INFO] This might be due to Cloudflare protection or complex captchas.")
        print("[INFO] Please ensure you solve any captchas manually in the browser.")
        return
    
    print("[INFO] Download URL extracted successfully!")
    
    # Only show browser-related messages if browser was actually used
    if 'pixeldrain.com' not in page_url or '/u/' not in page_url:
        print("[INFO] Browser will close and folder selection dialog will appear...")
        # Small delay to ensure browser has closed
        import time
        time.sleep(1)
    else:
        print("[INFO] Folder selection dialog will appear...")

    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)  # Make sure dialog appears on top
        root.update()  # Force update to ensure window is ready
        print("[INFO] Please select the folder to save the downloaded file.")
        output_folder = filedialog.askdirectory(parent=root, title="Select Download Folder")
        root.destroy()
        
        if not output_folder:
            print("[WARNING] No folder selected. Using current directory as fallback...")
            output_folder = os.getcwd()
            
    except Exception as e:
        print(f"[ERROR] Failed to open folder dialog: {e}")
        print("[INFO] Using current directory as fallback...")
        output_folder = os.getcwd()

    if not output_folder:
        print("[WARNING] No folder selected. Download cancelled.")
        return
    
    print(f"[INFO] Selected download folder: {output_folder}")

    # Extract filename from URL, handling various URL formats
    filename = direct_url.split("/")[-1].split("?")[0]
    if not filename or "." not in filename:
        # Fallback: use game title as filename
        filename = f"{game.get('title', 'game')}.zip"
    
    # Clean filename of invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    output_path = os.path.join(output_folder, filename)

    print(f"[INFO] Starting download from direct URL: {direct_url}")
    success = download_file(direct_url, output_path)
    
    if not success:
        print("[WARNING] Direct download failed. This might be due to:")
        print("  - Anti-bot protection on the download server")
        print("  - URL expiration or rate limiting")
        print("  - Network issues")
        print("[INFO] You may need to manually download the file from the browser")
        print(f"[INFO] Original download page: {page_url}")


def main():
    scraper = SteamRipScraper()

    if not any(fname.endswith(".json") for fname in os.listdir(DATA_DIR)):
        print("[INFO] Database empty. Scraping now...")
        scraper.update_database()

    while True:
        print("\n==== SteamRip External Downloader ====")
        print("1. Search games in local database")
        print("2. Refresh database (scrape again, multithreaded)")
        print("3. Clean database (delete all files)")
        print("4. Retry failed scrapes sequentially")
        print("5. Quickcheck database for issues")
        print("6. Exit")
        print("7. Check for updated/new versions")
        print("8. Download game files")
        choice = input("Choose an option (1-8): ").strip()

        if choice == "1":
            query = input("\nEnter search term: ").strip()
            if not query:
                print("[WARNING] Search term cannot be empty.")
                continue
            matches = scraper.search_games(query)
            if matches:
                print(f"\n[INFO] Found {len(matches)} result(s):")
                for idx, game in enumerate(matches, 1):
                    print(f"\n{idx}. {game['title']}")
                    if game.get("download_links"):
                        print("   Download links:")
                        for link in game["download_links"]:
                            print(f"    - {link}")
            else:
                print("[INFO] No results found.")

        elif choice == "2":
            confirm = input("This will overwrite existing files. Continue? (y/n): ").strip().lower()
            if confirm == "y":
                scraper.update_database(use_multithread=True)
            else:
                print("[INFO] Refresh cancelled.")

        elif choice == "3":
            confirm = input("Are you sure you want to delete ALL database files? (y/n): ").strip().lower()
            if confirm == "y":
                scraper.clean_database()
            else:
                print("[INFO] Clean cancelled.")

        elif choice == "4":
            scraper.retry_failed()

        elif choice == "5":
            scraper.quickcheck()

        elif choice == "6":
            print("[INFO] Exiting...")
            break

        elif choice == "7":
            scraper.check_for_updates()

        elif choice == "8":
            prompt_download(scraper)

        else:
            print("[ERROR] Invalid option. Please choose 1-8.")


if __name__ == "__main__":
    main()
