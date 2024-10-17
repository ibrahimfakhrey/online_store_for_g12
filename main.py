from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'your_secret_key'

# Initialize the database and Flask-Login
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirect users here if not logged in
login_manager.login_message_category = 'info'

# User model
class User(UserMixin, db.Model):  # UserMixin is required by Flask-Login
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='customer', nullable=False)

# Flask-Login: Load user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
@app.route("/")
def start():
    return render_template("index.html")
# Route to register user
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']

        # Check if email already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists. Please log in.', 'danger')
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(name=name, phone=phone, email=email, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('User registered successfully', 'success')
            return redirect(url_for('login'))
        except:
            flash('Error! Something went wrong.', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')

# Route to log in user
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Check your credentials', 'danger')

    return render_template('login.html')

# Route for logged-in user dashboard
@app.route('/dashboard')
@login_required  # Require login to access the dashboard
def dashboard():
    return f"Welcome, {current_user.name}! You are logged in as {current_user.role}."

# Route to log out the user
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create all tables
    app.run(debug=True)
