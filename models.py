from flask_sqlalchemy import SQLAlchemy

# กำหนดตัวแปรจัดการฐานข้อมูล
db = SQLAlchemy()

# ตารางบันทึกการจองคิว
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    queue_number = db.Column(db.Integer, nullable=False)  # คอลัมน์ลำดับคิว
    services = db.Column(db.Text, nullable=False)