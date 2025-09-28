# SteamRip External Downloader

A Python application for scraping game data from SteamRip and downloading game files with automated direct download URL extraction.

## Features

- **Game Database Management**: Scrape and maintain a local database of SteamRip games
- **Search Functionality**: Search through scraped game data
- **Automated Downloads**: Extract direct download URLs and download game files
- **Multi-threaded Scraping**: Fast database updates with concurrent processing
- **Error Recovery**: Retry failed scrapes and maintain failed games list

## Quick mention
1. it dosent download yet, but it is scrapping everything
2. the "Games" folder aint needed for the code, its pre-scrapped datas, if u want to look at it, but might get outdated by the time


## Installation

1. **Clone or download the project**
2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Brave Browser** (required for download URL extraction):
   - Download from: https://brave.com/
   - Update the `BRAVE_PATH` in `bin/getgamedownloadurl.py` if needed

## Usage

### Basic Usage

Run the main application:
```bash
python main.py
```

### Menu Options

1. **Search games** - Search the local database for games
2. **Refresh database** - Scrape all games from SteamRip (multithreaded)
3. **Clean database** - Delete all local game data files
4. **Retry failed scrapes** - Retry previously failed game scrapes
5. **Quickcheck database** - Check for incomplete or corrupted files
6. **Exit** - Close the application
7. **Check for updates** - Look for new or updated game versions
8. **Download game files** - Download a specific game

### Download Process

When downloading a game:

1. Search for the game by title
2. Select the game from the results
3. Choose a download link from the available options
4. The system will automatically:
   - Extract the direct download URL using Selenium/Brave
   - Open a folder selection dialog
   - Download the file with progress tracking

## File Structure

```
SteamRip External Downloader/
├── main.py                 # Main application
├── requirements.txt        # Python dependencies
├── test_integration.py     # Integration test script
├── bin/
│   ├── gamelistparser.py   # Parse SteamRip games list
│   ├── gamedataextractor.py # Extract game data from pages
│   └── getgamedownloadurl.py # Extract direct download URLs
├── data/
│   └── clones/             # Local game database
├── downloads/              # Default download folder
└── temp_downloads/         # Temporary files for URL extraction
```

## Integration Details

### getgamedownloadurl.py Integration

The `getgamedownloadurl.py` script is automatically called by `main.py` when downloading games. It:

- Uses Selenium with Brave browser to navigate to download pages
- Monitors network traffic to detect direct download URLs
- Returns the URL via stdout for `main.py` to capture
- Runs in headless mode for automation
- Has a 60-second timeout to prevent hanging

### Error Handling

The integration includes comprehensive error handling:

- **Python executable detection**: Automatically finds the correct Python path
- **Timeout protection**: 2-minute timeout for URL extraction
- **File validation**: Verifies downloaded files exist and have proper size
- **Fallback filenames**: Uses game title if URL doesn't contain filename
- **Detailed logging**: Provides debug information for troubleshooting

## Testing

Run the integration test to verify everything works:

```bash
python test_integration.py
```

This will check:
- Python environment and dependencies
- Module imports
- Script availability and basic functionality

## Troubleshooting

### Common Issues

1. **"Python executable not found"**
   - Make sure Python is installed and in PATH
   - Or activate your virtual environment

2. **"getgamedownloadurl.py failed"**
   - Check that Brave browser is installed
   - Update `BRAVE_PATH` in the script if needed
   - Ensure Selenium and webdriver-manager are installed

3. **"No download URL detected"**
   - The download page might have changed
   - Try a different download link
   - Check if the site is accessible

4. **Download timeouts**
   - Increase timeout values in the scripts
   - Check your internet connection
   - Some download servers may be slow

### Debug Mode

For detailed debugging, the scripts output progress information to stderr. Check the console output for detailed error messages.

## Requirements

- Python 3.7+
- Brave Browser
- Internet connection
- Sufficient disk space for game downloads

## Dependencies

- `requests`: HTTP requests
- `beautifulsoup4`: HTML parsing
- `selenium`: Browser automation
- `webdriver-manager`: ChromeDriver management
- `lxml`: XML/HTML parser

## License

This project is for educational purposes. Please respect the terms of service of the websites you interact with.


