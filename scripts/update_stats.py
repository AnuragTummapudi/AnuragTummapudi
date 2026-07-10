import os, requests, subprocess
from pathlib import Path

USERNAME = "AnuragTummapudi"
TOKEN = os.environ["GH_TOKEN"]
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}

def rest(path, params=None):
    r = requests.get("https://api.github.com" + path, headers=HEADERS, params=params, timeout=60)
    r.raise_for_status()
    return r.json()

user = rest(f"/users/{USERNAME}")
repos, page = [], 1
while True:
    batch = rest(f"/users/{USERNAME}/repos", {"per_page":100,"page":page,"type":"owner"})
    if not batch: break
    repos += batch; page += 1

stars = sum(r["stargazers_count"] for r in repos)
owned = [r for r in repos if not r["fork"]]

# All commits authored by the GitHub user across public GitHub.
commits = rest("/search/commits", {"q":f"author:{USERNAME}","per_page":1})["total_count"]

query = """query($login:String!){
  user(login:$login){
    repositoriesContributedTo(first:1, contributionTypes:[COMMIT,ISSUE,PULL_REQUEST,REPOSITORY]){totalCount}
  }
}"""
g = requests.post("https://api.github.com/graphql", headers=HEADERS,
                  json={"query":query,"variables":{"login":USERNAME}}, timeout=60)
g.raise_for_status()
contributed = g.json()["data"]["user"]["repositoriesContributedTo"]["totalCount"]

# Current tracked source lines across owned, non-fork public repositories.
total_lines = 0
tmp = Path(".stats-repos"); tmp.mkdir(exist_ok=True)
for repo in owned:
    d = tmp / repo["name"]
    subprocess.run(["git","clone","--depth","1","--quiet",repo["clone_url"],str(d)], check=False)
    if d.exists():
        p = subprocess.run(["git","-C",str(d),"ls-files"], capture_output=True, text=True)
        for rel in p.stdout.splitlines():
            f = d / rel
            try:
                if f.is_file() and f.stat().st_size < 2_000_000:
                    data = f.read_bytes()
                    if b"\0" not in data:
                        total_lines += data.count(b"\n")
            except Exception:
                pass

tpl = Path("assets/stats-template.svg").read_text()
values = {
    "{REPOS}": str(user["public_repos"]),
    "{CONTRIBUTED}": str(contributed),
    "{STARS}": str(stars),
    "{FOLLOWERS}": str(user["followers"]),
    "{COMMITS}": f"{commits:,}",
    "{LINES}": f"{total_lines:,}",
}
for k,v in values.items(): tpl = tpl.replace(k,v)
Path("assets/stats.svg").write_text(tpl)
