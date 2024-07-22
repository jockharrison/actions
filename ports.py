import requests
from requests.auth import HTTPBasicAuth

# Replace with your Artifactory details
ARTIFACTORY_URL = 'https://cse-space-artifactory-vir.infnonprod.dowjones.io/artifactory'
API_KEY = 'OPIUHB87BI67F685DEI56RFO78GP89GH[98H[9897T6857TOIY'
USERNAME = 'admin'

# Custom API endpoint for repository port mappings
PORT_MAPPING_URL = 'https://cse-space-artifactory-vir.infnonprod.dowjones.io/custom-api/repository-ports'

# Function to get the list of repositories
def get_repositories():
    url = f'{ARTIFACTORY_URL}/api/repositories'
    response = requests.get(url, auth=HTTPBasicAuth(USERNAME, API_KEY))
    response.raise_for_status()
    return response.json()

# Function to get repository port mappings
def get_repository_ports():
    response = requests.get(PORT_MAPPING_URL, auth=HTTPBasicAuth(USERNAME, API_KEY))
    response.raise_for_status()
    return response.json()

# Main function
def main():
    repos = get_repositories()
    repo_ports = get_repository_ports()

    for repo in repos:
        repo_key = repo['key']
        port = repo_ports.get(repo_key, 'Unknown port')
        print(f"Repository Key: {repo_key}")
        print(f"Port: {port}")
        print()

if __name__ == "__main__":
    main()
