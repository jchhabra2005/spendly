from flask import Flask, render_template, request, redirect, url_for, session
from collections import defaultdict
import time
from database.db import (
    init_db, seed_dummy_data,
    create_user, get_user_by_id, get_user_by_email, verify_password,
    update_user_profile, update_user_password, delete_user,
    create_expense, get_expense_by_id, get_expenses, update_expense,
    delete_expense, get_expense_summary,
    get_categories, create_category, delete_category,
)

app = Flask(__name__)
app.secret_key = 'change-this-in-production'
init_db()

# In-memory login rate limiting (resets on server restart)
_login_attempts = defaultdict(list)


def _is_rate_limited(ip):
    now = time.time()
    recent = [t for t in _login_attempts[ip] if now - t < 300]
    _login_attempts[ip] = recent
    return len(recent) >= 10


def _record_failed_login(ip):
    _login_attempts[request.remote_addr].append(time.time())


# ------------------------------------------------------------------ #
# Public routes                                                       #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or not password:
            return render_template("register.html", error="All fields are required.")
        if len(password) < 8:
            return render_template("register.html", error="Password must be at least 8 characters.")
        user = create_user(email, password, display_name=name)
        if user is None:
            return render_template("register.html", error="An account with this email already exists.")
        session["user_id"] = user["id"]
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ip = request.remote_addr
        if _is_rate_limited(ip):
            return render_template("login.html", error="Too many attempts. Please wait and try again."), 429
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_user_by_email(email)
        if not user or not verify_password(user["password_hash"], password):
            _record_failed_login(ip)
            return render_template("login.html", error="Invalid email or password.")
        session["user_id"] = user["id"]
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


# ------------------------------------------------------------------ #
# Authenticated routes                                                #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = get_user_by_id(session["user_id"])
    if request.method == "POST":
        old_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        if len(new_pw) < 8:
            return render_template("profile.html", user=user, error="Password must be at least 8 characters.")
        if not update_user_password(session["user_id"], old_pw, new_pw):
            return render_template("profile.html", user=user, error="Current password is incorrect.")
        return render_template("profile.html", user=user, success="Password updated successfully.")
    return render_template("profile.html", user=user)


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]
    result  = get_expenses(user_id)
    summary = get_expense_summary(user_id)
    user    = get_user_by_id(user_id)
    return render_template("dashboard.html", expenses=result["items"],
                           summary=summary, total=result["total"], user=user)


@app.route("/expenses")
def expenses():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]
    page = request.args.get("page", 1, type=int)
    filters = {k: v for k, v in {
        "date_from":   request.args.get("date_from"),
        "date_to":     request.args.get("date_to"),
        "category_id": request.args.get("category_id", type=int),
        "amount_min":  request.args.get("amount_min", type=float),
        "amount_max":  request.args.get("amount_max", type=float),
    }.items() if v is not None}
    result     = get_expenses(user_id, page=page, filters=filters)
    categories = get_categories(user_id)
    return render_template("expenses.html", **result, categories=categories,
                           filters=request.args)


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id    = session["user_id"]
    categories = get_categories(user_id)
    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", 0))
        except ValueError:
            return render_template("add_expense.html", categories=categories, error="Invalid amount.")
        category_id = request.form.get("category_id", type=int)
        date_str    = request.form.get("date", "")
        description = request.form.get("description", "").strip() or None
        if amount <= 0:
            return render_template("add_expense.html", categories=categories,
                                   error="Amount must be greater than zero.")
        expense = create_expense(user_id, amount, category_id, date_str, description)
        if expense is None:
            return render_template("add_expense.html", categories=categories,
                                   error="Invalid date or amount. Date must be DD-MM-YYYY and not in the future.")
        return redirect(url_for("dashboard"))
    return render_template("add_expense.html", categories=categories)


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]
    expense = get_expense_by_id(id, user_id)
    if expense is None:
        return "Expense not found.", 404
    categories = get_categories(user_id)
    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", 0))
        except ValueError:
            return render_template("edit_expense.html", expense=expense,
                                   categories=categories, error="Invalid amount.")
        fields = {
            "amount":      amount,
            "category_id": request.form.get("category_id", type=int),
            "date":        request.form.get("date", ""),
            "description": request.form.get("description", "").strip() or None,
        }
        if update_expense(id, user_id, fields):
            return redirect(url_for("dashboard"))
        return render_template("edit_expense.html", expense=expense, categories=categories,
                               error="Could not update expense.")
    return render_template("edit_expense.html", expense=expense, categories=categories)


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def expense_delete(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    delete_expense(id, session["user_id"])
    return redirect(url_for("dashboard"))


@app.route("/categories", methods=["GET", "POST"])
def categories():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            cats = get_categories(user_id)
            return render_template("categories.html", categories=cats, error="Category name is required.")
        if len(name) > 80:
            cats = get_categories(user_id)
            return render_template("categories.html", categories=cats,
                                   error="Name must be 80 characters or fewer.")
        result = create_category(user_id, name)
        if result is None:
            cats = get_categories(user_id)
            return render_template("categories.html", categories=cats,
                                   error="You already have a category with that name.")
        return redirect(url_for("categories"))
    cats = get_categories(user_id)
    return render_template("categories.html", categories=cats)


@app.route("/categories/<int:id>/delete", methods=["POST"])
def category_delete(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    delete_category(id, session["user_id"])
    return redirect(url_for("categories"))


if __name__ == "__main__":
    seed_dummy_data()
    app.run(debug=True, port=5001)
