import requests, os, re, yaml

ORG = "SUPSI-DEASS-CPPS"
TOKEN = os.getenv("GITHUB_TOKEN")
headers = {"Authorization": f"token {TOKEN}"}

def find_orcid(text):
    match = re.search(r"\b\d{4}-\d{4}-\d{4}-\d{3}[0-9X]\b", text or "")
    return match.group(0) if match else None

# Step 1: Collect contributors from GitHub
repos = requests.get(f"https://api.github.com/orgs/{ORG}/repos?per_page=100", headers=headers).json()
contributors = {}

for repo in repos:
    name = repo["name"]
    url = f"https://api.github.com/repos/{ORG}/{name}/contributors?per_page=100"
    resp = requests.get(url, headers=headers).json()
    for c in resp:
        if "login" in c:
            contributors[c["login"]] = {"avatar": c["avatar_url"], "orcid": None}

# Step 2: Enrich with ORCID from GitHub profiles
for login in contributors.keys():
    profile = requests.get(f"https://api.github.com/users/{login}", headers=headers).json()
    bio = profile.get("bio", "")
    blog = profile.get("blog", "")
    orcid = find_orcid(bio) or find_orcid(blog)
    if orcid:
        contributors[login]["orcid"] = orcid

# Step 3: Enrich with ORCID from CITATION.cff
for repo in repos:
    name = repo["name"]
    citation_url = f"https://raw.githubusercontent.com/{ORG}/{name}/HEAD/CITATION.cff"
    r = requests.get(citation_url)
    if r.status_code == 200:
        try:
            citation = yaml.safe_load(r.text)
            for author in citation.get("authors", []):
                if "orcid" in author:
                    # Try to match by GitHub username if listed in 'alias' or 'email'
                    # Otherwise, just add a synthetic entry
                    matched = False
                    for login in contributors:
                        if author.get("email") and author["email"].lower() in str(profile).lower():
                            contributors[login]["orcid"] = author["orcid"]
                            matched = True
                    if not matched:
                        # Add a placeholder entry for non-GitHub authors
                        contributors[author.get("family-names","unknown")] = {
                            "avatar": "https://avatars.githubusercontent.com/u/0?v=4",
                            "orcid": author["orcid"]
                        }
        except Exception:
            pass

# Step 4: Build avatar grid
avatars = " ".join(
    [f'<a href="https://github.com/{login}"><img src="{data["avatar"]}&s=64" width="48" height="48" style="border-radius:50%;margin:2px;" alt="{login}" /></a>'
     for login, data in sorted(contributors.items())]
)

# Step 5: Build text list with ORCID
text_list = "\n".join(
    [f'- [@{login}](https://github.com/{login})' + (f' · [ORCID](https://orcid.org/{data["orcid"]})' if data["orcid"] else "")
     for login, data in sorted(contributors.items())]
)

# Step 6: Update README
readme_path = ".github/profile/README.md"
with open(readme_path, "r", encoding="utf-8") as f:
    content = f.read()

new_content = re.sub(
    r"(<!-- CONTRIBUTORS START -->)(.*?)(<!-- CONTRIBUTORS END -->)",
    f"\\1\n<p>{avatars}</p>\n\n{text_list}\n\\3",
    content,
    flags=re.S
)

with open(readme_path, "w", encoding="utf-8") as f:
    f.write(new_content)