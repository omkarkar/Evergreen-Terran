from sqlalchemy import create_engine
import os

# IMPORTANT: update password if your PostgreSQL password is different
DATABASE_URL = "postgresql+psycopg2://postgres:Satara%40123@localhost:5432/agri_fin_db"


engine = create_engine(DATABASE_URL)
