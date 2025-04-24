# After receiving the auth token from XML or JSON:
headers = {"X-Tableau-Auth": self.auth_token}

# Make an authenticated request to a lightweight endpoint
me_url = f"{self.server}/api/{self.api_version}/me"
response = requests.get(me_url, headers=headers)

# Grab session cookie from response
self.session_id = response.cookies.get('workgroup_session_id')
