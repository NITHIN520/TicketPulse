import os
import time
import random
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
BASE_URL = "https://commerceiq.freshdesk.com"
TICKETS_XLSX = "Ticket_sheet2.xlsx"
OUTPUT_XLSX = "ticket_activities_scraped1.xlsx"

BATCH_SIZE = 75          # Safe batch size
MIN_DELAY = 1            # seconds
MAX_DELAY = 10           # seconds

# --------------------------------------------------
# AUTH COOKIES  (paste fresh cookies here when expired)
# Only the 6 cookies required for Freshdesk auth are kept.
# --------------------------------------------------
COOKIE_STRING = (
    "__cf_bm=vw5tABdJVe.L.xevMWTy6FB9VgXSQ99Qxguw2q0_X6E-1781436053.502242-1.0.1.1-N6Y5qVMb._esMGIdq4f8NC60_IIEPyOWuw_dwcTKYOjdwBl0XreDIszKs6kAZ0.grJlDwUXOpyw9DKpuEWEBLMTEcKqqfwkMruVKHQC7vFmV42Vdf4polY1MZKD0PnNr; "
    "fd=2253dabf-daa8-4403-8a7a-6c69775d39ac; "
    "helpdesk_url=commerceiq.freshdesk.com; "
    "helpdesk_node_session=c7b695deedf1ba8665959e4b177d1e0199b7f5ef4631a080a76ede45869ad817f8d827f5b9dc9cdd2293828c12f449172990a409df6ce68c6cbe2c5d70e7f640; "
    "user_credentials=BAhJIgGPYTkxM2NmOWE3ZDFjNGE0NzhmYWI1OGM1ZGU3NGU4ZDZlMTg1NmFkMTBlYjg0NWE1MWRlOGVlYmIwYzU3Mjc0MjM2ZDc4YTE0NGMwOWFlNGNkM2Y3MWU5ODU0NzRjOGE5ZGIwMjUzOTIwZmFjZDBhMDk2MmE5NGJmMzlkYTFjYTU6OjIwNDMxOTQ1MTkwMDgGOgZFVA%3D%3D--76e9a00d2f793009cf93a2a4b9253a2184141330; "
    "session_token=1367e502a1c3456c8d043acfbd77e7c1704182b87d1bdfd40c39d5c43ee765973ed8febe7a77bc2ffd72cb965c76344676061911c5455906615bd8a6934791fb0c1c3cc7e7404aa43984175cb8955d9e56b47e8a23175792bfb2cb0e8e068a2eace33995104c3958bd342bd8cb42869e"
)


def parse_cookies(cookie_str: str, domain: str) -> list:
    """Parse a browser cookie string into a Playwright-compatible list."""
    cookies = []
    for part in cookie_str.split("; "):
        if "=" not in part:
            continue
        name, _, value = part.strip().partition("=")
        cookies.append({
            "name": name.strip(),
            "value": value.strip(),
            "domain": domain,
            "path": "/",
        })
    return cookies


# --------------------------------------------------
# LOAD TICKET IDS
# --------------------------------------------------
def load_ticket_ids(path: str):
    df = pd.read_excel(path, dtype=str)
    if "ticket_id" in df.columns:
        return df["ticket_id"].dropna().astype(str).tolist()
    return df.iloc[:, 0].dropna().astype(str).tolist()


# --------------------------------------------------
# LOGIN / CONTEXT (COOKIE-BASED, ALWAYS HEADLESS)
# --------------------------------------------------
def ensure_logged_in(playwright):
    browser = playwright.chromium.launch(headless=True)

    context = browser.new_context(
        viewport={"width": 2560, "height": 1600},
        device_scale_factor=2,
    )

    cookies = parse_cookies(COOKIE_STRING, "commerceiq.freshdesk.com")
    context.add_cookies(cookies)
    print(f"✔ Injected {len(cookies)} cookies — running headless")

    return browser, context


# --------------------------------------------------
# FIND SHOW ACTIVITIES BUTTON
# --------------------------------------------------
def find_show_activities_button(page):
    # Primary: new button using data-test-toggle-activity attribute
    btn = page.locator("button[data-test-toggle-activity]")
    if btn.count() > 0:
        return btn.first

    # Fallback: aria-label
    btn = page.locator("button[aria-label='Activities']")
    if btn.count() > 0:
        return btn.first

    # Fallback: old title-based selector
    btn = page.locator("button[title='Show activities']")
    if btn.count() > 0:
        return btn.first

    return None


# --------------------------------------------------
# SCROLL HELPER
# --------------------------------------------------
def scroll_page(page, times=4, step=1200, wait=500):
    for _ in range(times):
        page.evaluate(f"window.scrollBy(0, {step})")
        page.wait_for_timeout(wait)


# --------------------------------------------------
# CLICK ALL "LOAD MORE"
# --------------------------------------------------
def click_load_more(page, ticket_id):
    for r in range(20):
        more = page.locator('[data-test-id="activities-load-more"]')
        if more.count() == 0:
            break

        print(f"  ▶ Ticket {ticket_id}: clicking 'Load more' (round {r + 1})")
        try:
            more.first.scroll_into_view_if_needed()
            more.first.click(timeout=5000)
            page.wait_for_timeout(1500)
        except Exception:
            break

        scroll_page(page, times=2)


# --------------------------------------------------
# GRAB ACTIVITIES TEXT
# --------------------------------------------------
def grab_activities_text(page):
    for selector in ["main", "div[role='main']"]:
        loc = page.locator(selector)
        if loc.count() > 0:
            return loc.first.inner_text()
    return page.inner_text("body")


# --------------------------------------------------
# OPEN TICKET & FETCH ACTIVITIES
# --------------------------------------------------
def open_ticket_and_fetch_activities(context, ticket_id):
    page = context.new_page()
    ticket_url = f"{BASE_URL}/a/tickets/{ticket_id}"

    print(f"\n=== Ticket {ticket_id} ===")

    try:
        page.goto(ticket_url, timeout=60000, wait_until="domcontentloaded")
    except PlaywrightTimeoutError:
        page.goto(ticket_url, timeout=60000, wait_until="domcontentloaded")

    page.wait_for_timeout(3000)

    btn = find_show_activities_button(page)
    if not btn:
        print("⚠ 'Activities' button not found")
        text = page.inner_text("body")
        page.close()
        return text

    btn.click()
    print("✔ Activities panel opened")

    page.wait_for_timeout(2000)
    scroll_page(page)
    click_load_more(page, ticket_id)
    scroll_page(page, times=3)

    text = grab_activities_text(page)
    print(f"✔ Captured activities text (length: {len(text)})")

    page.close()
    return text


# --------------------------------------------------
# MAIN (BATCH + RANDOM DELAY)
# --------------------------------------------------
def main():
    if not os.path.exists(TICKETS_XLSX):
        print(f"❌ Missing input file: {TICKETS_XLSX}")
        return

    ticket_ids = load_ticket_ids(TICKETS_XLSX)
    print(f"➡ Found {len(ticket_ids)} ticket IDs")

    rows = []

    with sync_playwright() as p:
        for i in range(0, len(ticket_ids), BATCH_SIZE):
            batch = ticket_ids[i:i + BATCH_SIZE]
            print(f"\n🚀 Processing batch {i // BATCH_SIZE + 1}")

            browser, context = ensure_logged_in(p)

            for tid in batch:
                try:
                    txt = open_ticket_and_fetch_activities(context, tid)
                except Exception as e:
                    print(f"⚠ Error on ticket {tid}: {e}")
                    txt = f"ERROR: {e}"

                rows.append({
                    "ticket_id": tid,
                    "activities_text": txt
                })

                delay = random.randint(MIN_DELAY, MAX_DELAY)
                print(f"⏳ Sleeping {delay} seconds")
                time.sleep(delay)

            context.close()
            browser.close()

    pd.DataFrame(rows).to_excel(OUTPUT_XLSX, index=False)
    print(f"\n✅ Saved raw activities to {OUTPUT_XLSX}")


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------
if __name__ == "__main__":
    main()
