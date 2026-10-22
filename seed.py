"""Create demo data: python seed.py  (admin/admin123; coastal, riverside, hilltown / center123)"""
from app import create_app
import seed_data

app = create_app()
with app.app_context():
    seed_data.load()
