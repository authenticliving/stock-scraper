# Inventory Scraper

This script scrapes stock quantities from supplier websites and outputs them into either:
- a CSV file (`output.csv`), or  
- a Google Sheet (if enabled with environment variables).

## How to run
1. Install dependencies:
   ```bash
   pip install requests beautifulsoup4 pandas gspread oauth2client

## Future Work / Tasks for Freelancer

The current script is a simple proof of concept. I am looking for a developer to extend and improve it with the following:

1. **Automation**
   - Set up the script to run daily without manual intervention (e.g. scheduled task, cron job, or deployment to Google Cloud Platform / AWS / Azure).

2. **Functionality Enhancements**
   - Add user-friendly ways for non-technical staff to adjust SKU logic (e.g. bundle rules, stock adjustments).
   - Support scraping from multiple supplier websites with different layouts.

3. **Error Handling & Logging**
   - Improve handling of timeouts, failed requests, and missing data.
   - Add logging with clear error messages and optional email/Slack notifications.

4. **Performance Optimisation**
   - Optimise scraper speed and efficiency.
   - Ensure requests are respectful of supplier sites (avoid being blocked).

5. **Google Sheets Integration**
   - Extend Google Sheets functionality:
     - Automatically update master sheet with fresh stock data.
     - Handle authentication securely via service account or OAuth.
     - Ensure compatibility for multiple sheets / suppliers.

6. **Documentation**
   - Improve README with setup instructions for both CSV-only and Google Sheets versions.
   - Add comments in the code for easier handover.

---
