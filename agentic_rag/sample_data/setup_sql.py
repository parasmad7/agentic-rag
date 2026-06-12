"""Create and populate the SQLite sample database with health & fitness data."""

from datetime import date

import sqlalchemy as sa

from agentic_rag.config import SQLITE_DB_PATH

metadata = sa.MetaData()

members = sa.Table(
    "members", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.String, nullable=False),
    sa.Column("email", sa.String, nullable=False),
    sa.Column("phone", sa.String),
    sa.Column("membership_type", sa.String, nullable=False),  # basic | premium | elite
    sa.Column("join_date", sa.Date, nullable=False),
    sa.Column("status", sa.String, nullable=False, default="active"),  # active | inactive | frozen
)

trainers = sa.Table(
    "trainers", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.String, nullable=False),
    sa.Column("email", sa.String, nullable=False),
    sa.Column("specialization", sa.String, nullable=False),
    sa.Column("certification", sa.String, nullable=False),
    sa.Column("hire_date", sa.Date, nullable=False),
    sa.Column("hourly_rate", sa.Float, nullable=False),
)

workout_sessions = sa.Table(
    "workout_sessions", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("member_id", sa.Integer, sa.ForeignKey("members.id")),
    sa.Column("trainer_id", sa.Integer, sa.ForeignKey("trainers.id"), nullable=True),
    sa.Column("session_date", sa.Date, nullable=False),
    sa.Column("workout_type", sa.String, nullable=False),  # strength | cardio | HIIT | yoga | pilates
    sa.Column("duration_min", sa.Integer, nullable=False),
    sa.Column("calories_burned", sa.Integer),
)

memberships = sa.Table(
    "memberships", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("member_id", sa.Integer, sa.ForeignKey("members.id")),
    sa.Column("plan_type", sa.String, nullable=False),  # basic | premium | elite
    sa.Column("start_date", sa.Date, nullable=False),
    sa.Column("end_date", sa.Date, nullable=False),
    sa.Column("monthly_fee", sa.Float, nullable=False),
    sa.Column("status", sa.String, nullable=False),  # active | expired | cancelled
)

classes = sa.Table(
    "classes", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.String, nullable=False),
    sa.Column("trainer_id", sa.Integer, sa.ForeignKey("trainers.id")),
    sa.Column("schedule_day", sa.String, nullable=False),
    sa.Column("time_slot", sa.String, nullable=False),
    sa.Column("max_capacity", sa.Integer, nullable=False),
    sa.Column("current_enrollment", sa.Integer, nullable=False, default=0),
    sa.Column("category", sa.String, nullable=False),  # yoga | HIIT | strength | cardio | pilates
)

body_metrics = sa.Table(
    "body_metrics", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("member_id", sa.Integer, sa.ForeignKey("members.id")),
    sa.Column("recorded_date", sa.Date, nullable=False),
    sa.Column("weight_kg", sa.Float, nullable=False),
    sa.Column("body_fat_pct", sa.Float),
    sa.Column("bmi", sa.Float),
    sa.Column("resting_heart_rate", sa.Integer),
)


def setup():
    SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SQLITE_DB_PATH.exists():
        SQLITE_DB_PATH.unlink()

    engine = sa.create_engine(f"sqlite:///{SQLITE_DB_PATH}")
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(members.insert(), [
            {"id": 1, "name": "Sarah Johnson", "email": "sarah@email.com", "phone": "555-0101", "membership_type": "elite", "join_date": date(2023, 1, 15), "status": "active"},
            {"id": 2, "name": "Mike Chen", "email": "mike@email.com", "phone": "555-0102", "membership_type": "premium", "join_date": date(2023, 3, 20), "status": "active"},
            {"id": 3, "name": "Emma Wilson", "email": "emma@email.com", "phone": "555-0103", "membership_type": "basic", "join_date": date(2023, 6, 1), "status": "active"},
            {"id": 4, "name": "James Rodriguez", "email": "james@email.com", "phone": "555-0104", "membership_type": "premium", "join_date": date(2023, 8, 10), "status": "active"},
            {"id": 5, "name": "Lisa Park", "email": "lisa@email.com", "phone": "555-0105", "membership_type": "elite", "join_date": date(2023, 2, 28), "status": "active"},
            {"id": 6, "name": "David Thompson", "email": "david@email.com", "phone": "555-0106", "membership_type": "basic", "join_date": date(2024, 1, 5), "status": "active"},
            {"id": 7, "name": "Priya Patel", "email": "priya@email.com", "phone": "555-0107", "membership_type": "premium", "join_date": date(2024, 3, 12), "status": "active"},
            {"id": 8, "name": "Ryan O'Brien", "email": "ryan@email.com", "phone": "555-0108", "membership_type": "basic", "join_date": date(2024, 5, 20), "status": "frozen"},
            {"id": 9, "name": "Ana Martinez", "email": "ana@email.com", "phone": "555-0109", "membership_type": "elite", "join_date": date(2024, 7, 1), "status": "active"},
            {"id": 10, "name": "Tom Baker", "email": "tom@email.com", "phone": "555-0110", "membership_type": "premium", "join_date": date(2024, 9, 15), "status": "active"},
            {"id": 11, "name": "Nina Kowalski", "email": "nina@email.com", "phone": "555-0111", "membership_type": "basic", "join_date": date(2024, 11, 1), "status": "inactive"},
            {"id": 12, "name": "Chris Lee", "email": "chris@email.com", "phone": "555-0112", "membership_type": "premium", "join_date": date(2025, 1, 10), "status": "active"},
        ])

        conn.execute(trainers.insert(), [
            {"id": 1, "name": "Marcus Rivera", "email": "marcus@fitgym.com", "specialization": "strength_training", "certification": "NSCA-CSCS", "hire_date": date(2022, 3, 1), "hourly_rate": 75.0},
            {"id": 2, "name": "Yuki Tanaka", "email": "yuki@fitgym.com", "specialization": "yoga", "certification": "RYT-500", "hire_date": date(2022, 6, 15), "hourly_rate": 65.0},
            {"id": 3, "name": "Derek Washington", "email": "derek@fitgym.com", "specialization": "HIIT", "certification": "ACE-CPT", "hire_date": date(2023, 1, 10), "hourly_rate": 70.0},
            {"id": 4, "name": "Sofia Andersson", "email": "sofia@fitgym.com", "specialization": "pilates", "certification": "PMA-CPT", "hire_date": date(2023, 5, 20), "hourly_rate": 65.0},
            {"id": 5, "name": "Kwame Asante", "email": "kwame@fitgym.com", "specialization": "cardio", "certification": "ACSM-EP", "hire_date": date(2023, 9, 1), "hourly_rate": 60.0},
            {"id": 6, "name": "Rachel Kim", "email": "rachel@fitgym.com", "specialization": "nutrition_coaching", "certification": "NASM-CNC", "hire_date": date(2024, 2, 1), "hourly_rate": 70.0},
        ])

        conn.execute(workout_sessions.insert(), [
            {"id": 1, "member_id": 1, "trainer_id": 1, "session_date": date(2025, 1, 6), "workout_type": "strength", "duration_min": 60, "calories_burned": 420},
            {"id": 2, "member_id": 1, "trainer_id": None, "session_date": date(2025, 1, 8), "workout_type": "cardio", "duration_min": 45, "calories_burned": 380},
            {"id": 3, "member_id": 2, "trainer_id": 3, "session_date": date(2025, 1, 7), "workout_type": "HIIT", "duration_min": 30, "calories_burned": 350},
            {"id": 4, "member_id": 3, "trainer_id": None, "session_date": date(2025, 1, 9), "workout_type": "cardio", "duration_min": 40, "calories_burned": 300},
            {"id": 5, "member_id": 4, "trainer_id": 2, "session_date": date(2025, 1, 10), "workout_type": "yoga", "duration_min": 75, "calories_burned": 200},
            {"id": 6, "member_id": 5, "trainer_id": 1, "session_date": date(2025, 1, 6), "workout_type": "strength", "duration_min": 55, "calories_burned": 400},
            {"id": 7, "member_id": 5, "trainer_id": 3, "session_date": date(2025, 1, 8), "workout_type": "HIIT", "duration_min": 30, "calories_burned": 340},
            {"id": 8, "member_id": 6, "trainer_id": None, "session_date": date(2025, 2, 3), "workout_type": "cardio", "duration_min": 30, "calories_burned": 250},
            {"id": 9, "member_id": 7, "trainer_id": 4, "session_date": date(2025, 2, 5), "workout_type": "pilates", "duration_min": 50, "calories_burned": 220},
            {"id": 10, "member_id": 9, "trainer_id": 1, "session_date": date(2025, 2, 10), "workout_type": "strength", "duration_min": 60, "calories_burned": 430},
            {"id": 11, "member_id": 10, "trainer_id": 5, "session_date": date(2025, 2, 12), "workout_type": "cardio", "duration_min": 50, "calories_burned": 410},
            {"id": 12, "member_id": 2, "trainer_id": 3, "session_date": date(2025, 2, 14), "workout_type": "HIIT", "duration_min": 30, "calories_burned": 360},
            {"id": 13, "member_id": 1, "trainer_id": 1, "session_date": date(2025, 3, 3), "workout_type": "strength", "duration_min": 65, "calories_burned": 450},
            {"id": 14, "member_id": 12, "trainer_id": 2, "session_date": date(2025, 3, 5), "workout_type": "yoga", "duration_min": 60, "calories_burned": 180},
            {"id": 15, "member_id": 5, "trainer_id": None, "session_date": date(2025, 3, 10), "workout_type": "cardio", "duration_min": 45, "calories_burned": 370},
        ])

        conn.execute(memberships.insert(), [
            {"id": 1, "member_id": 1, "plan_type": "elite", "start_date": date(2024, 1, 15), "end_date": date(2025, 1, 14), "monthly_fee": 149.99, "status": "expired"},
            {"id": 2, "member_id": 1, "plan_type": "elite", "start_date": date(2025, 1, 15), "end_date": date(2026, 1, 14), "monthly_fee": 159.99, "status": "active"},
            {"id": 3, "member_id": 2, "plan_type": "premium", "start_date": date(2024, 3, 20), "end_date": date(2025, 3, 19), "monthly_fee": 99.99, "status": "expired"},
            {"id": 4, "member_id": 2, "plan_type": "premium", "start_date": date(2025, 3, 20), "end_date": date(2026, 3, 19), "monthly_fee": 109.99, "status": "active"},
            {"id": 5, "member_id": 3, "plan_type": "basic", "start_date": date(2024, 6, 1), "end_date": date(2025, 5, 31), "monthly_fee": 49.99, "status": "active"},
            {"id": 6, "member_id": 4, "plan_type": "premium", "start_date": date(2024, 8, 10), "end_date": date(2025, 8, 9), "monthly_fee": 99.99, "status": "active"},
            {"id": 7, "member_id": 5, "plan_type": "elite", "start_date": date(2024, 2, 28), "end_date": date(2025, 2, 27), "monthly_fee": 149.99, "status": "expired"},
            {"id": 8, "member_id": 5, "plan_type": "elite", "start_date": date(2025, 2, 28), "end_date": date(2026, 2, 27), "monthly_fee": 159.99, "status": "active"},
            {"id": 9, "member_id": 6, "plan_type": "basic", "start_date": date(2025, 1, 5), "end_date": date(2026, 1, 4), "monthly_fee": 49.99, "status": "active"},
            {"id": 10, "member_id": 7, "plan_type": "premium", "start_date": date(2025, 3, 12), "end_date": date(2026, 3, 11), "monthly_fee": 109.99, "status": "active"},
            {"id": 11, "member_id": 8, "plan_type": "basic", "start_date": date(2024, 5, 20), "end_date": date(2025, 5, 19), "monthly_fee": 49.99, "status": "active"},
            {"id": 12, "member_id": 11, "plan_type": "basic", "start_date": date(2024, 11, 1), "end_date": date(2025, 4, 30), "monthly_fee": 49.99, "status": "cancelled"},
        ])

        conn.execute(classes.insert(), [
            {"id": 1, "name": "Power Yoga Flow", "trainer_id": 2, "schedule_day": "Monday", "time_slot": "07:00", "max_capacity": 25, "current_enrollment": 22, "category": "yoga"},
            {"id": 2, "name": "HIIT Blast", "trainer_id": 3, "schedule_day": "Monday", "time_slot": "18:00", "max_capacity": 20, "current_enrollment": 20, "category": "HIIT"},
            {"id": 3, "name": "Strength Foundations", "trainer_id": 1, "schedule_day": "Tuesday", "time_slot": "09:00", "max_capacity": 15, "current_enrollment": 12, "category": "strength"},
            {"id": 4, "name": "Spin & Burn", "trainer_id": 5, "schedule_day": "Wednesday", "time_slot": "06:30", "max_capacity": 30, "current_enrollment": 28, "category": "cardio"},
            {"id": 5, "name": "Pilates Core", "trainer_id": 4, "schedule_day": "Wednesday", "time_slot": "12:00", "max_capacity": 20, "current_enrollment": 15, "category": "pilates"},
            {"id": 6, "name": "Tabata Thursday", "trainer_id": 3, "schedule_day": "Thursday", "time_slot": "17:30", "max_capacity": 20, "current_enrollment": 19, "category": "HIIT"},
            {"id": 7, "name": "Restorative Yoga", "trainer_id": 2, "schedule_day": "Friday", "time_slot": "10:00", "max_capacity": 25, "current_enrollment": 18, "category": "yoga"},
            {"id": 8, "name": "Weekend Warrior HIIT", "trainer_id": 3, "schedule_day": "Saturday", "time_slot": "09:00", "max_capacity": 25, "current_enrollment": 25, "category": "HIIT"},
        ])

        conn.execute(body_metrics.insert(), [
            {"id": 1, "member_id": 1, "recorded_date": date(2025, 1, 5), "weight_kg": 72.5, "body_fat_pct": 24.0, "bmi": 25.1, "resting_heart_rate": 68},
            {"id": 2, "member_id": 1, "recorded_date": date(2025, 2, 5), "weight_kg": 71.0, "body_fat_pct": 23.2, "bmi": 24.6, "resting_heart_rate": 66},
            {"id": 3, "member_id": 1, "recorded_date": date(2025, 3, 5), "weight_kg": 69.8, "body_fat_pct": 22.1, "bmi": 24.2, "resting_heart_rate": 64},
            {"id": 4, "member_id": 2, "recorded_date": date(2025, 1, 10), "weight_kg": 88.0, "body_fat_pct": 28.5, "bmi": 28.3, "resting_heart_rate": 74},
            {"id": 5, "member_id": 2, "recorded_date": date(2025, 2, 10), "weight_kg": 86.5, "body_fat_pct": 27.8, "bmi": 27.8, "resting_heart_rate": 72},
            {"id": 6, "member_id": 2, "recorded_date": date(2025, 3, 10), "weight_kg": 85.2, "body_fat_pct": 26.9, "bmi": 27.4, "resting_heart_rate": 70},
            {"id": 7, "member_id": 3, "recorded_date": date(2025, 1, 15), "weight_kg": 65.0, "body_fat_pct": 30.2, "bmi": 24.2, "resting_heart_rate": 72},
            {"id": 8, "member_id": 3, "recorded_date": date(2025, 3, 15), "weight_kg": 64.0, "body_fat_pct": 29.0, "bmi": 23.8, "resting_heart_rate": 70},
            {"id": 9, "member_id": 4, "recorded_date": date(2025, 1, 20), "weight_kg": 80.0, "body_fat_pct": 22.0, "bmi": 25.0, "resting_heart_rate": 62},
            {"id": 10, "member_id": 4, "recorded_date": date(2025, 3, 20), "weight_kg": 79.0, "body_fat_pct": 20.5, "bmi": 24.7, "resting_heart_rate": 60},
            {"id": 11, "member_id": 5, "recorded_date": date(2025, 1, 8), "weight_kg": 58.5, "body_fat_pct": 20.0, "bmi": 21.5, "resting_heart_rate": 58},
            {"id": 12, "member_id": 5, "recorded_date": date(2025, 2, 8), "weight_kg": 58.0, "body_fat_pct": 19.5, "bmi": 21.3, "resting_heart_rate": 57},
            {"id": 13, "member_id": 5, "recorded_date": date(2025, 3, 8), "weight_kg": 57.5, "body_fat_pct": 19.0, "bmi": 21.1, "resting_heart_rate": 56},
            {"id": 14, "member_id": 9, "recorded_date": date(2025, 1, 25), "weight_kg": 68.0, "body_fat_pct": 26.0, "bmi": 24.5, "resting_heart_rate": 70},
            {"id": 15, "member_id": 9, "recorded_date": date(2025, 3, 25), "weight_kg": 66.5, "body_fat_pct": 24.5, "bmi": 24.0, "resting_heart_rate": 66},
            {"id": 16, "member_id": 10, "recorded_date": date(2025, 1, 30), "weight_kg": 95.0, "body_fat_pct": 32.0, "bmi": 30.1, "resting_heart_rate": 78},
            {"id": 17, "member_id": 10, "recorded_date": date(2025, 3, 30), "weight_kg": 92.0, "body_fat_pct": 30.5, "bmi": 29.1, "resting_heart_rate": 74},
            {"id": 18, "member_id": 12, "recorded_date": date(2025, 1, 15), "weight_kg": 76.0, "body_fat_pct": 25.0, "bmi": 24.8, "resting_heart_rate": 70},
            {"id": 19, "member_id": 12, "recorded_date": date(2025, 3, 15), "weight_kg": 74.5, "body_fat_pct": 23.8, "bmi": 24.3, "resting_heart_rate": 67},
            {"id": 20, "member_id": 7, "recorded_date": date(2025, 3, 20), "weight_kg": 62.0, "body_fat_pct": 23.0, "bmi": 22.8, "resting_heart_rate": 64},
        ])

    print(f"SQLite database created at {SQLITE_DB_PATH}")
    print("Tables: members, trainers, workout_sessions, memberships, classes, body_metrics")


if __name__ == "__main__":
    setup()
