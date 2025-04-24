import os
import time
import urllib.parse
import subprocess
import requests
from tableau_api_lib import TableauServerConnection
from tableau_api_lib.utils.querying import get_views_dataframe
from config import tableau_config


class TableauCLIScreenshotExporter:
    def __init__(self):
        self.connection = TableauServerConnection(tableau_config)
        self.connection.sign_in()
        self.site_id = self.connection.site_id
        self.server = tableau_config["server"]
        self.api_version = tableau_config["api_version"]
        self.headers = self.connection.auth_headers

    def get_view_url(self, view_id, filters):
        filter_string = "&".join(
            f"vf_{urllib.parse.quote_plus(k)}={urllib.parse.quote_plus(v)}"
            for k, v in filters.items()
        )
        timestamp = int(time.time())
        return (
            f"{self.server}/trusted/{self.get_trusted_ticket()}/views/"
            f"{view_id}?"
            f"{filter_string}&:refresh=yes&:maxAge=0&cb={timestamp}"
        )

    def get_trusted_ticket(self):
        auth_payload = {
            "username": tableau_config["username"],
            "target_site": tableau_config["site_content_url"]
        }
        url = f"{self.server}/trusted"
        response = requests.post(url, data=auth_payload, verify=False)
        if response.status_code == 200 and response.text.strip() not in ["", "-1"]:
            return response.text.strip()
        else:
            raise Exception("Failed to get trusted ticket.")

    def export_images_with_filters(self, workbook_name, filters_list, output_path="output"):
        os.makedirs(output_path, exist_ok=True)
        views_df = get_views_dataframe(self.connection)
        views = views_df[views_df['workbookName'] == workbook_name]

        for _, view in views.iterrows():
            for filters in filters_list:
                file_name = "_".join(f"{k}_{v.replace(',', '_')}" for k, v in filters.items()) + ".png"
                file_path = os.path.join(output_path, file_name)

                view_url = self.get_view_url(view['contentUrl'], filters)

                print(f"Capturing {file_name} from: {view_url}")
                self.capture_with_chrome(view_url, file_path)

    def capture_with_chrome(self, url, output_file):
        command = [
            "google-chrome",
            "--headless",
            "--disable-gpu",
            f"--screenshot={output_file}",
            "--window-size=1920,1080",
            url
        ]
        subprocess.run(command)

    def sign_out(self):
        self.connection.sign_out()


if __name__ == "__main__":
    exporter = TableauCLIScreenshotExporter()

    filters_list = [
        {"Region": "North"},
        {"Region": "North,South"},
        {"Region": "East,West", "Category": "Technology"},
    ]

    exporter.export_images_with_filters(workbook_name="Sample Workbook", filters_list=filters_list)
    exporter.sign_out()
              
