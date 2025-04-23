from tableau_api_lib import TableauServerConnection
from tableau_api_lib.utils.querying import get_views_dataframe
import requests
import os
import urllib.parse
from config import tableau_config


class TableauImageExporterWithRefresh:
    def __init__(self):
        self.connection = TableauServerConnection(tableau_config)
        self.connection.sign_in()

    def get_dashboard_views(self, workbook_name):
        views_df = get_views_dataframe(self.connection)
        return views_df[views_df['workbookName'] == workbook_name]

    def export_view_with_refresh(self, view_content_url, filters_list, output_path="output", file_format="png"):
        os.makedirs(output_path, exist_ok=True)

        # Omit /t/<site> if site_url is empty (default site)
        site_url = tableau_config['site_url']
        site_part = f"/t/{site_url}" if site_url else ""

        for filter_dict in filters_list:
            filter_name = "_".join([f"{key}_{value.replace(',', '_')}" for key, value in filter_dict.items()])
            file_name = f"{filter_name}.{file_format}"
            file_path = os.path.join(output_path, file_name)

            # Encode filters
            filter_params = "&".join([f"{urllib.parse.quote_plus(k)}={urllib.parse.quote_plus(v)}" for k, v in filter_dict.items()])
            full_url = f"{tableau_config['server']}{site_part}/views/{view_content_url}.{file_format}?:refresh=yes&{filter_params}"

            print(f"Requesting URL: {full_url}")

            response = requests.get(full_url, headers=self.connection.auth_headers)

            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(response.content)
                print(f"Exported image to {file_path}")
            else:
                print(f"Failed for {filter_dict} | Status: {response.status_code} | Message: {response.text}")

    def sign_out(self):
        self.connection.sign_out()


if __name__ == "__main__":
    exporter = TableauImageExporterWithRefresh()

    workbook_name = "Sample Workbook"

    filters_list = [
        {"Region": "North"},
        {"Region": "South"},
        {"Region": "North,South"},
        {"Region": "East,West", "Category": "Office Supplies"},
    ]

    views = exporter.get_dashboard_views(workbook_name)

    for _, view in views.iterrows():
        exporter.export_view_with_refresh(view_content_url=view['contentUrl'], filters_list=filters_list)

    exporter.sign_out()
