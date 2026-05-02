import requests
import time
from datetime import datetime, timedelta
from openpyxl import load_workbook

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
TELEGRAM_TOKEN = "8430077568:AAEE2LBikDWtrx8j1iZvgIckXNlJl3xnGmA"
GROUP_CHAT_ID  = "-5118811032"
EXCEL_FILE     = "roster.xlsx"
SEND_HOUR      = 19   # 9 PM — change this number only
SEND_MINUTE    = 35

# ─────────────────────────────────────────────
#  STEP 1 — Parse roster from Excel
# ─────────────────────────────────────────────
def parse_roster(filepath):
    wb = load_workbook(filepath, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    roster = {}
    i = 0

    while i < len(rows):
        row = rows[i]
        month_val = row[2] if len(row) > 2 else None

        if month_val in ("APRIL", "MAY"):
            month_row = rows[i]
            date_row  = rows[i + 1]
            i += 3

            col_dates = {}
            current_month = None
            year = 2026

            for col_idx in range(len(date_row)):
                if col_idx < len(month_row) and month_row[col_idx] in ("APRIL", "MAY"):
                    current_month = 4 if month_row[col_idx] == "APRIL" else 5
                date_val = date_row[col_idx]
                if date_val and isinstance(date_val, str) and date_val[:-2].isdigit() and current_month:
                    col_dates[col_idx] = datetime(year, current_month, int(date_val[:-2]))

            while i < len(rows):
                staff_row = rows[i]
                if staff_row[0] is None and staff_row[1] is None:
                    break
                if staff_row[1] == "NAME":
                    break
                name = staff_row[1]
                if name:
                    name = name.strip()
                    for col_idx, date in col_dates.items():
                        shift = staff_row[col_idx] if col_idx < len(staff_row) else None
                        if shift is not None:
                            if date not in roster:
                                roster[date] = {}
                            roster[date][name] = str(shift).strip()
                i += 1
        else:
            i += 1

    return roster


# ─────────────────────────────────────────────
#  STEP 2 — Build the message
# ─────────────────────────────────────────────
def build_message(roster, target_date):
    day_name = target_date.strftime("%A")
    date_str = target_date.strftime("%-d %B")

    shifts  = {}
    offs    = []
    leaves  = []
    travels = []

    day_data = roster.get(target_date, {})
    if not day_data:
        return f"⚠️ No roster data found for {day_name}, {date_str}."

    for name, shift in sorted(day_data.items()):
        if shift == "OFF":
            offs.append(name)
        elif shift == "ANNUAL LEAVE":
            leaves.append(name)
        elif shift == "DUTY TRAVEL":
            travels.append(name)
        else:
            shifts.setdefault(shift, []).append(name)

    emoji_map = {
        "0600-1400": "🌅",
        "1200-2000": "🌤",
        "1400-2200": "🌙",
    }

    lines = [f"👋 Hey team! Tomorrow's duty ({day_name}, {date_str}):\n"]

    for shift_time in sorted(shifts.keys()):
        icon  = emoji_map.get(shift_time, "⏰")
        names = ", ".join(shifts[shift_time])
        lines.append(f"{icon} {shift_time} → {names}")

    if offs:
        lines.append(f"\n🏖 OFF → {', '.join(offs)}")
    if leaves:
        lines.append(f"✈️ Annual Leave → {', '.join(leaves)}")
    if travels:
        lines.append(f"🚗 Duty Travel → {', '.join(travels)}")

    lines.append("\nGood luck everyone! 💪")
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  STEP 3 — Send to Telegram
# ─────────────────────────────────────────────
def send_to_telegram(message):
    print(f"📤 Sending message to Telegram...")
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": GROUP_CHAT_ID,
        "text":    message
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"📡 Response status: {response.status_code}")
        print(f"📡 Response body: {response.text}")
        result = response.json()
        if result.get("ok"):
            print(f"✅ Sent successfully!")
        else:
            print(f"❌ Failed: {result}")
    except Exception as e:
        print(f"❌ Exception while sending: {e}")


# ─────────────────────────────────────────────
#  STEP 4 — Daily job
# ─────────────────────────────────────────────
def daily_job():
    print(f"\n⏰ Triggered at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    print(f"📅 Building schedule for: {tomorrow.strftime('%A, %d %B')}")
    try:
        roster  = parse_roster(EXCEL_FILE)
        print(f"✅ Roster parsed, {len(roster)} days found")
        message = build_message(roster, tomorrow)
        print(f"📋 Message built:\n{message}\n")
        send_to_telegram(message)
    except Exception as e:
        print(f"❌ Error in daily_job: {e}")
        import traceback
        traceback.print_exc()


# ─────────────────────────────────────────────
#  MAIN — simple loop, no schedule library
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🤖 Telegram Duty Bot started at {datetime.now().strftime('%H:%M:%S')}")
    print(f"📅 Will send daily at {SEND_HOUR:02d}:{SEND_MINUTE:02d}\n")

    sent_today = False

    while True:
        now = datetime.now()

        # Reset sent flag at midnight
        if now.hour == 0 and now.minute == 0:
            sent_today = False

        # Check if it's time to send
        if now.hour == SEND_HOUR and now.minute == SEND_MINUTE and not sent_today:
            print(f"🔔 It's {SEND_HOUR:02d}:{SEND_MINUTE:02d} — running daily job!")
            daily_job()
            sent_today = True

        # Log every minute so we know bot is alive
        if now.second < 10:
            print(f"💓 Bot alive — {now.strftime('%H:%M')} (waiting for {SEND_HOUR:02d}:{SEND_MINUTE:02d})")

        time.sleep(10)
