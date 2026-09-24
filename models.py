from flask_sqlalchemy import SQLAlchemy

# กำหนดตัวแปรจัดการฐานข้อมูล
db = SQLAlchemy()

# ตารางบันทึกการจองคิว
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)        # เก็บอายุ
    gender = db.Column(db.String(20), nullable=False)  # เก็บเพศ
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(10), nullable=False)    # เก็บเวลา
    queue_number = db.Column(db.Integer, nullable=False)
    services = db.Column(db.Text, nullable=False)