import os
import json
import base64
import requests
import time
import threading

# =============================
# CONFIG
# =============================

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")

BRANCH = "main"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

# =============================
# CACHE
# =============================

cache = {}
sha_cache = {}

push_queue = set()

last_push = 0
PUSH_DELAY = 5

lock = threading.Lock()

# =============================
# URL
# =============================

def github_url(file):

    return f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file}"

# =============================
# LOAD
# =============================

def load_json(file):

    with lock:

        if file in cache:
            return cache[file]

        r = requests.get(github_url(file), headers=HEADERS)

        if r.status_code != 200:

            cache[file] = {}
            return {}

        data = r.json()

        sha_cache[file] = data["sha"]

        decoded = base64.b64decode(data["content"]).decode()

        parsed = json.loads(decoded)

        cache[file] = parsed

        return parsed

# =============================
# SAVE
# =============================

def save_json(file, data):

    with lock:

        cache[file] = data
        push_queue.add(file)

    schedule_push()

# =============================
# PUSH SCHEDULER
# =============================

def schedule_push():

    global last_push

    now = time.time()

    if now - last_push < PUSH_DELAY:
        return

    last_push = now

    thread = threading.Thread(target=push_all)
    thread.start()

# =============================
# PUSH ALL
# =============================

def push_all():

    with lock:

        files = list(push_queue)
        push_queue.clear()

    for file in files:

        try:
            push_file(file)
        except Exception as e:
            print("GitHub push error:", e)

# =============================
# PUSH FILE
# =============================

def push_file(file):

    content = json.dumps(cache[file], ensure_ascii=False, indent=4)

    encoded = base64.b64encode(content.encode()).decode()

    data = {
        "message": f"update {file}",
        "content": encoded,
        "branch": BRANCH
    }

    if file in sha_cache:
        data["sha"] = sha_cache[file]

    r = requests.put(
        github_url(file),
        headers=HEADERS,
        json=data
    )

    if r.status_code in (200, 201):

        sha_cache[file] = r.json()["content"]["sha"]

    else:


        print("GitHub error:", r.text)
