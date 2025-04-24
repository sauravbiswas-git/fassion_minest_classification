import os
import time
import urllib.parse
import requests
import subprocess
from config import tableau_config


class TableauHeadlessScreenshot:
    def __init__(self):
        self.server = tableau_config["server"]
        self.api_version = tableau_config["api_version"]
        self.username = tableau_config["username"]
        self.password = tableau_config["password"]
        self.site = tableau_config.get("site_content_url", "")
        self.site_param = "" if self.site == "" else f"/sites/{self.site}"
        self.auth_token = None
        self.session_id = None

    def sign_in(self):
        url = f"{self.server}/api/{self.api_version}/auth/signin"
        payload = {
            "credentials": {
                "name": self.username,
                "password": self.password,
                "site": {"contentUrl": self.site}
            }
        }

        response = requests.post(url, json=payload)
        if response.status_code == 200:
            self.auth_token = response.json()['credentials']['token']
            self.session_id = response.cookies.get('workgroup_session_id')
            print("Signed in. Session ID obtained.")
        else:
            raise Exception(f"Failed to sign in: {response.status_code} - {response.text}")

    def build_dashboard_url(self, view_path, filters: dict):
        filter_str = "&".join([
            f"vf_{urllib.parse.quote_plus(k)}={urllib.parse.quote_plus(v)}"
            for k, v in filters.items()
        ])
        timestamp = int(time.time())
        return f"{self.server}/views/{view_path}?{filter_str}&:refresh=yes&:maxAge=0&cb={timestamp}"

    def capture_with_headless_chrome(self, url, output_file):
        cookie = f"workgroup_session_id={self.session_id}"
        command = [
            "google-chrome",
            "--headless",
            "--disable-gpu",
            f"--screenshot={output_file}",
            f"--window-size=1920,1080",
            f"--user-agent=Mozilla/5.0",
            f"--cookie={cookie}",
            url
        ]
        print(f"Running: {' '.join(command)}")
        subprocess.run(command)

    def export_images_with_filters(self, view_path, filters_list, output_dir="output"):
        os.makedirs(output_dir, exist_ok=True)
        for filters in filters_list:
            filename = "_".join(f"{k}_{v.replace(',', '_')}" for k, v in filters.items()) + ".png"
            file_path = os.path.join(output_dir, filename)
            full_url = self.build_dashboard_url(view_path, filters)
            print(f"Exporting image for: {full_url}")
            self.capture_with_headless_chrome(full_url, file_path)

    def sign_out(self):
        url = f"{self.server}/api/{self.api_version}/auth/signout"
        headers = {"X-Tableau-Auth": self.auth_token}
        requests.post(url, headers=headers)
        print("Signed out.")


if __name__ == "__main__":
    view_path = "YourWorkbook/YourDashboard"  # e.g. "SalesWorkbook/Overview"

    filters_list = [
        {"Region": "North"},
        {"Region": "North,South"},
        {"Region": "East,West", "Category": "Technology"},
    ]

    exporter = TableauHeadlessScreenshot()
    exporter.sign_in()
    exporter.export_images_with_filters(view_path, filters_list)
    exporter.sign_out()
    
