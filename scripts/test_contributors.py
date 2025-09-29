import requests, os

ORG = "YOUR_ORG"   # replace with your org name
TOKEN = os.getenv("GITHUB_TOKEN")
headers = {"Authorization": f"token {TOKEN}"}

# Get repos
repos = requests.get(f"https://api.github.com/orgs/{ORG}/repos?per_page=50", headers=headers).json()

contributors = set()
for repo in repos:
    name = repo["name"]
    url = f"https://api.github.com/repos/{ORG}/{name}/contributors?per_page=50"
    resp = requests.get(url, headers=headers).json()
    for c in resp:
        if "login" in c:
            contributors.add(c["login"])

print("Contributors found:", contributors if contributors else "None")