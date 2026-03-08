import os
import requests
import base64

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPO")
BRANCH = "main"

def push_json(file_path):

    with open(file_path, "rb") as f:
        content = f.read()

    encoded = base64.b64encode(content).decode()

    filename = os.path.basename(file_path)

    url = f"https://api.github.com/repos/{REPO}/contents/{filename}"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}"
    }

    # получаем sha файла
    r = requests.get(url, headers=headers)

    sha = None
    if r.status_code == 200:
        sha = r.json()["sha"]

    data = {
        "message": f"update {filename}",
        "content": encoded,
        "branch": BRANCH
    }

    if sha:
        data["sha"] = sha

    requests.put(url, headers=headers, json=data)