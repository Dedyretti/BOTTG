from sqlalchemy import create_engine



engine = create_engine("sqlite:///attendance_bot/database/attendance_bot.db", echo=True)
