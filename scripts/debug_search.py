import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from db import SessionLocal
from sqlalchemy import text

def main():
    db = SessionLocal()
    try:
        # 1) How many projects mention New Cairo in "area"?
        c1 = db.execute(text("SELECT COUNT(*) FROM projects WHERE area ILIKE '%New Cairo%'")).scalar()
        print("projects with area ILIKE '%New Cairo%':", c1)

        # 2) Sample unit types for those projects
        rows = db.execute(text("""
            SELECT DISTINCT put.unit_type
            FROM projects p
            JOIN project_unit_types put ON put.project_id = p.id
            WHERE p.area ILIKE '%New Cairo%'
            LIMIT 50
        """)).fetchall()
        print("sample unit_type values:", [r[0] for r in rows])

        # 3) Min price for apartments in New Cairo (to see if <= 3M exists)
        min_price = db.execute(text("""
            SELECT MIN(put.price)
            FROM projects p
            JOIN project_unit_types put ON put.project_id = p.id
            WHERE p.area ILIKE '%New Cairo%'
              AND put.unit_type ILIKE '%apartment%'
        """)).scalar()
        print("min apartment price in New Cairo:", min_price)

    finally:
        db.close()

if __name__ == "__main__":
    main()
