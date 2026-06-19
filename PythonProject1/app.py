from flask import request
import qrcode
import io
from flask import send_file

from datetime import datetime
from flask import Flask, render_template, request, redirect, session
from flask_mysqldb import MySQL
import config

app = Flask(__name__)

# -----------------------
# MySQL Configuration
# -----------------------
app.config["MYSQL_HOST"] = config.MYSQL_HOST
app.config["MYSQL_USER"] = config.MYSQL_USER
app.config["MYSQL_PASSWORD"] = config.MYSQL_PASSWORD
app.config["MYSQL_DB"] = config.MYSQL_DB

app.secret_key = config.SECRET_KEY

mysql = MySQL(app)

# ===========================
# LOGIN
# ===========================
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        cursor = mysql.connection.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s AND role=%s",
            (email, password, role)
        )

        user = cursor.fetchone()

        cursor.close()

        if user:

            session["user_id"] = user[0]
            session["name"] = user[1]
            session["role"] = user[4]
            session["roll_no"] = user[5]
            session["department"] = user[6]
            session["year"] = user[7]

            if user[4] == "student":
                return redirect("/student")

            elif user[4] == "faculty":
                return redirect("/faculty")

            elif user[4] == "guard":
                return redirect("/guard")

            elif user[4] == "admin":
                return redirect("/admin")


        return "Invalid Email or Password"

    return render_template("login.html")


# ===========================
# REGISTER
# ===========================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        roll = request.form["roll"]
        department = request.form["department"]
        year = request.form["year"]

        cursor = mysql.connection.cursor()

        cursor.execute("""
            INSERT INTO users
            (name,email,password,role,roll_no,department,year)
            VALUES(%s,%s,%s,%s,%s,%s,%s)
        """, (
            name,
            email,
            password,
            "student",
            roll,
            department,
            year
        ))

        mysql.connection.commit()

        cursor.close()

        return redirect("/")

    return render_template("register.html")

@app.route("/admin")
def admin():

    if "user_id" not in session:
        return redirect("/")

    cursor = mysql.connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='student'")
    students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='faculty'")
    faculty = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='guard'")
    guards = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM gate_passes")
    passes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM gate_passes WHERE status='Pending'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM gate_passes WHERE status='Approved'")
    approved = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM gate_passes WHERE status='Rejected'")
    rejected = cursor.fetchone()[0]

    cursor.close()

    return render_template(
        "admin/admin_dashboard.html",
        students=students,
        faculty=faculty,
        guards=guards,
        passes=passes,
        pending=pending,
        approved=approved,
        rejected=rejected
    )
@app.route("/manage_faculty")
def manage_faculty():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
        id,
        name,
        email,
        department

        FROM users

        WHERE role='faculty'
    """)

    faculties = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/manage_faculty.html",
        faculties=faculties
    )


@app.route("/delete_faculty/<int:id>")
def delete_faculty(id):

    cursor = mysql.connection.cursor()

    cursor.execute(
        "DELETE FROM users WHERE id=%s",
        (id,)
    )

    mysql.connection.commit()

    cursor.close()

    return redirect("/manage_faculty")
@app.route("/add_faculty", methods=["POST"])
def add_faculty():

    name = request.form["name"]
    email = request.form["email"]
    department = request.form["department"]
    password = request.form["password"]  # later we can hash it

    cursor = mysql.connection.cursor()

    cursor.execute("""
        INSERT INTO users (name, email, department, password, role)
        VALUES (%s, %s, %s, %s, %s)
    """, (name, email, department, password, "faculty"))

    mysql.connection.commit()
    cursor.close()

    return redirect("/manage_faculty")
# ===========================
# STUDENT DASHBOARD
# ===========================
@app.route("/student")
def student():

    if "user_id" not in session:
        return redirect("/")

    return render_template("students/dashboard.html")


# ===========================
# FACULTY DASHBOARD
# ===========================
@app.route("/faculty")
def faculty():

    if "user_id" not in session:
        return redirect("/")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            gate_passes.id,
            users.name,
            users.roll_no,
            users.department,
            gate_passes.reason,
            gate_passes.destination,
            gate_passes.out_date,
            gate_passes.out_time,
            gate_passes.return_time,
            gate_passes.status

        FROM gate_passes

        JOIN users
        ON gate_passes.student_id = users.id

        WHERE gate_passes.status='Pending'

        ORDER BY gate_passes.created_at DESC
    """)

    passes = cursor.fetchall()

    cursor.close()

    return render_template("faculty/dashboard.html", passes=passes)
@app.route("/approve/<int:id>", methods=["GET", "POST"])
def approve(id):

    remark = request.form["remark"]

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE gate_passes
        SET status=%s,
            faculty_remark=%s
        WHERE id=%s
    """, (
        "Approved",
        remark,
        id
    ))

    mysql.connection.commit()

    cursor.close()

    return redirect("/faculty")
@app.route("/reject/<int:id>", methods=["GET", "POST"])
def reject(id):

    remark = request.form["remark"]

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE gate_passes
        SET status=%s,
            faculty_remark=%s
        WHERE id=%s
    """, (
        "Rejected",
        remark,
        id
    ))

    mysql.connection.commit()

    cursor.close()

    return redirect("/faculty")
# ===========================
# GUARD DASHBOARD
# ===========================
@app.route("/guard")
def guard():

    if "user_id" not in session:
        return redirect("/")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
            gate_passes.id,
            users.name,
            users.roll_no,
            users.department,
            gate_passes.reason,
            gate_passes.destination,
            gate_passes.out_date,
            gate_passes.out_time,
            gate_passes.return_time,
            gate_passes.exit_status

        FROM gate_passes

        JOIN users
        ON gate_passes.student_id = users.id

        WHERE gate_passes.status='Approved'

        ORDER BY gate_passes.created_at DESC
    """)

    passes = cursor.fetchall()

    cursor.close()

    return render_template("guard/dashboard.html", passes=passes)
@app.route("/exit/<int:id>")
def exit_student(id):

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE gate_passes
        SET exit_status=%s,
            actual_exit_time=%s
        WHERE id=%s
    """, (
        "Exited",
        datetime.now(),
        id
    ))

    mysql.connection.commit()
    cursor.close()

    return redirect("/guard")
@app.route("/return/<int:id>")
def return_student(id):

    cursor = mysql.connection.cursor()

    cursor.execute("""
        UPDATE gate_passes
        SET exit_status=%s,
            actual_return_time=%s
        WHERE id=%s
    """, (
        "Returned",
        datetime.now(),
        id
    ))

    mysql.connection.commit()
    cursor.close()

    return redirect("/guard")
# ===========================
# APPLY GATE PASS
# ===========================
@app.route("/apply", methods=["GET", "POST"])
def apply():

    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":

        reason = request.form["reason"]
        destination = request.form["destination"]
        out_date = request.form["out_date"]
        out_time = request.form["out_time"]
        return_time = request.form["return_time"]

        cursor = mysql.connection.cursor()

        cursor.execute("""
            INSERT INTO gate_passes
            (student_id,reason,destination,out_date,out_time,return_time)
            VALUES(%s,%s,%s,%s,%s,%s)
        """, (
            session["user_id"],
            reason,
            destination,
            out_date,
            out_time,
            return_time
        ))

        mysql.connection.commit()

        cursor.close()

        return redirect("/my_passes")

    return render_template("students/apply.html")


# ===========================
# VIEW STATUS
# ===========================
@app.route("/status")
def status():

    if "user_id" not in session:
        return redirect("/")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT id,
               reason,
               destination,
               out_date,
               out_time,
               return_time,
               status,
               faculty_remark
        FROM gate_passes
        WHERE student_id=%s
        ORDER BY created_at DESC
    """,(session["user_id"],))

    passes = cursor.fetchall()

    cursor.close()

    return render_template("students/status.html", passes=passes)
# ===========================
# LOGOUT
# ===========================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

@app.route("/manage_students")
def manage_students():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT
        id,
        name,
        email,
        roll_no,
        department,
        year

        FROM users

        WHERE role='student'
    """)

    students = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/manage_students.html",
        students=students
    )
@app.route("/add_student", methods=["POST"])
def add_student():

    name = request.form["name"]
    email = request.form["email"]
    department = request.form["department"]
    roll_no = request.form["roll_no"]
    password = request.form["password"]

    cursor = mysql.connection.cursor()

    cursor.execute("""
        INSERT INTO users (name, email, department, roll_no, password, role)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (name, email, department, roll_no, password, "student"))

    mysql.connection.commit()
    cursor.close()

    return redirect("/manage_students")

@app.route("/delete_student/<int:id>")
def delete_student(id):

    cursor = mysql.connection.cursor()

    cursor.execute(
        "DELETE FROM users WHERE id=%s",
        (id,)
    )

    mysql.connection.commit()

    cursor.close()

    return redirect("/manage_students")
@app.route("/manage_guards")
def manage_guards():

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT id, name, email
        FROM users
        WHERE role='guard'
    """)

    guards = cursor.fetchall()
    cursor.close()

    return render_template("admin/manage_guards.html", guards=guards)
@app.route("/delete_guard/<int:id>")
def delete_guard(id):

    cursor = mysql.connection.cursor()

    cursor.execute("DELETE FROM users WHERE id=%s", (id,))

    mysql.connection.commit()
    cursor.close()

    return redirect("/manage_guards")

@app.route("/add_guard", methods=["POST"])
def add_guard():

    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]

    cursor = mysql.connection.cursor()

    cursor.execute("""
        INSERT INTO users (name, email, password, role)
        VALUES (%s, %s, %s, %s)
    """, (name, email, password, "guard"))

    mysql.connection.commit()
    cursor.close()

    return redirect("/manage_guards")

@app.route("/all_passes")
def all_passes():
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/")

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT 
            gate_passes.id, 
            users.name, 
            gate_passes.reason, 
            gate_passes.status, 
            gate_passes.out_date
        FROM gate_passes
        JOIN users ON gate_passes.student_id = users.id
        ORDER BY gate_passes.id DESC
    """)

    passes = cursor.fetchall()
    cursor.close()

    return render_template("admin/all_passes.html", passes=passes)






@app.route("/reports")
def reports():

    cursor = mysql.connection.cursor()

    # Total counts
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='student'")
    students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='faculty'")
    faculty = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='guard'")
    guards = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM gate_passes")
    passes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM gate_passes WHERE status='Pending'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM gate_passes WHERE status='Approved'")
    approved = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM gate_passes WHERE status='Rejected'")
    rejected = cursor.fetchone()[0]

    cursor.close()

    return render_template(
        "admin/reports.html",
        students=students,
        faculty=faculty,
        guards=guards,
        passes=passes,
        pending=pending,
        approved=approved,
        rejected=rejected
    )
@app.route("/qr/<int:pass_id>")
def qr(pass_id):
    # Dynamically gets the current domain (localhost or public link)
    base_url = request.host_url.rstrip('/')
    qr_url = f"{base_url}/verify_pass/{pass_id}"

    img = qrcode.make(qr_url)

    buffer = io.BytesIO()
    img.save(buffer)
    buffer.seek(0)

    return send_file(buffer, mimetype="image/png")

@app.route("/verify_pass/<int:pass_id>")
def verify_pass(pass_id):

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT gp.id, u.name, u.roll_no, gp.reason, gp.status, gp.out_date
        FROM gate_passes gp
        JOIN users u ON gp.student_id = u.id
        WHERE gp.id = %s
    """, (pass_id,))

    data = cursor.fetchone()
    cursor.close()

    return render_template("admin/verify_pass.html", data=data)

@app.route("/my_passes")
def my_passes():
    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    cursor = mysql.connection.cursor()

    cursor.execute("""
        SELECT id, reason, status, out_date
        FROM gate_passes
        WHERE student_id=%s
        ORDER BY id DESC
    """, (user_id,))

    passes = cursor.fetchall()
    cursor.close()

    return render_template("students/my_passes.html", passes=passes)

if __name__ == "__main__":
    app.run(debug=True)