import os
import time
import json
import subprocess
from pathlib import Path

def get_cookie_from_chrome(profile_dir, domain="your.tableau.server.com"):
    cookies_path = Path(profile_dir) / "Default" / "Network" / "Cookies"
    if not cookies_path.exists():
        raise FileNotFoundError("Cookies DB not found. Login must be completed in Chrome first.")

    cmd = [
        "sqlite3", str(cookies_path),
        f"SELECT name, value FROM cookies WHERE host_key LIKE '%{domain}%' AND name = 'workgroup_session_id';"
    ]
    result = subprocess.check_output(cmd).decode().strip()
    if result:
        name, value = result.split("|")
        return value
    else:
        raise Exception("workgroup_session_id not found in Chrome cookie store.")

def capture_dashboard(url, session_id, output_file):
    command = [
        "google-chrome",
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--window-size=1920,1080",
        f'--cookie=workgroup_session_id={session_id}',
        f'--screenshot={output_file}',
        url
    ]
    subprocess.run(command, check=True)
    print(f"Saved: {output_file}")

if __name__ == "__main__":
    chrome_profile = "/tmp/tableau-profile"
    tableau_view = "https://your.tableau.server.com/views/Workbook/ViewName?vf_Region=North&:refresh=yes&:maxAge=0"
    output_file = "north_view.png"

    cookie = get_cookie_from_chrome(chrome_profile, "your.tableau.server.com")
    capture_dashboard(tableau_view, cookie, output_file)
  
