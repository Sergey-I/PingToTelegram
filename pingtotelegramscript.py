import requests
import time
import os

# 🔐 Use environment variables in production
BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
CHAT_ID = os.getenv("CHAT_ID") or "YOUR_CHAT_ID"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def classify_speed(ms):
    if ms is None:
        return "❓ unknown"
    elif ms < 800:
        return "⚡ fast"
    elif ms < 2000:
        return "🟢 ok"
    elif ms < 4000:
        return "⚠️ slow"
    else:
        return "🐢 very slow"

def check_website_in_russia(domain):
    message_lines = []
    message_lines.append(f"🌍 *Website check (RU)*\n`{domain}`\n")

    start_url = "https://api.globalping.io/v1/measurements"
    payload = {
        "type": "http",
        "target": domain,
        "locations": [
            {"country": "RU", "limit": 7},
            {"continent": "EU", "limit": 2}
        ],
        "measurementOptions": {
            "protocol": "HTTPS"
        }
    }

    try:
        response = requests.post(start_url, json=payload)
        response.raise_for_status()
        measurement_id = response.json().get("id")
    except requests.exceptions.RequestException as e:
        send_telegram(f"❌ Failed to start measurement:\n`{e}`")
        return

    result_url = f"https://api.globalping.io/v1/measurements/{measurement_id}"

    # wait for results
    while True:
        try:
            res = requests.get(result_url)
            res.raise_for_status()
            data = res.json()

            if data.get("status") != "in-progress":
                break

            time.sleep(2)

        except requests.exceptions.RequestException as e:
            send_telegram(f"❌ Failed to fetch results:\n`{e}`")
            return

    # parse results
    results = data.get("results", [])

    if not results:
        send_telegram("⚠️ No probes returned results.")
        return

    success_count = 0

    for probe in results:
        location = probe.get("probe", {}).get("city", "Unknown")
        network = probe.get("probe", {}).get("network", "Unknown")

        probe_result = probe.get("result", {})
        timings = probe_result.get("timings", {})
        total_time = timings.get("total") or 0

        speed = classify_speed(total_time)       
        
        status_code = probe_result.get("statusCode")

        if status_code:
           speed = classify_speed(total_time)

           if total_time:
              time_str = f"{total_time} ms"
           else:
              time_str = "no data"

           if 200 <= status_code < 400:
              status = "✅ OK"
              success_count += 1
           else:
              status = "❌ ERROR"

           message_lines.append(
              f"📍 *{location}* ({network})\n"
              f"   HTTP {status_code} → {status}\n"
              f"   ⏱ {time_str} → {speed}"
            )
        else:
            error_msg = probe_result.get("error", "Connection failed")
            message_lines.append(
                f"📍 *{location}* ({network})\n"
                f"   ❌ {error_msg}"
            )

    # summary
    slow_count = sum(
       1 for probe in results
       if (probe.get("result", {}).get("timings", {}).get("total") or 0) > 3000
       )
    message_lines.append("\n---")
    message_lines.append(f"✔️ Success: {success_count}/{len(results)}")

    # send final message
    final_message = "\n".join(message_lines)
    if success_count == 0:
       send_telegram("🚫 Website DOWN in Russia")
    elif slow_count >= len(results) // 2:
       send_telegram("🐢 Website is VERY SLOW in Russia")
    else:
       send_telegram(final_message)


if __name__ == "__main__":
    check_website_in_russia("www.internetaddicts.ru")
