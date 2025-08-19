import os
import time
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup
import pandas as pd

# Optional: Google Sheets (only used if you set env vars)
USE_SHEETS = os.getenv("USE_SHEETS", "false").lower() == "true"
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "YOUR_SPREADSHEET_ID")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME", "URLS")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "/path/to/service_account.json")

# Networking safety knobs (freelancers can tune)
REQUEST_TIMEOUT_SECS = int(os.getenv("REQUEST_TIMEOUT_SECS", "20"))
REQUEST_DELAY_SECS = float(os.getenv("REQUEST_DELAY_SECS", "0.5"))
HEADERS = {"User-Agent": "Mozilla/5.0 (+info@example.com)"}  # harmless UA

def get_urls_from_local_csv(csv_path: str = "urls.csv") -> List[str]:
    """
    Fallback for freelancers: put a 'urls.csv' with a single 'url' column in the repo.
    """
    if not os.path.exists(csv_path):
        return []
    df = pd.read_csv(csv_path)
    col = [c for c in df.columns if c.strip().lower() == "url"]
    return df[col[0]].dropna().tolist() if col else []

def get_urls_from_google_sheets() -> List[str]:
    """
    Uses gspread only if USE_SHEETS=true and credentials are provided via env.
    This keeps secrets out of source code.
    """
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SERVICE_ACCOUNT_JSON, scope)
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    urls = sheet.col_values(1)  # column A
    if urls and urls[0].strip().lower() == "url":
        urls = urls[1:]
    return [u for u in urls if u]

def fetch_html(url: str) -> Optional[str]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECS)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"[WARN] Failed to GET {url}: {e}")
        return None

def parse_stock_rows(html: str) -> List[Dict[str, str]]:
    """
    Parses the specific DOM you had. If a freelancer wants to improve robustness,
    they can parameterise selectors here.
    """
    soup = BeautifulSoup(html, 'html.parser')
    out: List[Dict[str, str]] = []

    rows = soup.find_all(
        'div',
        {'class': 'product_form_list container is-justtify-space-between has-no-side-gutter content-for-list'}
    )
    for row in rows:
        # strip header blocks if present
        for header in row.find_all('div', {'class': 'column header one-fifth medium-down--one-half'}):
            header.decompose()

        columns = row.find_all('div', {'class': 'column'})
        # iterate in chunks of 5 as in the original assumption
        for i in range(0, len(columns), 5):
            try:
                qty_col = columns[i + 3] if (i + 3) < len(columns) else None
                max_quantity = (
                    qty_col.find('input').get('max', 'Unknown') if qty_col and qty_col.find('input') else 'Unknown'
                )
                code_text = columns[i].get_text(strip=True) if i < len(columns) else ""
                code = code_text.split(' ', 1)[0] if code_text else ""

                if code:
                    out.append({'Code': code, 'QTY': max_quantity})
            except Exception as e:
                print(f"[WARN] Row parse error at index {i}: {e}")
    return out

def try_parse_int(val) -> Optional[int]:
    try:
        return int(val)
    except Exception:
        return None

def derive_manual_skus(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reproduces your manual SKU logic.
    """
    df = df.copy()
    qty_5l = df.loc[df['Code'] == 'ACGEL5L', 'QTY']
    qty_250 = df.loc[df['Code'] == 'ACGEL250', 'QTY']

    if not qty_5l.empty:
        q_5l = try_parse_int(qty_5l.values[0])
        if q_5l is not None:
            df = pd.concat([df, pd.DataFrame([{'Code': 'ACGEL5L+', 'QTY': q_5l}])], ignore_index=True)

    if not qty_250.empty:
        q_250 = try_parse_int(qty_250.values[0])
        if q_250 is not None:
            derived = [
                {'Code': 'ACGEL250(2)', 'QTY': q_250 // 2},
                {'Code': 'ACGEL250(4)', 'QTY': q_250 // 4},
                {'Code': 'ACGEL250(12)', 'QTY': q_250 // 12},
            ]
            df = pd.concat([df, pd.DataFrame(derived)], ignore_index=True)

    return df

def write_to_google_sheets(df: pd.DataFrame):
    """
    Writes only if USE_SHEETS=true.
    Clears columns B and C then writes Code/QTY starting B2/C2.
    """
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SERVICE_ACCOUNT_JSON, scope)
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)

    # Clear B and C from row 2 down
    sheet.batch_clear(["B2:B", "C2:C"])

    # Prepare values
    values = list(zip(df["Code"].astype(str).tolist(), df["QTY"].astype(str).tolist()))
    if not values:
        return

    # Update columns B and C
    # gspread batch_update via ranges (fewer API calls)
    code_col = [["Code"]] + [[v[0]] for v in values]
    qty_col = [["QTY"]] + [[v[1]] for v in values]
    sheet.update("B1:B{}".format(len(code_col)), code_col)
    sheet.update("C1:C{}".format(len(qty_col)), qty_col)

    # Bold header
    sheet.format("B1:C1", {"textFormat": {"bold": True}})

def main():
    # 1) Get URLs
    if USE_SHEETS:
        urls = get_urls_from_google_sheets()
    else:
        urls = get_urls_from_local_csv("urls.csv")

    if not urls:
        print("[INFO] No URLs found. Provide urls.csv or enable USE_SHEETS.")
        return

    all_stock_data: List[Dict[str, str]] = []
    for url in urls:
        html = fetch_html(url)
        if html:
            rows = parse_stock_rows(html)
            all_stock_data.extend(rows)
        time.sleep(REQUEST_DELAY_SECS)

    # 2) Build DataFrame
    df = pd.DataFrame(all_stock_data or [], columns=["Code", "QTY"]).dropna(subset=["Code"])
    df = derive_manual_skus(df)

    # 3) Output
    if USE_SHEETS:
        write_to_google_sheets(df)
        print("Google Sheet updated successfully with manual SKUs.")
    else:
        out_path = "output.csv"
        df.to_csv(out_path, index=False)
        print(f"Wrote {len(df)} rows to {out_path}")

if __name__ == "__main__":
    main()
