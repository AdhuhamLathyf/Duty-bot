import requests
import schedule
import time
from datetime import datetime, timedelta
from openpyxl import load_workbook

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
TELEGRAM_TOKEN = "8430077568:AAEE2LBikDWtrx8j1iZvgIckXNlJl3xnGmA"
GROUP_CHAT_ID  = "-5118811032"
EXCEL_FILE     = "roster.xlsx"   # your Excel file in the same folder
SEND_TIME      = "21:00"         # 9 PM every night

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
#  STEP 3 — Send to Telegram group
# ─────────────────────────────────────────────
def send_to_telegram(message):
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": GROUP_CHAT_ID,
        "text":    message
    }
    response = requests.post(url, json=payload)
    result   = response.json()

    if result.get("ok"):
        print(f"✅ Sent successfully at {datetime.now().strftime('%H:%M:%S')}")
    else:
        print(f"❌ Failed: {result}")


# ─────────────────────────────────────────────
#  STEP 4 — Daily scheduled job
# ─────────────────────────────────────────────
def daily_job():
    print(f"⏰ Running at {datetime.now().strftime('%H:%M:%S')}")
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    try:
        roster  = parse_roster(EXCEL_FILE)
        message = build_message(roster, tomorrow)
        print("📋 Preview:\n", message)
        send_to_telegram(message)
    except Exception as e:
        print(f"❌ Error: {e}")


# ─────────────────────────────────────────────
#  STEP 5 — Test immediately
# ─────────────────────────────────────────────
def test_now():
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    roster   = parse_roster(EXCEL_FILE)
    message  = build_message(roster, tomorrow)
    print("📋 Message preview:\n")
    print(message)
    print("\n--- Sending to Telegram now ---")
    send_to_telegram(message)


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🤖 Telegram Duty Bot started. Sending daily at {SEND_TIME}.")
    print("   To test immediately, run:")
    print("   python3 -c 'from telegram_bot import test_now; test_now()'\n")
    schedule.every().day.at(SEND_TIME).do(daily_job)
    while True:
        schedule.run_pending()
        time.sleep(30)
