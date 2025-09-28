import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import traceback  # <-- import traceback module

BASE_URL = "https://steamrip.com/zoochosis-free-download/"

def get_real_image_url(img_tag, base_url):
    # (same as your original code)
    src = img_tag.get("src", "")
    if src.startswith("data:image/"):
        for attr in ["data-src", "data-lazy-src", "data-main-img"]:
            alt_src = img_tag.get(attr)
            if alt_src and not alt_src.startswith("data:image/"):
                return urljoin(base_url, alt_src)
        srcset = img_tag.get("srcset", "")
        if srcset:
            first_url = srcset.split(",")[0].strip().split(" ")[0]
            if first_url and not first_url.startswith("data:image/"):
                return urljoin(base_url, first_url)
        return src
    else:
        return urljoin(base_url, src)

def scrape_game_data(url):
    try:
        r = requests.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        cover_figure = soup.find("figure", class_="single-featured-image")
        cover_img_url = None
        if cover_figure:
            img = cover_figure.find("img")
            if not img:
                raise ValueError("Expected <img> tag inside cover figure not found")
            cover_img_url = get_real_image_url(img, url)

        post = soup.find("article", id="the-post")
        if not post:
            raise ValueError("Expected <article id='the-post'> element not found")
        content = post.find("div", class_="entry-content")
        if not content:
            raise ValueError("Expected <div class='entry-content'> inside article not found")

        # 1. Title
        keywords = ["download", "free", "direct"]
        title = None

        # Try header tags first (h2, h1, h3)
        for tag in ["h2", "h1", "h3"]:
            candidates = content.find_all(tag)
            for el in candidates:
                text = el.get_text(strip=True)
                if any(keyword in text.lower() for keyword in keywords):
                    title = text
                    break
            if title:
                break

        # If no title found in headers, try checking the first few <p> tags
        if not title:
            paragraphs = content.find_all("p", limit=5)
            for p in paragraphs:
                text = p.get_text(strip=True)
                if any(keyword in text.lower() for keyword in keywords):
                    title = text
                    break

        if not title:
            raise ValueError("Expected title element containing keywords not found in header or first paragraphs")


        # Rest of your code remains same
        # 2. Description paragraphs before first <h4>
        desc_parts = []
        for el in content.find_all(recursive=False):
            if el.name == "h4":
                break
            if el.name == "p":
                desc_parts.append(el.get_text(" ", strip=True))
        description = "\n".join(desc_parts)

        # 3. Screenshots section
        screenshots = []
        screenshots_h4 = content.find("h4", string=lambda s: s and "SCREENSHOTS" in s.upper())
        if screenshots_h4:
            for sibling in screenshots_h4.find_next_siblings():
                if sibling.name == "h4":
                    break
                for link in sibling.find_all("a", href=True):
                    full_url = urljoin(url, link["href"])
                    screenshots.append(full_url)

        # 4. System requirements
        system_requirements = {}
        sys_req_div = content.find("div", class_="checklist")
        if sys_req_div:
            for li in sys_req_div.find_all("li"):
                strong = li.find("strong")
                if strong:
                    key = strong.get_text(strip=True).rstrip(":")
                    value = li.get_text(strip=True).replace(strong.get_text(strip=True), "").strip(": ").strip()
                    system_requirements[key] = value

        # 5. Additional game info
        game_info = {}
        game_info_div = content.find("div", class_="plus")
        if game_info_div:
            for li in game_info_div.find_all("li"):
                strong = li.find("strong")
                if strong:
                    key = strong.get_text(strip=True).rstrip(":")
                    value = li.get_text(strip=True).replace(strong.get_text(strip=True), "").strip(": ").strip()
                    game_info[key] = value

        # 6. Download links
        download_links = []
        for a in content.find_all("a", href=True):
            if "download" in a.get_text(strip=True).lower():
                href = a["href"]
                if href.startswith("//"):
                    href = "https:" + href
                download_links.append(href)

        # If no download links found and page states fix no longer working, set download_links to page URL
        if not download_links:
            full_text = content.get_text(separator=" ", strip=True).lower()
            if "fix is no longer working." in full_text:
                download_links = [url]

        return {
            "page_url": url,
            "title": title.replace("Direct Download", "").strip(),
            "description": description,
            "screenshots": screenshots,
            "system_requirements": system_requirements,
            "game_info": game_info,
            "download_links": download_links,
            "cover_image": cover_img_url,
        }



    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        raise Exception(
            f"Error scraping {url}:\nOriginal error: {e}\nTraceback:\n{tb_str}"
        ) from e


if __name__ == "__main__":
    data = scrape_game_data(BASE_URL)
    from pprint import pprint
    pprint(data)
