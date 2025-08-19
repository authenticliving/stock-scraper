# Inventory Scraper

This script scrapes stock quantities from supplier websites and outputs them into either:
- a CSV file (`output.csv`), or  
- a Google Sheet (if enabled with environment variables).

## How to run
1. Install dependencies:
   ```bash
   pip install requests beautifulsoup4 pandas gspread oauth2client
