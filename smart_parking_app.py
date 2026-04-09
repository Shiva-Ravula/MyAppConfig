from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')

class ParkingSpace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    space_number = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(20), default='available')

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    space_id = db.Column(db.Integer, db.ForeignKey('parking_space.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    fee = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='pending')
    active = db.Column(db.Boolean, default=True)

    user = db.relationship('User', backref='reservations')
    space = db.relationship('ParkingSpace', backref='reservations')

def current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

def login_required(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        return func(*args, **kwargs)

    return wrapper

def admin_required(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return func(*args, **kwargs)

    return wrapper

def calculate_fee(start_time, end_time):
    total_hours = max((end_time - start_time).total_seconds() / 3600, 1)
    rate_per_hour = 5.0
    return round(total_hours * rate_per_hour, 2)

BASE_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Smart Parking Management System</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #f4f6f8; }
        nav { background: #1f2937; padding: 15px; }
        nav a { color: white; margin-right: 15px; text-decoration: none; }
        .container { width: 90%; max-width: 1000px; margin: 30px auto; background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background: #f2f2f2; }
        input, select { padding: 10px; width: 100%; margin: 8px 0 15px; }
        button { padding: 10px 18px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; }
        .flash { padding: 10px; margin-bottom: 12px; border-radius: 6px; }
        .success { background: #dcfce7; }
        .warning { background: #fef3c7; }
        .danger { background: #fee2e2; }
        .info { background: #dbeafe; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; }
        .card { padding: 18px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb; }
    </style>
</head>
<body>
    <nav>
        <a href="{{ url_for('home') }}">Home</a>
        {% if user %}
            <a href="{{ url_for('dashboard') }}">Dashboard</a>
            <a href="{{ url_for('spaces') }}">Parking Spaces</a>
            <a href="{{ url_for('my_reservations') }}">My Reservations</a>
            {% if user.role == 'admin' %}
                <a href="{{ url_for('admin_panel') }}">Admin</a>
                <a href="{{ url_for('add_space') }}">Add Space</a>
            {% endif %}
            <a href="{{ url_for('logout') }}">Logout</a>
        {% else %}
            <a href="{{ url_for('register') }}">Register</a>
            <a href="{{ url_for('login') }}">Login</a>
        {% endif %}
    </nav>

    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        {{ content|safe }}
    </div>
</body>
</html>
'''

def render_page(content, **context):
    return render_template_string(BASE_HTML, content=content, user=current_user(), **context)

@app.route('/')
def home():
    content = '''
    <h1>Smart Parking Management System</h1>
    <p>This semester project includes user login, parking space management, reservation handling, payment simulation, and admin reporting.</p>
    <div class="grid">
        <div class="card"><h3>Version 1</h3><p>Login, parking spaces, check-in/check-out.</p></div>
        <div class="card"><h3>Version 2</h3><p>Reservations, time-based booking, payment simulation.</p></div>
        <div class="card"><h3>Version 3</h3><p>Admin dashboard, analytics, optimization-ready structure.</p></div>
    </div>
    '''
    return render_page(content)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        user = User(name=name, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))

    content = '''
    <h2>Register</h2>
    <form method="POST">
        <label>Name</label>
        <input type="text" name="name" required>
        <label>Email</label>
        <input type="email" name="email" required>
        <label>Password</label>
        <input type="password" name="password" required>
        <button type="submit">Register</button>
    </form>
    '''
    return render_page(content)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))

        flash('Invalid email or password.', 'danger')
        return redirect(url_for('login'))

    content = '''
    <h2>Login</h2>
    <form method="POST">
        <label>Email</label>
        <input type="email" name="email" required>
        <label>Password</label>
        <input type="password" name="password" required>
        <button type="submit">Login</button>
    </form>
    '''
    return render_page(content)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_spaces = ParkingSpace.query.count()
    available_spaces = ParkingSpace.query.filter_by(status='available').count()
    reserved_spaces = ParkingSpace.query.filter_by(status='reserved').count()
    occupied_spaces = ParkingSpace.query.filter_by(status='occupied').count()

    content = f'''
    <h2>Dashboard</h2>
    <div class="grid">
        <div class="card"><h3>Total Spaces</h3><p>{total_spaces}</p></div>
        <div class="card"><h3>Available</h3><p>{available_spaces}</p></div>
        <div class="card"><h3>Reserved</h3><p>{reserved_spaces}</p></div>
        <div class="card"><h3>Occupied</h3><p>{occupied_spaces}</p></div>
    </div>
    '''
    return render_page(content)

@app.route('/spaces')
@login_required
def spaces():
    all_spaces = ParkingSpace.query.order_by(ParkingSpace.space_number).all()

    rows = ''
    for s in all_spaces:
        action = ''
        if s.status == 'available':
            action = f'<a href="/reserve/{s.id}"><button>Reserve</button></a>'
        rows += f'<tr><td>{s.space_number}</td><td>{s.status}</td><td>{action}</td></tr>'

    content = f'''
    <h2>Parking Spaces</h2>
    <table>
        <tr><th>Space Number</th><th>Status</th><th>Action</th></tr>
        {rows}
    </table>
    '''
    return render_page(content)

@app.route('/reserve/<int:space_id>', methods=['GET', 'POST'])
@login_required
def reserve(space_id):
    space = ParkingSpace.query.get_or_404(space_id)

    if request.method == 'POST':
        start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
        end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')

        if end_time <= start_time:
            flash('End time must be after start time.', 'danger')
            return redirect(url_for('reserve', space_id=space_id))

        fee = calculate_fee(start_time, end_time)
        reservation = Reservation(
            user_id=session['user_id'],
            space_id=space.id,
            start_time=start_time,
            end_time=end_time,
            fee=fee,
            payment_status='pending',
            active=True,
        )
        space.status = 'reserved'
        db.session.add(reservation)
        db.session.commit()

        flash(f'Reservation created successfully. Fee: ${fee}', 'success')
        return redirect(url_for('my_reservations'))

    content = f'''
    <h2>Reserve Space {space.space_number}</h2>
    <form method="POST">
        <label>Start Time</label>
        <input type="datetime-local" name="start_time" required>
        <label>End Time</label>
        <input type="datetime-local" name="end_time" required>
        <button type="submit">Confirm Reservation</button>
    </form>
    '''
    return render_page(content)

@app.route('/my_reservations')
@login_required
def my_reservations():
    reservations = Reservation.query.filter_by(user_id=session['user_id']).order_by(Reservation.start_time.desc()).all()

    rows = ''
    for r in reservations:
        pay_btn = '' if r.payment_status == 'paid' else f'<a href="/pay/{r.id}"><button>Pay</button></a>'
        rows += f'''
        <tr>
            <td>{r.space.space_number}</td>
            <td>{r.start_time}</td>
            <td>{r.end_time}</td>
            <td>${r.fee}</td>
            <td>{r.payment_status}</td>
            <td>{pay_btn}</td>
        </tr>
        '''

    content = f'''
    <h2>My Reservations</h2>
    <table>
        <tr><th>Space</th><th>Start</th><th>End</th><th>Fee</th><th>Payment</th><th>Action</th></tr>
        {rows}
    </table>
    '''
    return render_page(content)

@app.route('/pay/<int:reservation_id>')
@login_required
def pay(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.user_id != session['user_id']:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('my_reservations'))

    reservation.payment_status = 'paid'
    reservation.space.status = 'occupied'
    db.session.commit()
    flash('Payment successful. Space marked as occupied.', 'success')
    return redirect(url_for('my_reservations'))

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    reservations = Reservation.query.order_by(Reservation.start_time.desc()).all()
    total_revenue = sum(r.fee for r in reservations if r.payment_status == 'paid')

    rows = ''
    for r in reservations:
        rows += f'''
        <tr>
            <td>{r.user.name}</td>
            <td>{r.space.space_number}</td>
            <td>{r.start_time}</td>
            <td>{r.end_time}</td>
            <td>${r.fee}</td>
            <td>{r.payment_status}</td>
        </tr>
        '''

    content = f'''
    <h2>Admin Dashboard</h2>
    <div class="grid">
        <div class="card"><h3>Total Reservations</h3><p>{len(reservations)}</p></div>
        <div class="card"><h3>Total Revenue</h3><p>${round(total_revenue, 2)}</p></div>
    </div>
    <table>
        <tr><th>User</th><th>Space</th><th>Start</th><th>End</th><th>Fee</th><th>Payment</th></tr>
        {rows}
    </table>
    '''
    return render_page(content)

@app.route('/add_space', methods=['GET', 'POST'])
@login_required
@admin_required
def add_space():
    if request.method == 'POST':
        space_number = request.form['space_number']
        if ParkingSpace.query.filter_by(space_number=space_number).first():
            flash('Space already exists.', 'danger')
            return redirect(url_for('add_space'))

        db.session.add(ParkingSpace(space_number=space_number, status='available'))
        db.session.commit()
        flash('Parking space added successfully.', 'success')
        return redirect(url_for('spaces'))

    content = '''
    <h2>Add Parking Space</h2>
    <form method="POST">
        <label>Space Number</label>
        <input type="text" name="space_number" required>
        <button type="submit">Add Space</button>
    </form>
    '''
    return render_page(content)

@app.cli.command('init-db')
def init_db_command():
    db.create_all()

    if not User.query.filter_by(email='admin@parking.com').first():
        admin = User(
            name='Admin',
            email='admin@parking.com',
            password=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)

    if ParkingSpace.query.count() == 0:
        for i in range(1, 11):
            db.session.add(ParkingSpace(space_number=f'A-{i}', status='available'))

    db.session.commit()
    print('Database initialized with admin user and sample parking spaces.')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)