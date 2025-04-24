import os
import time
import urllib.parse
import subprocess
import requests
import xml.etree.ElementTree as ET
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

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            try:
                self.auth_token = response.json()['credentials']['token']
            except ValueError:
                root = ET.fromstring(response.text)
                ns = {"t": "http://tableau.com/api"}
                self.auth_token = root.find(".//t:credentials", ns).attrib['token']
            print("Signed in. Token received.")

            # Call /me to get session cookie
            me_url = f"{self.server}/api/{self.api_version}/me"
            me_headers = {"X-Tableau-Auth": self.auth_token}
            me_response = requests.get(me_url, headers=me_headers)

            # Extract session cookie
            self.session_id = me_response.cookies.get('workgroup_session_id')
            if not self.session_id:
                raise Exception("Session ID not found in /me response cookies.")
            print(f"Session ID obtained: {self.session_id}")
        else:
            raise Exception(f"Failed to sign in: {response.status_code} - {response.text}")

    def build_dashboard_url(self, view_path, filters: dict):
        filter_str = "&".join(
            f"vf_{urllib.parse.quote_plus(k)}={urllib.parse.quote_plus(v)}"
            for k, v in filters.items()
        )
        timestamp = int(time.time())
        return f"{self.server}/views/{view_path}?{filter_str}&:refresh=yes&:maxAge=0&cb={timestamp}"

    def capture_with_headless_chrome(self, url, output_file):
        if not self.session_id:
            raise Exception("Session ID not available.")

        user_data_dir = f"/tmp/chrome-profile-{int(time.time())}"
        command = [
            "google-chrome",
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--window-size=1920,1080",
            f"--user-data-dir={user_data_dir}",
            f"--cookie=workgroup_session_id={self.session_id}",
            f"--screenshot={output_file}",
            url
        ]
        print(f"Running Chrome to capture: {output_file}")
        subprocess.run(command, check=True)

    def export_images_with_filters(self, view_path, filters_list, output_dir="output"):
        os.makedirs(output_dir, exist_ok=True)
        for filters in filters_list:
            filename = "_".join(f"{k}_{v.replace(',', '_')}" for k, v in filters.items()) + ".png"
            file_path = os.path.join(output_dir, filename)
            full_url = self.build_dashboard_url(view_path, filters)
            print(f"Exporting image from: {full_url}")
            self.capture_with_headless_chrome(full_url, file_path)

    def sign_out(self):
        url = f"{self.server}/api/{self.api_version}/auth/signout"
        headers = {"X-Tableau-Auth": self.auth_token}
        requests.post(url, headers=headers)
        print("Signed out from Tableau.")


if __name__ == "__main__":
    # Viz-style view path: Workbook/ViewName
    view_path = "SalesWorkbook/SalesDashboard"  # Replace with yours

    filters_list = [
        {"Region": "North"},
        {"Region": "North,South"},
        {"Region": "East,West", "Category": "Technology"},
    ]

    exporter = TableauHeadlessScreenshot()
    exporter.sign_in()
    exporter.export_images_with_filters(view_path, filters_list)
    exporter.sign_out()
    
