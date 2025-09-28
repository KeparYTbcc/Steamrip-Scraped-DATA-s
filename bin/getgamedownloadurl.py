#!/usr/bin/env python3
"""
SteamRip Direct Download URL Extractor
Extracts direct download URLs from SteamRip pages using browser automation.
"""

import sys
import json
import time
import os
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options

# Set this path to your Brave browser executable
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"  # <-- Update if needed

# Folder to save downloads (not used for actual browser downloads here)
DOWNLOAD_FOLDER = "./temp_downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def convert_to_direct_download_url(url):
    """
    Convert various file hosting URLs to their direct download format.
    """
    # Pixeldrain conversion
    if 'pixeldrain.com' in url:
        if '/u/' in url:
            file_id = url.split('/u/')[-1].split('?')[0].split('#')[0]
            return f"https://pixeldrain.com/api/file/{file_id}?download"
    
    # Add more conversions here as needed
    # Example for other file hosts:
    # if 'mediafire.com' in url:
    #     # Convert mediafire URL format
    
    return url

def is_downloadable(url, headers):
    """
    Check if URL or response headers indicate a .zip or .rar download.
    """
    cd = headers.get('content-disposition', '')
    if 'attachment' in cd.lower():
        return True
    for ext in ['.zip', '.rar']:
        if url.lower().endswith(ext):
            return True
    return False


def get_direct_download_url(start_url):
    """
    Extract direct download URL from SteamRip page using browser automation.
    Returns the direct download URL or None if not found.
    """
    # Check if it's a pixeldrain URL that we can convert directly
    if 'pixeldrain.com' in start_url and '/u/' in start_url:
        print(f"[*] Detected pixeldrain URL: {start_url}", file=sys.stderr)
        direct_url = convert_to_direct_download_url(start_url)
        if direct_url != start_url:
            print(f"[+] Converted pixeldrain URL to direct download: {direct_url}", file=sys.stderr)
            print(direct_url)
            return direct_url
    
    # For other URLs, use undetected-chromedriver
    options = uc.ChromeOptions()
    options.binary_location = BRAVE_PATH
    
    # Basic settings for undetected-chromedriver
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--safebrowsing-disable-download-protection")
    
    # Disable some features but keep Cloudflare compatibility
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    
    # Disable Brave's aggressive privacy features for Cloudflare compatibility
    options.add_argument("--disable-brave-features")
    options.add_argument("--disable-brave-extension")
    options.add_argument("--disable-brave-shields")
    
    # Allow necessary features for Cloudflare
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-features=VizDisplayCompositor")
    
    # Add random window size to appear more human
    import random
    width = random.randint(1200, 1920)
    height = random.randint(800, 1080)
    options.add_argument(f"--window-size={width},{height}")
    
    # Set download behavior to deny but allow Cloudflare scripts
    prefs = {
        "download.default_directory": os.path.abspath(DOWNLOAD_FOLDER),  # Keep original folder
        "download.prompt_for_download": False,
        "download.directory_upgrade": False,
        "safebrowsing.enabled": False,
        "safebrowsing.disable_download_protection": True,
        "profile.default_content_setting_values.automatic_downloads": 1,  # Block all downloads
        "profile.default_content_settings.popups": 2,  # Block popups
        
        # Disable Brave's privacy features that interfere with Cloudflare
        "profile.default_content_setting_values.javascript": 1,  # Allow JavaScript
        "profile.default_content_setting_values.cookies": 1,  # Allow cookies
        "profile.default_content_setting_values.media_stream": 1,  # Allow media
        "profile.default_content_setting_values.geolocation": 1,  # Allow geolocation
        "profile.default_content_setting_values.notifications": 1,  # Allow notifications
        
        # Disable Brave's fingerprinting protection for Cloudflare
        "profile.default_content_setting_values.plugins": 1,  # Allow plugins
        "profile.default_content_setting_values.images": 1,  # Allow images for captcha
    }
    options.add_experimental_option("prefs", prefs)

    # Enable performance logging to capture network events
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    # Use undetected-chromedriver for better anti-detection
    driver = uc.Chrome(options=options)
    
    print(f"[*] Navigating to: {start_url}", file=sys.stderr)
    driver.get(start_url)
    
    # Add script to prevent downloads (undetected-chromedriver handles anti-detection)
    driver.execute_script("""
        // Prevent any download attempts
        window.addEventListener('beforeunload', function(e) {
            e.preventDefault();
            e.returnValue = '';
        });
        
        // Override download functions
        if (window.navigator && window.navigator.msSaveBlob) {
            window.navigator.msSaveBlob = function() { return false; };
        }
        
        // Prevent form submissions that might trigger downloads
        document.addEventListener('submit', function(e) {
            e.preventDefault();
            return false;
        });
    """)

    print("[*] Brave launched. Monitoring for .zip or .rar download URLs...", file=sys.stderr)

    try:
        print("[*] Using undetected-chromedriver for better Cloudflare bypass...", file=sys.stderr)
        
        # Wait a bit for page to load
        time.sleep(3)
        
        max_wait_time = 120  # Maximum 2 minutes for manual captcha solving
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # Check for Cloudflare challenge
            try:
                page_source = driver.page_source.lower()
                if 'cloudflare' in page_source and ('checking' in page_source or 'challenge' in page_source):
                    print("[*] Cloudflare challenge detected. Please solve the captcha manually in the browser.", file=sys.stderr)
                    print("[*] The script will wait for you to complete the challenge...", file=sys.stderr)
                    time.sleep(5)  # Check every 5 seconds
                    continue
            except:
                pass
            
            logs = driver.get_log('performance')
            for entry in logs:
                message = entry['message']
                if '"Network.responseReceived"' in message:
                    try:
                        message_json = json.loads(message)['message']
                        response = message_json['params']['response']
                        url = response['url']
                        headers = {k.lower(): v for k, v in response['headers'].items()}

                        if is_downloadable(url, headers):
                            print(f"[+] Detected downloadable URL: {url}", file=sys.stderr)
                            
                            # Convert to direct download URL if possible
                            direct_url = convert_to_direct_download_url(url)
                            if direct_url != url:
                                print(f"[+] Converted to direct download URL: {direct_url}", file=sys.stderr)
                                url = direct_url
                            
                            # Return the URL directly to stdout for main.py to capture
                            print(url)
                            # Stop page load immediately to prevent browser download
                            driver.execute_script("window.stop();")
                            driver.quit()
                            return url

                    except Exception:
                        pass
            
            time.sleep(1)  # Check every second

    except KeyboardInterrupt:
        print("[*] Interrupted by user. Exiting...", file=sys.stderr)
    except Exception as e:
        print(f"[ERROR] Browser automation failed: {e}", file=sys.stderr)
        print("[INFO] This might be due to aggressive Cloudflare protection.", file=sys.stderr)
    finally:
        try:
            driver.quit()
        except:
            pass

    # If we get here, the automated approach failed
    print("[WARNING] Automated URL extraction failed.", file=sys.stderr)
    print("[INFO] This could be due to:", file=sys.stderr)
    print("  - Aggressive Cloudflare protection", file=sys.stderr)
    print("  - Complex captcha challenges", file=sys.stderr)
    print("  - Anti-bot detection", file=sys.stderr)
    print("[INFO] You may need to manually extract the download URL.", file=sys.stderr)
    
    return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python getgamedownloadurl.py <url>", file=sys.stderr)
        sys.exit(1)
    
    test_url = sys.argv[1]
    download_url = get_direct_download_url(test_url)
    if download_url:
        print(f"[SUCCESS] Retrieved direct download URL: {download_url}", file=sys.stderr)
    else:
        print("[ERROR] No download URL detected.", file=sys.stderr)
        sys.exit(1)
