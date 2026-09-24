import csv
from io import StringIO
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, Response
from models import db, Booking
from data import SERVICE_LIST

app = Flask(__name__)
app.secret_key = "mysecretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///clinic.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# --- 1. หน้าแรก (ต้อนรับ) ---
@app.route("/")
def index():
    return render_template("index.html")

# --- 2. ขั้นตอนที่ 1: กรอกชื่อ อายุ เพศ และวันที่ ---
@app.route("/step1", methods=["GET", "POST"])
def step1():
    if request.method == "POST":
        session["name"] = request.form.get("name")
        session["age"] = request.form.get("age")
        session["gender"] = request.form.get("gender")
        session["date"] = request.form.get("date")
        return redirect(url_for("step2"))
        
    return render_template(
        "step1.html", 
        name=session.get("name", ""), 
        age=session.get("age", ""),
        gender=session.get("gender", ""),
        date=session.get("date", "")
    )

# --- 3. ขั้นตอนที่ 2: เลือกบริการ ---
@app.route("/step2", methods=["GET", "POST"])
def step2():
    if not session.get("name"):
        return redirect(url_for("step1"))
        
    if request.method == "POST":
        session["services"] = request.form.getlist("services")
        return redirect(url_for("step3"))
        
    return render_template("step2.html", services=SERVICE_LIST, chosen_services=session.get("services", []))

# --- 4. ขั้นตอนที่ 3: สรุปข้อมูล (ใช้วันที่ลูกค้าเลือก + เวลาอัตโนมัติ) ---
@app.route("/step3", methods=["GET", "POST"])
def step3():
    name = session.get("name")
    age = session.get("age")
    gender = session.get("gender")
    date = session.get("date")
    services = session.get("services")
    
    if not name or not date:
        return redirect(url_for("step1"))
    
    # ดึงเวลาปัจจุบันอัตโนมัติ (ไม่ดึงวันที่แล้ว เพราะใช้วันที่ที่ลูกค้าเลือก)
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    
    existing_count = Booking.query.filter_by(date=date).count()
    next_queue = existing_count + 1

    if request.method == "POST":
        service_text = ", ".join(services) if services else "ไม่ได้ระบุ"
        new_booking = Booking(
            name=name, age=age, gender=gender, 
            date=date, time=current_time, queue_number=next_queue, services=service_text
        )
        db.session.add(new_booking)
        db.session.commit()
        
        booking_id = new_booking.id
        session.pop("name", None)
        session.pop("age", None)
        session.pop("gender", None)
        session.pop("date", None)
        session.pop("services", None)
        
        return redirect(url_for("success", booking_id=booking_id))
        
    return render_template("step3.html", name=name, age=age, gender=gender, date=date, time=current_time, queue_number=next_queue, services=services)

# --- 5. หน้าใบนัดหมายเมื่อจองสำเร็จ ---
@app.route("/success/<int:booking_id>")
def success(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    return render_template("success.html", booking=booking)

# --- 6. แอดมิน: เข้าสู่ระบบ ---
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == "1111":
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        else:
            error = "รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง"
    return render_template("admin_login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("index"))

# --- 7. แอดมิน: ดูรายการจองทั้งหมด ---
@app.route("/admin")
def admin():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
        
    selected_date = request.args.get("date", "")
    all_dates = [d[0] for d in db.session.query(Booking.date).distinct().order_by(Booking.date.asc()).all()]
    
    if selected_date:
        bookings = Booking.query.filter_by(date=selected_date).order_by(Booking.queue_number.asc()).all()
    else:
        bookings = Booking.query.order_by(Booking.id.desc()).all()
        
    return render_template("admin.html", bookings=bookings, all_dates=all_dates, selected_date=selected_date)

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    bookings = Booking.query.all()
    total_bookings = len(bookings)
    date_stats = {}
    for b in bookings:
        date_stats[b.date] = date_stats.get(b.date, 0) + 1
    sorted_date_stats = sorted(date_stats.items())
    total_dates = len(sorted_date_stats)
    return render_template("admin_dashboard.html", total_bookings=total_bookings, total_dates=total_dates, date_stats=sorted_date_stats)

@app.route("/admin/delete/<int:id>", methods=["POST"])
def delete_booking(id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    booking = Booking.query.get_or_404(id)
    db.session.delete(booking)
    db.session.commit()
    return redirect(url_for("admin"))

@app.route("/admin/clear_all", methods=["POST"])
def clear_all_bookings():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    Booking.query.delete()
    db.session.commit()
    return redirect(url_for("admin"))

# --- 8. แอดมิน: ส่งออกไฟล์ Excel ---
@app.route("/export")
def export_csv():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
        
    bookings = Booking.query.order_by(Booking.id.asc()).all()
    output = StringIO()
    writer = csv.writer(output)
    output.write('\ufeff')
    writer.writerow(["ID", "ชื่อ-นามสกุล", "อายุ", "เพศ", "วันที่รับบริการ", "เวลาเข้าจอง", "ลำดับคิว", "บริการ"])
    
    for b in bookings:
        writer.writerow([b.id, b.name, b.age, b.gender, b.date, b.time, f"คิวที่ {b.queue_number}", b.services])
        
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=bookings.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True)