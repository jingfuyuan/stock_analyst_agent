# app/scripts/run_daily_brief.py
from datetime import date
from app.agents.daily_brief import run_daily_brief

if __name__ == "__main__":
    USER_ID = 1  # adjust as needed
    brief = run_daily_brief(USER_ID, target_date=date.today())
    print("Generated brief:")
    print(brief.text)
    if brief.audio_path:
        print(f"Audio saved at: {brief.audio_path}")
