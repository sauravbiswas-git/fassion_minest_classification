import os
import time
import urllib.parse
import requests
from tableau_api_lib import TableauServerConnection
from tableau_api_lib.utils.querying import get_workbooks_dataframe, get_views_dataframe
from config import tableau_config


class TableauDashboardExporter:
    def __init__(self):
        self.connection = TableauServerConnection(tableau_config)
        self.connection.sign_in()

    def get_dashboard_views(self, workbook_name):
        views_df = get_views_dataframe(self.connection)
        return views_df[views_df['workbookName'] == workbook_name]

    def refresh_workbook_extract(self, workbook_name):
        """Trigger extract refresh for the given workbook."""
        workbooks_df = get_workbooks_dataframe(self.connection)
        workbook = workbooks_df[workbooks_df['name'] == workbook_name]

        if workbook.empty:
            print(f"Workbook '{workbook_name}' not found.")
            return None

        workbook_id = workbook['id'].values[0]
        print(f"Triggering extract refresh for workbook: {workbook_name} (ID: {workbook_id})")

        response = self.connection.refresh_workbook(workbook_id=workbook_id)

        if response.status_code == 202:
            print("Refresh started successfully.")
            return response.json()['job']['id']  # Return job ID to track it
        else:
            print(f"Failed to start refresh. Status: {response.status_code}")
            print(response.content)
            return None

    def wait_for_job_completion(self, job_id, timeout=600):
        """Poll the job status until it completes or times out."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            response = self.connection.query_job(job_id)
            job = response.json()['job']
            job_status = job['status']

            print(f"Job status: {job_status}")

            if job_status in ["Success", "Failed", "Cancelled"]:
                return job_status
            time.sleep(5)

        return "Timeout"

    def export_dashboard_as_images(self, view_id, filters_list, output_path="output"):
        os.makedirs(output_path, exist_ok=True)

        for filter_dict in filters_list:
            # Unique filename
            filter_name = "_".join([
                f"{k}_{v.replace(',', '_')}" for k, v in filter_dict.items()
            ])
            file_name = f"{filter_name}.png"
            file_path = os.path.join(output_path, file_name)

            # Encode filters
            filter_params = "&".join([
                f"vf_{urllib.parse.quote_plus(k)}={urllib.parse.quote_plus(v)}"
                for k, v in filter_dict.items()
            ])

            # Add cache-busting timestamp
            cache_bust = f"cb={int(time.time())}"

            # Build URL
            url = (
                f"{tableau_config['server']}/api/{tableau_config['api_version']}/"
                f"sites/{self.connection.site_id}/views/{view_id}/image?"
                f"{filter_params}&:refresh=yes&:maxAge=0&{cache_bust}"
            )

            print(f"Requesting export: {url}")
            response = requests.get(url, headers=self.connection.auth_headers)

            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(response.content)
                print(f"Saved image: {file_path}")
            else:
                print(f"Failed to export {filter_dict}: {response.status_code} - {response.text}")

    def sign_out(self):
        self.connection.sign_out()
        print("Signed out.")


if __name__ == "__main__":
    exporter = TableauDashboardExporter()

    workbook_name = "Sample Workbook"  # Your workbook name here

    # Step 1: Trigger extract refresh
    job_id = exporter.refresh_workbook_extract(workbook_name)

    if job_id:
        # Step 2: Wait for extract refresh to finish
        final_status = exporter.wait_for_job_completion(job_id)
        if final_status == "Success":
            print("Extract refresh completed successfully!")
        else:
            print(f"Extract refresh finished with status: {final_status}")
    else:
        print("No refresh triggered.")

    # Step 3: Define filters to apply
    filters_list = [
        {"Region": "North"},
        {"Region": "North,South"},
        {"Region": "East,West", "Category": "Technology"},
    ]

    # Step 4: Export the updated dashboards
    views = exporter.get_dashboard_views(workbook_name)

    for _, view in views.iterrows():
        exporter.export_dashboard_as_images(view_id=view['id'], filters_list=filters_list)

    # Step 5: Sign out
    exporter.sign_out()
                                
