import os
import time
import urllib.parse
import asyncio
from playwright.async_api import async_playwright

# ---------------- CONFIG ----------------
TABLEAU_BASE_URL = "https://your-tableau-server.com"
TABLEAU_VIEW_PATH = "views/YourWorkbook/YourView"
USERNAME = "your_username"
PASSWORD = "your_password"
OUTPUT_DIR = "output"
WAIT_TIME = 10  # seconds
HEADLESS = True


FILTERS_LIST = [
    {"Region": "North"},
    {"Region": "North,South"},
    {"Region": "East,West", "Category": "Technology"},
]


def build_filtered_url(filters: dict) -> str:
    encoded_filters = "&".join(
        f"vf_{urllib.parse.quote_plus(k)}={urllib.parse.quote_plus(v)}"
        for k, v in filters.items()
    )
    timestamp = int(time.time())
    return f"{TABLEAU_BASE_URL}/{TABLEAU_VIEW_PATH}?{encoded_filters}&:refresh=yes&:maxAge=0&cb={timestamp}"


def get_output_filename(filters: dict) -> str:
    return "_".join(f"{k}_{v.replace(',', '_')}" for k, v in filters.items()) + ".png"


async def capture_tableau_screenshot(playwright, url, output_file):
    browser = await playwright.chromium.launch(headless=HEADLESS)
    context = await browser.new_context()
    page = await context.new_page()

    print(f"Logging in and navigating to: {url}")
    await page.goto(f"{TABLEAU_BASE_URL}/login", wait_until="load")

    # Auto-login (for username/password auth only)
    await page.fill('input[name="username"]', USERNAME)
    await page.fill('input[name="password"]', PASSWORD)
    await page.click('button[type="submit"]')

    # Wait for redirect to Tableau home or dashboard
    await page.wait_for_url("**/views/**", timeout=20000)

    await page.goto(url, wait_until="load")
    await page.wait_for_timeout(WAIT_TIME * 1000)

    # Wait for dashboard content only (change this selector as needed)
    await page.wait_for_selector('.tableauViz', timeout=20000)

    # Get bounding box of viz div to crop screenshot
    viz_element = await page.query_selector('.tableauViz')
    box = await viz_element.bounding_box()

    print(f"Capturing screenshot: {output_file}")
    await page.screenshot(
        path=output_file,
        clip={
            "x": box["x"],
            "y": box["y"],
            "width": box["width"],
            "height": box["height"]
        }
    )

    await browser.close()
    print("Done.\n")


async def run_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    async with async_playwright() as playwright:
        tasks = []
        for filters in FILTERS_LIST:
            url = build_filtered_url(filters)
            filename = get_output_filename(filters)
            output_path = os.path.join(OUTPUT_DIR, filename)
            tasks.append(capture_tableau_screenshot(playwright, url, output_path))

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(run_all())
  
