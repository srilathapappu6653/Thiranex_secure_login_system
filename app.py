import os
import sqlite3
from datetime import timedelta

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "development-secret-key"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

bcrypt = Bcrypt(app)

DATABASE = "users.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))

        if len(username) < 3:
            flash("Username must contain at least 3 characters.", "danger")
            return redirect(url_for("register"))

        if "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        connection = get_db_connection()

        existing_user = connection.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()

        if existing_user:
            connection.close()
            flash("Username or email already exists.", "danger")
            return redirect(url_for("register"))

        hashed_password = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

        connection.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed_password)
        )

        connection.commit()
        connection.close()

        flash("Registration successful. Please login.", "success")

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return redirect(url_for("login"))

        connection = get_db_connection()

        user = connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        connection.close()

        if user and bcrypt.check_password_hash(
            user["password"],
            password
        ):

            session.clear()

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            session.permanent = True

            flash("Login successful.", "success")

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        username=session["username"]
    )


@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.", "success")

    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()

    app.run(debug=True)