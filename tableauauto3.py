import xml.etree.ElementTree as ET

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
            # If JSON returned
            self.auth_token = response.json()['credentials']['token']
            self.session_id = response.cookies.get('workgroup_session_id')
            print("Signed in via JSON.")
        except ValueError:
            # Fallback: parse XML
            root = ET.fromstring(response.text)
            self.auth_token = root.find(".//t:credentials", {"t": "http://tableau.com/api"}).attrib['token']
            self.session_id = response.cookies.get('workgroup_session_id')
            print("Signed in via XML.")
    else:
        raise Exception(f"Failed to sign in: {response.status_code} - {response.text}")
        
