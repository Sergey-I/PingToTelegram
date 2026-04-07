import requests
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta, timezone



BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
CHAT_ID = os.getenv("CHAT_ID") or "YOUR_CHAT_ID"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# -------------------------
# Fetch data
# -------------------------
def fetch_data(domain):
   since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    url = f"{SUPABASE_URL}/rest/v1/checks?domain=eq.{domain}&created_at=gte.{since}&select=created_at,avgtime,region&order=created_at.asc"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()

# -------------------------
# Get users
# -------------------------
def get_all_users():
    url = f"{SUPABASE_URL}/rest/v1/users?select=chat_id"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    res = requests.get(url, headers=headers)
    return [u["chat_id"] for u in res.json()]

# -------------------------
# Build chart
# -------------------------
def build_chart(domain):
    data = fetch_data(domain)

    if not data:
        print("No data")
        return None

    df = pd.DataFrame(data)
    df["created_at"] = pd.to_datetime(df["created_at"])

    # daily aggregation
    df["date"] = df["created_at"].dt.date
    df = df.groupby(["date", "region"])["avg_time"].mean().reset_index()

    ru = df[df["region"] == "ru"]
    not_ru = df[df["region"] == "not_ru"]

    plt.figure()

    plt.plot(ru["date"], ru["avg_time"], label="RU")
    plt.plot(not_ru["date"], not_ru["avg_time"], label="NOT_RU")

    plt.xlabel("Date")
    plt.ylabel("Latency (ms)")
    plt.title(f"Latency (7 days): {domain}")
    plt.legend()

    plt.xticks(rotation=45)
    plt.tight_layout()

    filename = "latency_chart.png"
    plt.savefig(filename)
    plt.close()

    return filename

# -------------------------
# Send image to Telegram
# -------------------------
def send_photo(chat_id, file_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    with open(file_path, "rb") as photo:
        requests.post(url, data={"chat_id": chat_id}, files={"photo": photo})

# -------------------------
# Broadcast chart
# -------------------------
def broadcast_chart(file_path):
    users = get_all_users()

    for chat_id in users:
        try:
            send_photo(chat_id, file_path)
        except Exception as e:
            print(f"Failed for {chat_id}: {e}")

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    domain = "www.internetaddicts.ru"

    chart = build_chart(domain)

    if chart:
        broadcast_chart(chart)
