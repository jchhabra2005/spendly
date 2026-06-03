
Spendly
Database Setup — Feature Spec
v2.0  .  June 2026  .  Internal

█  1. Problem Statement
Spendly is an expense tracker where anyone can sign up, log their spending, and see where their money goes.

Right now there is no database. We need to build one that:
-	Stores user accounts securely
-	Saves every expense a user logs
-	Makes sure User A can never see User B's data
-	Stays fast even as more users sign up

█  2. Functional Requirements
Users
-	Anyone can create an account with email + password
-	Passwords are hashed — never stored as plain text
-	A user can log in, log out, change their password, and delete their account

Expenses
-	A logged-in user can add, view, edit, and delete their own expenses
-	Each expense has: amount, category, date, and an optional note
-	Expenses can be filtered by date range, category, or amount

Categories
-	8 default categories ship with the app: Food, Transport, Shopping, Entertainment, Health, Utilities, Education, Other
-	Users can add their own custom categories
-	Deleting a category moves its expenses to Other

█  3. Inputs & Outputs
What goes IN

Action	Required Fields	Rules
Register	email, password	Valid email; password min 8 chars
Login	email, password	Must match a registered account
Add Expense	amount, category, date	Amount > 0; date not in the future; DD-MM-YYYY format
Edit Expense	any expense field	User must own the expense
Delete Expense	expense id	User must own the expense
Filter Expenses	date range / category / min-max amount	date_from must be <= date_to
Add Category	name	Max 80 characters; unique per user
Change Password	current password, new password	Current must be correct; new min 8 chars

What comes OUT

Output	When
Session cookie	After successful login
User profile (id, email, name)	After register or profile update
Expense record	After adding or editing an expense
Paginated expense list	When viewing or filtering expenses
Category list	When opening the category picker
Success / error message	After every action

█  4. Constraints
Tech Stack
-	Backend: Python / Flask
-	Database: SQLite using Python's built-in sqlite3 module — no ORM, no SQLAlchemy
-	All queries written as plain SQL strings inside db.py functions
-	Passwords hashed using werkzeug.security.generate_password_hash — already installed with Flask, no extra package needed

SQL Rules (must follow every time)
-	Use parameterized queries — pass values as ? placeholders, never build SQL by joining strings
-	IMPORTANT : Never use f-strings or .format() inside a SQL query — this is a security risk
-	Run PRAGMA foreign_keys = ON on every new database connection
-	Store expense amounts as REAL (float in Python), not INTEGER
-	All dates stored as text in DD-MM-YYYY format consistently

Security Rules
-	Passwords are never stored or logged as plain text
-	Every expense route checks the user is logged in and owns the record
-	Login endpoint is rate-limited to stop brute-force attacks

Data Rules
-	One account per email address
-	Expense amounts must be positive numbers
-	Expense dates cannot be set in the future
-	System default categories cannot be renamed or deleted
-	Deleting an account removes all their expenses and categories too

Performance
-	First page of expenses (20 records) must load in under 500 ms for up to 10,000 records
-	Database indexes on: user_id, expense_date, category_id

█  5. Error Handling

Situation	Code	Message shown to user
Email already registered	409	An account with this email already exists.
Wrong email or password	401	Invalid email or password.
Not logged in	401	You must be logged in to do this.
Trying to access another user's data	403	You don't have permission to do this.
Expense not found	404	Expense not found.
Amount is zero or negative	400	Amount must be greater than zero.
Expense date is in the future	400	Expense date cannot be in the future.
Password too short	400	Password must be at least 8 characters.
Too many login attempts	429	Too many attempts. Please wait and try again.
Server / database error	500	Something went wrong. Please try again.

█  6. Acceptance Criteria
Registration & Login
-	A new user can sign up with a unique email and be logged in automatically
-	A duplicate email shows an error — no second account is created
-	Wrong credentials on login show a generic error — no session is created
-	After logout, protected pages return a 401

Expenses
-	A logged-in user can add, edit, and delete their own expenses
-	A user cannot read or change another user's expenses (returns 403)
-	Negative amounts and future dates are rejected with a 400 error
-	The expense list shows only the current user's records — never another user's

Categories
-	Default categories are visible to every user
-	A user can create, rename, and delete their own custom categories
-	Deleting a category reassigns its expenses to Other

Security & Performance
-	No plain-text passwords exist anywhere in the database
-	10+ failed logins from the same IP triggers a 429 response
-	A user with 10,000 expenses gets the first page back in under 500 ms

█  7. db.py — Functions to Build
All database logic lives in db.py. Routes call these functions and never touch the database directly. Every function opens its own connection, runs PRAGMA foreign_keys = ON, and closes the connection when done.

Setup

Function	What it does
get_connection()	Opens a sqlite3 connection, runs PRAGMA foreign_keys = ON, and returns the connection object. Called internally by every other function.
init_db()	Runs the CREATE TABLE IF NOT EXISTS statements for users, expenses, and categories.
seed_default_categories()	Inserts the 8 default categories if they are not already there. Safe to call multiple times.

Users

Function	Returns	What it does
create_user(email, password, display_name=None)	user row or None	Hash the password with generate_password_hash, INSERT into users. Return None if email is taken.
get_user_by_id(user_id)	user row or None	SELECT user by primary key.
get_user_by_email(email)	user row or None	SELECT user by email. Used at login.
verify_password(stored_hash, password)	True / False	Call check_password_hash to compare plain password with stored hash.
update_user_profile(user_id, display_name, email)	True / False	UPDATE name or email for the given user.
update_user_password(user_id, old_pw, new_pw)	True / False	Verify old password first, then UPDATE with new hash. Return False if old password is wrong.
delete_user(user_id)	True / False	DELETE user row. Cascade removes all their expenses and categories.

Expenses

Function	Returns	What it does
create_expense(user_id, amount, category_id, date, description=None)	expense row or None	Validate amount > 0 and date <= today, then INSERT. Date must be DD-MM-YYYY string.
get_expense_by_id(expense_id, user_id)	expense row or None	SELECT one expense. Checks user_id matches so users cannot read each other's data.
get_expenses(user_id, page=1, filters={})	dict	Paginated SELECT with optional WHERE clauses for date range, category, amount. Returns {items, total, page, pages}.
update_expense(expense_id, user_id, fields)	True / False	UPDATE the given fields. Checks ownership via user_id in the WHERE clause.
delete_expense(expense_id, user_id)	True / False	DELETE expense only if user_id matches. Returns False if not found or not owned.
get_expense_summary(user_id, date_from=None, date_to=None)	list of dicts	SELECT category name and SUM(amount) grouped by category. Used for the dashboard.

Categories

Function	Returns	What it does
get_categories(user_id)	list	SELECT all default categories plus custom ones belonging to user_id.
create_category(user_id, name)	category row or None	INSERT custom category. Return None if user already has one with the same name.
update_category(category_id, user_id, name)	True / False	UPDATE name. Return False if it is a default category (is_default = 1).
delete_category(category_id, user_id)	True / False	UPDATE expenses to Other category first, then DELETE. Return False if default.

Important: how to write queries safely
Always write queries like this — values go in a separate tuple, never inside the string:

# CORRECT
cursor.execute('SELECT * FROM users WHERE email = ?', (email,))

# WRONG — never do this
cursor.execute(f'SELECT * FROM users WHERE email = {email}')

█  8. Dummy Data (for Development)
Since there are no real users yet, db.py must include a seed_dummy_data() function that fills the database with fake but realistic data so the app can be tested right away.

How to trigger it
-	Call seed_dummy_data() once when the app starts up in development
-	It checks if dummy users already exist before inserting — running it twice is safe
-	Only use this in development. Never run it in production.

What it creates

What	Details
3 dummy users	Each with a name, email, and the password password123 (hashed with generate_password_hash)
20 expenses per user	Spread across the last 3 months with random amounts and categories
Mix of categories	Each user's expenses cover at least 5 different categories
Varied amounts	Range from Rs.50 to Rs.5000 to feel realistic
Optional notes	Roughly half the expenses have a short description filled in

Dummy users to create

Name	Email	Password
Aarav Sharma	aarav@example.com	password123
Priya Mehta	priya@example.com	password123
Rohan Kapoor	rohan@example.com	password123

Sample expenses to insert (per user)

Amount (REAL)	Category	Date (DD-MM-YYYY)	Note
120.0	Food	Use date 7 days ago	Lunch at dhaba
450.0	Transport	14 days ago	Ola cab to airport
1200.0	Shopping	30 days ago	T-shirts from Myntra
80.0	Food	Yesterday	Tea and samosa
2500.0	Health	45 days ago	Pharmacy
600.0	Entertainment	21 days ago	(no note)
300.0	Utilities	Start of month	Mobile recharge
950.0	Education	60 days ago	Udemy course
200.0	Food	4 days ago	Zomato order
3500.0	Shopping	35 days ago	(no note)

Use Python's datetime module to calculate past dates dynamically so dates are always valid relative to today:

from datetime import date, timedelta
seven_days_ago = (date.today() - timedelta(days=7)).strftime('%Y-%m-%d')

█  9. app.py — Changes Needed
The current app.py only renders templates. Once db.py is ready, app.py needs to be updated so each route actually reads from and writes to the database.

Step 1 — Add imports at the top of app.py

from db import init_db, seed_dummy_data, get_user_by_email, create_user,
             verify_password, create_expense, get_expenses, get_expense_by_id,
             update_expense, delete_expense, get_categories, get_expense_summary
from flask import session, redirect, url_for, request, flash
from werkzeug.security import check_password_hash

Step 2 — Initialise the database right after app is created

app = Flask(__name__)
app.secret_key = 'change-this-in-production'
init_db()   # creates tables if they don't exist

Step 3 — Routes to update

Route	Current state	What to add
/register	Renders register.html	Accept POST: call create_user(), store user id in session, redirect to /dashboard
/login	Renders login.html	Accept POST: call get_user_by_email() then verify_password(), store id in session, redirect
/logout	Returns placeholder string	Clear session, redirect to /login
/profile	Returns placeholder string	GET: show profile using session user id. POST: handle password change
/expenses/add	Returns placeholder string	GET: show form. POST: call create_expense() then redirect to /dashboard
/expenses/<id>/edit	Returns placeholder string	GET: load expense, show edit form. POST: call update_expense(), redirect
/expenses/<id>/delete	Returns placeholder string	Call delete_expense(), redirect to /dashboard

Step 4 — New routes to add

New Route	Method	What it does
/dashboard	GET	Show logged-in user's expense list and summary chart. Redirect to /login if no session.
/expenses	GET	Paginated expense list. Reads query params: date_from, date_to, category, page.
/categories	GET, POST	GET: list categories. POST: create a new custom category.
/categories/<id>/delete	POST	Delete custom category, move its expenses to Other.

Step 5 — Protect routes by checking the session
Since we are not using Flask-Login, add this check at the top of every protected route:

if 'user_id' not in session:
    return redirect(url_for('login'))

Routes that need this check:
-	/dashboard
-	/profile
-	/expenses/add
-	/expenses/<id>/edit
-	/expenses/<id>/delete
-	/categories

Step 6 — Seed dummy data on first run (dev only)
Add this at the bottom of app.py:

if __name__ == '__main__':
    seed_dummy_data()   # skips if data already exists
    app.run(debug=True, port=5001)

Summary of all changes

File	Change	Why
app.py	Import db.py functions at top	So routes can call the database
app.py	Call init_db() after app is created	Creates tables on first run
app.py	Add app.secret_key	Required for Flask sessions to work
app.py	Update 7 existing placeholder routes	Make them actually work
app.py	Add 4 new routes	Dashboard, expense list, categories
app.py	Add session check to protected routes	Stop logged-out users accessing pages
app.py	Call seed_dummy_data() on startup	Have test data ready immediately

Spendly  .  Internal Spec  .  v2.0  .  June 2026
