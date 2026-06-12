"""Populate MongoDB with health & fitness sample collections."""

from datetime import datetime

from pymongo import MongoClient

from agentic_rag.config import MONGO_DB_NAME, MONGO_URI


def setup():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]

    db.nutrition_logs.drop()
    db.trainer_reviews.drop()
    db.health_assessments.drop()

    db.nutrition_logs.insert_many([
        {
            "member_id": 1,
            "member_name": "Sarah Johnson",
            "date": datetime(2025, 3, 5),
            "meals": [
                {"meal_type": "breakfast", "description": "Greek yogurt with berries and granola", "calories": 350, "protein_g": 22, "carbs_g": 45, "fat_g": 10},
                {"meal_type": "lunch", "description": "Grilled chicken salad with quinoa", "calories": 520, "protein_g": 42, "carbs_g": 38, "fat_g": 18},
                {"meal_type": "dinner", "description": "Salmon with roasted vegetables and brown rice", "calories": 620, "protein_g": 38, "carbs_g": 52, "fat_g": 22},
                {"meal_type": "snack", "description": "Protein shake with banana", "calories": 280, "protein_g": 30, "carbs_g": 32, "fat_g": 5},
            ],
            "daily_totals": {"calories": 1770, "protein_g": 132, "carbs_g": 167, "fat_g": 55},
            "water_liters": 2.5,
            "notes": "Hit protein target. Felt energized during evening workout.",
        },
        {
            "member_id": 2,
            "member_name": "Mike Chen",
            "date": datetime(2025, 3, 7),
            "meals": [
                {"meal_type": "breakfast", "description": "Oatmeal with protein powder and almonds", "calories": 450, "protein_g": 30, "carbs_g": 55, "fat_g": 14},
                {"meal_type": "lunch", "description": "Turkey wrap with avocado", "calories": 580, "protein_g": 35, "carbs_g": 48, "fat_g": 25},
                {"meal_type": "dinner", "description": "Steak with sweet potato and broccoli", "calories": 700, "protein_g": 48, "carbs_g": 45, "fat_g": 30},
                {"meal_type": "snack", "description": "Trail mix and protein bar", "calories": 420, "protein_g": 18, "carbs_g": 52, "fat_g": 20},
            ],
            "daily_totals": {"calories": 2150, "protein_g": 131, "carbs_g": 200, "fat_g": 89},
            "water_liters": 1.8,
            "notes": "Over on calories. Need to cut back on snacking. Water intake too low.",
        },
        {
            "member_id": 5,
            "member_name": "Lisa Park",
            "date": datetime(2025, 3, 8),
            "meals": [
                {"meal_type": "breakfast", "description": "Smoothie bowl with spinach, banana, and chia seeds", "calories": 320, "protein_g": 15, "carbs_g": 48, "fat_g": 10},
                {"meal_type": "lunch", "description": "Lentil soup with whole grain bread", "calories": 480, "protein_g": 24, "carbs_g": 62, "fat_g": 12},
                {"meal_type": "dinner", "description": "Tofu stir-fry with vegetables and jasmine rice", "calories": 550, "protein_g": 28, "carbs_g": 65, "fat_g": 18},
            ],
            "daily_totals": {"calories": 1350, "protein_g": 67, "carbs_g": 175, "fat_g": 40},
            "water_liters": 3.0,
            "notes": "Protein too low for muscle-building goal. Trainer recommended adding a post-workout shake.",
        },
        {
            "member_id": 4,
            "member_name": "James Rodriguez",
            "date": datetime(2025, 3, 10),
            "meals": [
                {"meal_type": "breakfast", "description": "Egg white omelette with vegetables", "calories": 280, "protein_g": 28, "carbs_g": 12, "fat_g": 8},
                {"meal_type": "lunch", "description": "Grilled fish tacos with slaw", "calories": 520, "protein_g": 36, "carbs_g": 42, "fat_g": 20},
                {"meal_type": "dinner", "description": "Chicken breast with asparagus and wild rice", "calories": 580, "protein_g": 45, "carbs_g": 48, "fat_g": 15},
                {"meal_type": "snack", "description": "Cottage cheese with pineapple", "calories": 200, "protein_g": 22, "carbs_g": 18, "fat_g": 4},
            ],
            "daily_totals": {"calories": 1580, "protein_g": 131, "carbs_g": 120, "fat_g": 47},
            "water_liters": 2.8,
            "notes": "Clean eating day. Good macro balance. Yoga session improved flexibility.",
        },
        {
            "member_id": 10,
            "member_name": "Tom Baker",
            "date": datetime(2025, 3, 12),
            "meals": [
                {"meal_type": "breakfast", "description": "Bagel with cream cheese and orange juice", "calories": 520, "protein_g": 12, "carbs_g": 78, "fat_g": 18},
                {"meal_type": "lunch", "description": "Burger and fries from cafeteria", "calories": 950, "protein_g": 35, "carbs_g": 85, "fat_g": 52},
                {"meal_type": "dinner", "description": "Pasta with meat sauce and garlic bread", "calories": 880, "protein_g": 32, "carbs_g": 110, "fat_g": 30},
            ],
            "daily_totals": {"calories": 2350, "protein_g": 79, "carbs_g": 273, "fat_g": 100},
            "water_liters": 1.2,
            "notes": "Way over calorie target. Trainer flagged this as a pattern — need nutrition counseling session.",
        },
        {
            "member_id": 9,
            "member_name": "Ana Martinez",
            "date": datetime(2025, 3, 14),
            "meals": [
                {"meal_type": "breakfast", "description": "Avocado toast with poached eggs", "calories": 380, "protein_g": 18, "carbs_g": 30, "fat_g": 22},
                {"meal_type": "lunch", "description": "Poke bowl with brown rice", "calories": 560, "protein_g": 35, "carbs_g": 55, "fat_g": 18},
                {"meal_type": "dinner", "description": "Grilled shrimp with zucchini noodles", "calories": 420, "protein_g": 38, "carbs_g": 20, "fat_g": 22},
                {"meal_type": "snack", "description": "Apple with almond butter", "calories": 250, "protein_g": 6, "carbs_g": 28, "fat_g": 14},
            ],
            "daily_totals": {"calories": 1610, "protein_g": 97, "carbs_g": 133, "fat_g": 76},
            "water_liters": 2.4,
            "notes": "Good balance. Could use more protein for strength training recovery.",
        },
        {
            "member_id": 12,
            "member_name": "Chris Lee",
            "date": datetime(2025, 3, 15),
            "meals": [
                {"meal_type": "breakfast", "description": "Protein pancakes with blueberries", "calories": 400, "protein_g": 30, "carbs_g": 45, "fat_g": 12},
                {"meal_type": "lunch", "description": "Chicken Caesar salad", "calories": 480, "protein_g": 38, "carbs_g": 20, "fat_g": 28},
                {"meal_type": "dinner", "description": "Beef stir-fry with mixed vegetables", "calories": 550, "protein_g": 40, "carbs_g": 35, "fat_g": 25},
                {"meal_type": "snack", "description": "Greek yogurt with honey", "calories": 180, "protein_g": 15, "carbs_g": 22, "fat_g": 4},
            ],
            "daily_totals": {"calories": 1610, "protein_g": 123, "carbs_g": 122, "fat_g": 69},
            "water_liters": 2.6,
            "notes": "Solid day. On track with weight loss goal.",
        },
    ])

    db.trainer_reviews.insert_many([
        {
            "member_id": 1,
            "member_name": "Sarah Johnson",
            "trainer_id": 1,
            "trainer_name": "Marcus Rivera",
            "rating": 5,
            "review": "Marcus is incredible. My strength has improved dramatically in 3 months — I'm deadlifting 50% more than when I started. He adjusts the program every 4 weeks and always emphasizes proper form. Worth every penny of the elite membership.",
            "review_date": datetime(2025, 3, 10),
            "categories": ["expertise", "results", "form_correction"],
        },
        {
            "member_id": 2,
            "member_name": "Mike Chen",
            "trainer_id": 3,
            "trainer_name": "Derek Washington",
            "rating": 4,
            "review": "Derek's HIIT sessions are brutal but effective. Lost 3 kg in the first month. Only downside is class sizes — the Monday 6pm slot is always packed and sometimes he can't give individual attention. Would recommend capping it at 15.",
            "review_date": datetime(2025, 3, 5),
            "categories": ["intensity", "results", "class_size"],
        },
        {
            "member_id": 4,
            "member_name": "James Rodriguez",
            "trainer_id": 2,
            "trainer_name": "Yuki Tanaka",
            "rating": 5,
            "review": "Yuki's yoga classes have transformed my flexibility and mental clarity. She offers modifications for all levels and creates a calming atmosphere. The Power Yoga Flow on Mondays is my favorite class in the entire gym.",
            "review_date": datetime(2025, 2, 28),
            "categories": ["expertise", "atmosphere", "accessibility"],
        },
        {
            "member_id": 7,
            "member_name": "Priya Patel",
            "trainer_id": 4,
            "trainer_name": "Sofia Andersson",
            "rating": 3,
            "review": "Sofia knows pilates well but she's often late to class — 10 minutes late twice in February. The exercises are good and I feel my core getting stronger, but punctuality matters when I'm paying premium rates.",
            "review_date": datetime(2025, 3, 1),
            "categories": ["punctuality", "expertise", "core_strength"],
        },
        {
            "member_id": 10,
            "member_name": "Tom Baker",
            "trainer_id": 5,
            "trainer_name": "Kwame Asante",
            "rating": 2,
            "review": "Kwame is friendly but the cardio sessions feel generic. Same routine every week — 20 min treadmill, 15 min bike, 15 min elliptical. For the price I'm paying, I expected more variety and a customized plan. Considering switching trainers.",
            "review_date": datetime(2025, 3, 18),
            "categories": ["variety", "customization", "value"],
        },
    ])

    db.health_assessments.insert_many([
        {
            "member_id": 1,
            "member_name": "Sarah Johnson",
            "assessment_date": datetime(2025, 1, 5),
            "assessment_type": "quarterly_checkup",
            "vitals": {"blood_pressure": "118/76", "resting_hr": 68, "vo2_max": 34.5},
            "measurements": {"weight_kg": 72.5, "body_fat_pct": 24.0, "bmi": 25.1},
            "goals": ["Lose 5 kg", "Reduce body fat to 20%", "Run 5K under 28 minutes"],
            "recommendations": ["Increase strength training to 3x/week", "Add 20 min LISS cardio on rest days", "Target 130g protein daily"],
            "risk_factors": ["Slightly elevated BMI", "Family history of hypertension"],
        },
        {
            "member_id": 1,
            "member_name": "Sarah Johnson",
            "assessment_date": datetime(2025, 3, 5),
            "assessment_type": "quarterly_checkup",
            "vitals": {"blood_pressure": "115/74", "resting_hr": 64, "vo2_max": 37.2},
            "measurements": {"weight_kg": 69.8, "body_fat_pct": 22.1, "bmi": 24.2},
            "goals": ["Lose 2 more kg", "Reduce body fat to 20%", "Run 5K under 26 minutes"],
            "recommendations": ["Continue current program", "Begin interval running 2x/week", "Maintain protein intake"],
            "risk_factors": ["Family history of hypertension — monitor BP"],
        },
        {
            "member_id": 2,
            "member_name": "Mike Chen",
            "assessment_date": datetime(2025, 1, 10),
            "assessment_type": "initial_assessment",
            "vitals": {"blood_pressure": "132/85", "resting_hr": 74, "vo2_max": 28.0},
            "measurements": {"weight_kg": 88.0, "body_fat_pct": 28.5, "bmi": 28.3},
            "goals": ["Lose 10 kg", "Lower blood pressure naturally", "Build cardio endurance"],
            "recommendations": ["HIIT 3x/week", "Reduce sodium intake", "Monitor blood pressure monthly", "Limit alcohol to weekends only"],
            "risk_factors": ["Elevated blood pressure", "Overweight BMI", "Sedentary job"],
        },
        {
            "member_id": 5,
            "member_name": "Lisa Park",
            "assessment_date": datetime(2025, 3, 8),
            "assessment_type": "quarterly_checkup",
            "vitals": {"blood_pressure": "108/68", "resting_hr": 56, "vo2_max": 42.0},
            "measurements": {"weight_kg": 57.5, "body_fat_pct": 19.0, "bmi": 21.1},
            "goals": ["Build lean muscle", "Improve upper body strength", "Maintain cardiovascular fitness"],
            "recommendations": ["Increase calorie intake by 200/day", "Add protein supplement post-workout", "Focus on progressive overload in strength sessions"],
            "risk_factors": ["Low calorie intake risk — ensure minimum 1500 cal/day"],
        },
        {
            "member_id": 10,
            "member_name": "Tom Baker",
            "assessment_date": datetime(2025, 1, 30),
            "assessment_type": "initial_assessment",
            "vitals": {"blood_pressure": "140/90", "resting_hr": 78, "vo2_max": 24.5},
            "measurements": {"weight_kg": 95.0, "body_fat_pct": 32.0, "bmi": 30.1},
            "goals": ["Lose 15 kg", "Get blood pressure under control", "Be able to run 1 mile without stopping"],
            "recommendations": ["Start with low-impact cardio 4x/week", "Mandatory nutrition counseling", "Weekly weigh-ins", "Consider physician referral for blood pressure"],
            "risk_factors": ["Obese BMI", "Stage 1 hypertension", "Poor diet habits", "Low cardiovascular fitness"],
        },
        {
            "member_id": 9,
            "member_name": "Ana Martinez",
            "assessment_date": datetime(2025, 3, 25),
            "assessment_type": "quarterly_checkup",
            "vitals": {"blood_pressure": "112/72", "resting_hr": 66, "vo2_max": 35.8},
            "measurements": {"weight_kg": 66.5, "body_fat_pct": 24.5, "bmi": 24.0},
            "goals": ["Tone and strengthen", "Improve flexibility", "Reduce stress"],
            "recommendations": ["Mix strength and yoga 2x each per week", "Continue current nutrition plan", "Consider adding meditation practice"],
            "risk_factors": ["Mild shoulder impingement — avoid overhead pressing until cleared"],
        },
    ])

    print(f"MongoDB database '{MONGO_DB_NAME}' populated:")
    print(f"  nutrition_logs: {db.nutrition_logs.count_documents({})} documents")
    print(f"  trainer_reviews: {db.trainer_reviews.count_documents({})} documents")
    print(f"  health_assessments: {db.health_assessments.count_documents({})} documents")

    client.close()


if __name__ == "__main__":
    setup()
