from flask import Flask, request, redirect, url_for, session, jsonify, Response
import mysql.connector
import os
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message  # Ensure Flask-Mail is installed and configured
from bs4 import BeautifulSoup  # Import BeautifulSoup for sanitization
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pytz  # Ensure pytz is installed for timezone handling
from slugify import slugify  # Ensure this is the correct import
import shutil
from flask_login import login_required, LoginManager, UserMixin, login_user

app = Flask(__name__)

# --- Configuration ---
# Secret key for session management
app.secret_key = 'your_secret_key_here'

# Database configuration
db_config = {
    'user': 'root',
    'password': 'ThEnExTbIgThInG#7447',
    'host': 'localhost',
    'database': 'FrenchGta'
}

# File upload configuration
UPLOAD_FOLDER = 'w:/FRENCH.GTA/code/static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'frenchgta.ca@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'heoe whvu msfp mdye'  # Replace with your app password
app.config['MAIL_DEFAULT_SENDER'] = 'frenchgta.ca@gmail.com'  # Replace with your email
mail = Mail(app)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:ThEnExTbIgThInG#7447@localhost/FrenchGta'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the User model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(255), nullable=True)
    custom_number = db.Column(db.String(50), nullable=True)
    # Add a backref for the relationship with Student
    students = db.relationship('Student', backref='user', lazy=True)

# Define the Blog model
class Blog(db.Model):
    __tablename__ = 'blogs'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)  # Add slug field
    category = db.Column(db.String(50), nullable=False)  # Add category field
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255), nullable=True)

    def __init__(self, title, category, content, image=None):
        self.title = title
        self.category = category
        self.slug = slugify(f"{category}_{title}")  # Ensure category and title are strings
        self.content = content
        self.image = image

class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    availability = db.Column(db.String(255), nullable=True)
    specialization = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hours_worked = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, nullable=True)
    students = db.relationship('Student', backref='teacher', lazy=True)
    materials = db.relationship('Material', backref='teacher', lazy=True)
    schedules = db.relationship('Schedule', backref='teacher', lazy=True)

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    contact = db.Column(db.String(255), nullable=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_classes = db.Column(db.Integer, default=0)
    remaining_classes = db.Column(db.Integer, default=0)
    months_continuing = db.Column(db.Integer, nullable=True)
    nationality = db.Column(db.String(255), nullable=True)
    availability = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)

class Material(db.Model):
    __tablename__ = 'materials'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)

class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sender_role = db.Column(db.String(50), nullable=False)  # 'teacher' or 'student'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Properly define the timestamp attribute

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)

class Schedule(db.Model):
    __tablename__ = 'schedules'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    subject = db.Column(db.String(255), nullable=False)

# --- Utility Functions ---
def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def connect_db():
    """Connect to the database."""
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {repr(err)}")
        return None

def sanitize_input(data):
    """Basic input sanitization."""
    if data is None:
        return ""  # Return an empty string if the input is None
    data = data.strip()
    data = data.replace('<', '&lt;').replace('>', '&gt;')
    return data

def sanitize_html(content):
    """Sanitize HTML content to remove unwanted attributes and tags."""
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup.find_all(True):
        # Allow only specific tags
        if tag.name not in ["b", "i", "u", "strong", "em", "p", "ul", "ol", "li", "a", "h1", "h2", "h3", "h4", "h5", "h6", "br"]:
            tag.decompose()
        else:
            # Remove all attributes except href for <a> tags
            if tag.name == "a":
                tag.attrs = {key: tag.attrs[key] for key in tag.attrs if key == "href"}
            else:
                tag.attrs = {}  # Remove all other attributes
    return str(soup)

# --- File Upload Route ---
@app.route('/upload_image', methods=['POST'])
def upload_image():
    """Handle image uploads."""
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        file_url = url_for('static', filename=f'uploads/{filename}', _external=True)
        return jsonify({'url': file_url}), 200

    return jsonify({'error': 'Invalid file type'}), 400

# --- Inquiry Submission Route ---
@app.route('/submit_inquiry', methods=['POST'])
def submit_inquiry():
    """Handle inquiry form submissions."""
    # Debugging: Log the received form data
    print("Received Form Data:", request.form.to_dict())

    name = sanitize_input(request.form.get('name'))
    email = sanitize_input(request.form.get('email'))

    # Validate input fields
    if not name or not email:
        return redirect(url_for('index', error='Name and email are required.'))

    if '@' not in email or '.' not in email:
        return redirect(url_for('index', error='Invalid email address.'))

    # Send acknowledgment email to the inquirer
    try:
        acknowledgment_msg = Message(
            subject="Thank You for Your Inquiry - FRENCH.GTA",
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[email],
            body=f"Dear {name},\n\nThank you for reaching out to FRENCH.GTA. We have received your inquiry and will get back to you shortly.\n\nBest regards,\nFRENCH.GTA Team"
        )
        mail.send(acknowledgment_msg)

        # Log the inquiry for internal purposes
        print(f"Inquiry received from {name} ({email}).")

        # Redirect back to index with a success message
        return redirect(url_for('index', success=f'Thank you for reaching out to us, {name}! We will get back to you shortly.'))
    except Exception as e:
        print(f"Error sending acknowledgment email: {repr(e)}")
        return redirect(url_for('index', error='Failed to process your inquiry. Please try again later.'))

# --- Authentication Routes ---
@app.route('/login.html', methods=['GET', 'POST'])
def login():
    """Login route."""
    if request.method == 'POST':
        email = sanitize_input(request.form['email'])
        password = sanitize_input(request.form['password'])

        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)
        try:
            query = "SELECT id, email, role, name FROM users WHERE email = %s AND password = %s"
            cursor.execute(query, (email, password))
            user = cursor.fetchone()
            if user:
                user_obj = SimpleUser(user['id'], user['email'], user['role'], user.get('name'))
                login_user(user_obj)
                if user['role'] == 'admin':
                    return redirect(url_for('admin_portal'))
                elif user['role'] == 'student':
                    return redirect(url_for('student_schedule'))
                elif user['role'] == 'teacher':
                    return redirect(url_for('teacher_dashboard'))
            return "Invalid email or password", 401
        except mysql.connector.Error as err:
            print(f"Database error: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()

    return jsonify({'message': 'Login page. Please POST your credentials.'})

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register route."""
    if request.method == 'POST':
        email = sanitize_input(request.form['email'])
        password = sanitize_input(request.form['password'])

        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor()
        try:
            query = "INSERT INTO users (email, password, role) VALUES (%s, %s, 'user')"
            cursor.execute(query, (email, password))
            conn.commit()
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            print(f"Database error: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()

    return jsonify({'message': 'Register page. Please POST your registration data.'})

@app.route('/logout')
def logout():
    """Log out the user and clear the session."""
    session.clear()
    return redirect(url_for('login'))

# --- Admin Portal and User Management ---
@app.route('/admin_portal', methods=['GET'])
@login_required
def admin_portal():
    """Admin portal to manage users and blogs."""
    conn = connect_db()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch role filter from query parameters
        role_filter = request.args.get('role_filter', '')

        # Fetch users with optional role filtering
        query = "SELECT id AS user_id, email, name, role, custom_number FROM users"
        params = []
        if role_filter:
            query += " WHERE role = %s"
            params.append(role_filter)

        cursor.execute(query, params)
        users = cursor.fetchall()

        # Fetch all blogs
        cursor.execute("SELECT * FROM blogs")
        blogs = cursor.fetchall()

        # Define all available categories
        categories = ["french", "canadian_immigration", "general", "tef_specific"]

        # Pass the users, blogs, role filter, and categories to the template
        return jsonify({'users': users, 'blogs': blogs, 'edit_user': None, 'role_filter': role_filter, 'categories': categories})
    except mysql.connector.Error as err:
        print(f"Database error in admin_portal: {repr(err)}")
        return f"Database error: {repr(err)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/edit_user_form/<int:user_id>', methods=['GET'])
def edit_user_form(user_id):
    """Fetch user data and pass it to the admin portal for editing."""
    conn = connect_db()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch the user data by ID, including the password
        cursor.execute("SELECT id AS user_id, email, name, password, role, custom_number FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return "User not found", 404

        # Fetch all users for the list
        cursor.execute("SELECT id AS user_id, email, name, role, custom_number FROM users")
        users = cursor.fetchall()

        # Pass the user data and the list of users to the admin portal
        return jsonify({'users': users, 'edit_user': user})
    except mysql.connector.Error as err:
        print(f"Database error in edit_user_form: {repr(err)}")
        return f"Database error: {repr(err)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/manage_users', methods=['POST'])
def manage_users():
    """Handle creating or updating users."""
    user_id = request.form.get('user_id')
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')
    role = request.form.get('role')
    custom_number = request.form.get('custom_number')

    conn = connect_db()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor(dictionary=True)
    try:
        if user_id:  # Update existing user
            query = """
                UPDATE users
                SET email = %s, name = %s, password = %s, role = %s, custom_number = %s
                WHERE id = %s
            """
            cursor.execute(query, (email, name, password or None, role, custom_number, user_id))
        else:  # Create new user
            # Generate user_id based on role
            prefix = "2501" if role == "admin" else "2502" if role == "teacher" else "2503"
            cursor.execute(f"SELECT MAX(id) AS max_id FROM users WHERE id LIKE '{prefix}%'")
            result = cursor.fetchone()
            max_id = int(result['max_id']) if result['max_id'] else int(prefix + "000")
            new_user_id = max_id + 1

            query = """
                INSERT INTO users (id, email, name, password, role, custom_number)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (new_user_id, email, name, password, role, custom_number))
        conn.commit()
        return redirect(url_for('admin_portal'))
    except mysql.connector.Error as err:
        print(f"Database error in manage_users: {repr(err)}")
        return f"Database error: {repr(err)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/edit_user', methods=['POST'])
def edit_user():
    """Handle user editing actions."""
    user_id = request.form.get('user_id')
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')
    role = request.form.get('role')
    custom_number = request.form.get('custom_number')

    conn = connect_db()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch the current user data
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return "User not found", 404

        # Use existing values if fields are not provided
        email = email or user['email']
        name = name or user['name']
        password = password or user['password']
        role = role or user['role']
        custom_number = custom_number or user['custom_number']

        # Update the user data
        query = """
            UPDATE users
            SET email = %s, name = %s, password = %s, role = %s, custom_number = %s
            WHERE id = %s
        """
        cursor.execute(query, (email, name, password, role, custom_number, user_id))
        conn.commit()
        return redirect(url_for('admin_portal'))
    except mysql.connector.Error as err:
        print(f"Database error in edit_user: {repr(err)}")
        return f"Database error: {repr(err)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    """Handle user deletion."""
    conn = connect_db()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor()
    try:
        query = "DELETE FROM users WHERE id = %s"
        cursor.execute(query, (user_id,))
        conn.commit()
        return redirect(url_for('admin_portal'))
    except mysql.connector.Error as err:
        print(f"Database error in delete_user: {repr(err)}")
        return f"Database error: {repr(err)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/admin_add_blog', methods=['POST'])
def admin_add_blog():
    """Add or override a blog."""
    title = request.form.get('title')
    category = request.form.get('category', 'general')  # Default category
    content = request.form.get('content')
    image = None

    if 'image' in request.files:
        image_file = request.files['image']
        if image_file and allowed_file(image_file.filename):
            image_filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            image = image_filename

    slug = slugify(f"{category}_{title}")
    conn = connect_db()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor()
    try:
        # Check if a blog with the same slug already exists
        cursor.execute("SELECT id FROM blogs WHERE slug = %s", (slug,))
        existing_blog = cursor.fetchone()

        if existing_blog:
            # Update the existing blog
            query = """
                UPDATE blogs
                SET title = %s, category = %s, content = %s, image = %s
                WHERE slug = %s
            """
            cursor.execute(query, (title, category, content, image, slug))
        else:
            # Insert a new blog
            query = "INSERT INTO blogs (title, slug, category, content, image) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query, (title, slug, category, content, image))

        conn.commit()
        return redirect(url_for('blog_management'))
    except mysql.connector.Error as err:
        print(f"Database error in admin_add_blog: {repr(err)}")
        return f"Database error: {repr(err)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/admin_edit_blog', methods=['POST'])
def admin_edit_blog():
    """Edit an existing blog."""
    if 'role' in session and session['role'] == 'admin':
        blog_id = request.form.get('blog_id')
        title = sanitize_input(request.form.get('title'))
        category = sanitize_input(request.form.get('category'))
        content = sanitize_html(request.form.get('content'))
        image = None

        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and allowed_file(image_file.filename):
                image_filename = secure_filename(image_file.filename)
                image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                image = image_filename

        try:
            blog = Blog.query.get(int(blog_id))
            if not blog:
                return jsonify({'error': 'Blog not found'}), 404

            new_slug = slugify(f"{category}_{title}")
            if new_slug != blog.slug:
                existing_blog = Blog.query.filter_by(slug=new_slug).first()
                if existing_blog:
                    return jsonify({'error': 'A blog with this category and title already exists. Choose a different title or override the existing blog.'}), 400

            blog.title = title
            blog.category = category
            blog.slug = new_slug
            blog.content = content
            if image:
                blog.image = image

            db.session.commit()
            return redirect(url_for('blog_management'))
        except Exception as e:
            print(f"Error updating blog: {repr(e)}")
            return jsonify({'error': 'Failed to update blog'}), 500
    return redirect(url_for('login'))

@app.route('/teacher_portal')
@login_required
def teacher_portal():
    # Redirect to dashboard for modular navigation
    return redirect(url_for('teacher_dashboard'))

@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    teacher_user_id = session['user_id']
    teacher_name = session.get('teacher_name', 'Teacher')
    upcoming_count = 0
    student_count = 0
    payments_month = 0
    return jsonify({
        'teacher_name': teacher_name,
        'upcoming_count': upcoming_count,
        'student_count': student_count,
        'payments_month': payments_month,
        'active_page': 'dashboard'
    })

@app.route('/teacher/chat')
@login_required
def teacher_chat():
    teacher_user_id = session['user_id']
    students = get_students_for_teacher(teacher_user_id)
    return jsonify({
        'students': students,
        'teacher_id': teacher_user_id,
        'active_page': 'chat'
    })

@app.route('/teacher/schedule')
@login_required
def teacher_schedule():
    teacher_user_id = session['user_id']
    students = get_students_for_teacher(teacher_user_id)
    calendar_events = []
    upcoming_classes = []
    return jsonify({
        'calendar_events': calendar_events,
        'upcoming_classes': upcoming_classes,
        'students': students,
        'active_page': 'schedule'
    })

@app.route('/teacher/payments')
@login_required
def teacher_payments():
    payments = []
    return jsonify({
        'payments': payments,
        'active_page': 'payments'
    })

@app.route('/teacher/profile')
@login_required
def teacher_profile():
    teacher_user_id = session['user_id']
    teacher = {
        'name': session.get('teacher_name', 'Teacher'),
        'email': session.get('teacher_email', 'teacher@example.com'),
        'contact': 'N/A',
        'role': 'Teacher',
        'joined': 'N/A'
    }
    return jsonify({
        'teacher': teacher,
        'active_page': 'profile'
    })

@app.route('/fetch_messages', methods=['GET'])
def fetch_messages():
    """Fetch messages for real-time updates."""
    teacher_id = request.args.get('teacher_id')
    student_id = request.args.get('student_id')
    messages = Conversation.query.filter_by(teacher_id=teacher_id, student_id=student_id).order_by(Conversation.timestamp).all()

    return jsonify([
        {
            'message': msg.message,
            'sender_role': msg.sender_role,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
        for msg in messages
    ])



@app.route('/financial_management', methods=['GET', 'POST'])
@login_required
def financial_management():
    """Enhanced Financial Management page."""
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)
        filter_type = request.args.get('type', '')
        filter_category = request.args.get('category', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        min_amount = request.args.get('min_amount', '')
        max_amount = request.args.get('max_amount', '')
        page = int(request.args.get('page', 1))
        per_page = 10

        try:
            # Only show students who are also users with the 'student' role
            cursor.execute("""
                SELECT s.id, u.name, s.contact, s.total_classes, s.remaining_classes, s.payment_status, s.next_payment_date, u.email
                FROM students s
                JOIN users u ON s.user_id = u.id
                WHERE u.role = 'student'
            """)
            students = cursor.fetchall()

            cursor.execute("SELECT id, name FROM users WHERE role = 'teacher'")
            instructors = cursor.fetchall()

            # --- Revenue and Expense Filtering ---
            query = ""
            params = []

            def add_filter_clauses(base_query, filters):
                clauses = []
                params = []
                if filters.get('category'):
                    clauses.append("category = %s")
                    params.append(filters['category'])
                if filters.get('start_date'):
                    clauses.append("date >= %s")
                    params.append(filters['start_date'])
                if filters.get('end_date'):
                    clauses.append("date <= %s")
                    params.append(filters['end_date'])
                if filters.get('min_amount'):
                    clauses.append("amount >= %s")
                    params.append(filters['min_amount'])
                if filters.get('max_amount'):
                    clauses.append("amount <= %s")
                    params.append(filters['max_amount'])
                if clauses:
                    base_query += " WHERE " + " AND ".join(clauses)
                return base_query, params

            filters = {
                'category': filter_category,
                'start_date': start_date,
                'end_date': end_date,
                'min_amount': min_amount,
                'max_amount': max_amount
            }

            if filter_type == 'revenue':
                query, filter_params = add_filter_clauses("SELECT 'revenue' AS type, date, amount, category FROM revenue", filters)
                query += " ORDER BY date DESC LIMIT %s OFFSET %s"
                filter_params.extend([per_page, (page - 1) * per_page])
                params = filter_params
            elif filter_type == 'expense':
                query, filter_params = add_filter_clauses("SELECT 'expense' AS type, date, amount, category FROM expenses", filters)
                query += " ORDER BY date DESC LIMIT %s OFFSET %s"
                filter_params.extend([per_page, (page - 1) * per_page])
                params = filter_params
            else:
                # For 'all', apply filters to both revenue and expenses and union
                rev_query, rev_params = add_filter_clauses("SELECT 'revenue' AS type, date, amount, category FROM revenue", filters)
                exp_query, exp_params = add_filter_clauses("SELECT 'expense' AS type, date, amount, category FROM expenses", filters)
                query = f"{rev_query} UNION ALL {exp_query} ORDER BY date DESC LIMIT %s OFFSET %s"
                params = rev_params + exp_params + [per_page, (page - 1) * per_page]

            cursor.execute(query, params)
            records = cursor.fetchall()

            # For summary cards, do not filter by pagination
            cursor.execute("SELECT SUM(amount) AS total_revenue FROM revenue")
            total_revenue = cursor.fetchone()['total_revenue'] or 0

            cursor.execute("SELECT SUM(amount) AS total_expenses FROM expenses")
            total_expenses = cursor.fetchone()['total_expenses'] or 0

            net_profit = total_revenue - total_expenses

            # Monthly Revenue
            cursor.execute("SELECT SUM(amount) AS monthly_revenue FROM revenue WHERE MONTH(date) = MONTH(CURDATE()) AND YEAR(date) = YEAR(CURDATE())")
            monthly_revenue = cursor.fetchone()['monthly_revenue'] or 0

            # Fetch all expenses and revenues for tables, with filters
            exp_query, exp_params = add_filter_clauses("SELECT * FROM expenses", filters)
            exp_query += " ORDER BY date DESC LIMIT 100"
            cursor.execute(exp_query, exp_params)
            expenses = cursor.fetchall()

            rev_query, rev_params = add_filter_clauses("SELECT * FROM revenue", filters)
            rev_query += " ORDER BY date DESC LIMIT 100"
            cursor.execute(rev_query, rev_params)
            revenues = cursor.fetchall()

            # Fetch all reserves for the reserves table
            cursor.execute("SELECT * FROM reserves ORDER BY date DESC LIMIT 100")
            reserves = cursor.fetchall()

            return jsonify({
                'students': students,
                'records': records,
                'total_revenue': total_revenue,
                'total_expenses': total_expenses,
                'net_profit': net_profit,
                'monthly_revenue': monthly_revenue,
                'filter_type': filter_type,
                'filter_category': filter_category,
                'start_date': start_date,
                'end_date': end_date,
                'min_amount': min_amount,
                'max_amount': max_amount,
                'page': page,
                'per_page': per_page,
                'instructors': instructors,
                'expenses': expenses,
                'revenues': revenues,
                'reserves': reserves
            })
        except mysql.connector.Error as err:
            print(f"Database error in financial_management: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/update_payment_status/<int:student_id>', methods=['POST'])
def update_payment_status(student_id):
    """Update the payment status of a student."""
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor()
        payment_status = sanitize_input(request.form.get('payment_status'))
        try:
            query = "UPDATE students SET payment_status = %s WHERE id = %s"
            cursor.execute(query, (payment_status, student_id))
            conn.commit()
            return redirect(url_for('financial_management'))
        except mysql.connector.Error as err:
            print(f"Database error in update_payment_status: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/update_next_payment_date/<int:student_id>', methods=['POST'])
def update_next_payment_date(student_id):
    """Update the next payment date for a student."""
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor()
        next_payment_date = request.form.get('next_payment_date')
        try:
            query = "UPDATE students SET next_payment_date = %s WHERE id = %s"
            cursor.execute(query, (next_payment_date, student_id))
            conn.commit()
            return redirect(url_for('financial_management'))
        except mysql.connector.Error as err:
            print(f"Database error in update_next_payment_date: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/send_fee_notification/<int:student_id>', methods=['POST'])
def send_fee_notification(student_id):
    """Send a fee notification email to a student."""
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT users.email, users.name
                FROM users
                JOIN students ON users.id = students.user_id
                WHERE students.id = %s
            """, (student_id,))
            student = cursor.fetchone()

            if student:
                subject = "Fee Payment Reminder - FRENCH.GTA"
                body = f"""
Dear {student['name']},

This is a friendly reminder regarding your upcoming fee payment for your French classes at FRENCH.GTA.

Please ensure your payment is made by the due date to continue your learning without interruption.

Thank you for your continued enrollment.

Best regards,
FRENCH.GTA Team
"""
                send_email(to_email=student['email'], subject=subject, body=body)
                return redirect(url_for('student_management', success=f"Fee notification sent to {student['name']}"))
            else:
                return "Student not found", 404
        except mysql.connector.Error as err:
            print(f"Database error in send_fee_notification: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))
@app.route('/teacher_punch', methods=['POST'])
def teacher_punch():
    """Handle teacher punch in/out with email option."""
    if 'role' in session and session['role'] == 'teacher':
        teacher_user_id = session['user_id']  # Get the user ID from the session
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)
        try:
            # Validate that the teacher exists in the `teachers` table
            cursor.execute("SELECT id, name FROM teachers WHERE user_id = %s", (teacher_user_id,))
            teacher = cursor.fetchone()
            if not teacher:
                return "Teacher not found. Please contact the administrator.", 404

            teacher_id = teacher['id']  # Get the teacher's ID
            teacher_name = teacher['name']
            action = request.form.get('action')
            email_option = request.form.get('email_option', 'none')

            if action == 'in':
                # Deduct one class from each student's remaining classes
                cursor.execute("""
                    UPDATE students
                    SET remaining_classes = remaining_classes - 1
                    WHERE teacher_id = %s AND remaining_classes > 0
                """, (teacher_id,))
                conn.commit()

                # Fetch students assigned to the teacher
                cursor.execute("""
                    SELECT users.email AS student_email, users.name AS student_name
                    FROM students
                    JOIN users ON students.user_id = users.id
                    WHERE students.teacher_id = %s
                """, (teacher_id,))
                students = cursor.fetchall()

                # Send emails based on email_option
                if email_option in ('students', 'all'):
                    for student in students:
                        student_email_body = f"""
                        Dear {student['student_name']},

                        Your instructor {teacher_name} has clocked in and is ready for your class. Please prepare accordingly.

                        Best regards,
                        FRENCH.GTA Team
                        """
                        send_email(to_email=student['student_email'], subject="Class Notification", body=student_email_body)

                if email_option in ('self', 'all'):
                    teacher_email_body = f"""
                    Dear {teacher_name},

                    You have successfully clocked in. Your students have been notified.

                    Best regards,
                    FRENCH.GTA Team
                    """
                    send_email(to_email=session['email'], subject="Clock-In Confirmation", body=teacher_email_body)

                query = "INSERT INTO punch_records (teacher_id, punch_in) VALUES (%s, NOW())"
                cursor.execute(query, (teacher_id,))
                conn.commit()
                session['shift_started'] = True  # Mark shift as started
                return redirect(url_for('teacher_portal'))
            elif action == 'out':
                query = "UPDATE punch_records SET punch_out = NOW() WHERE teacher_id = %s AND punch_out IS NULL"
                cursor.execute(query, (teacher_id,))
                conn.commit()
                session.pop('shift_started', None)  # Clear shift started flag
                return redirect(url_for('teacher_portal'))
            else:
                return "Invalid action", 400
        except mysql.connector.Error as err:
            print(f"Database error in teacher_punch: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))


@app.route('/teacher_add_material', methods=['POST'])
def teacher_add_material():
    """Add material shared by the teacher."""
    if 'role' in session and session['role'] == 'teacher':
        teacher_id = session['user_id']
        title = request.form.get('title')
        link = request.form.get('link')
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor()
        try:
            query = "INSERT INTO materials (teacher_id, title, link) VALUES (%s, %s, %s)"
            cursor.execute(query, (teacher_id, title, link))
            conn.commit()
            return redirect(url_for('teacher_portal'))
        except mysql.connector.Error as err:
            print(f"Database error in teacher_add_material: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))


@app.route('/teacher_send_message', methods=['POST'])
def teacher_send_message():
    """Send a message to a student."""
    if 'role' in session and session['role'] == 'teacher':
        teacher_id = session['user_id']
        student_id = request.form.get('student_id')
        message = request.form.get('message')

        # Debugging: Log the received data
        print(f"Received data: teacher_id={teacher_id}, student_id={student_id}, message={message}")

        if not student_id or not message:
            print("Error: Missing student_id or message.")
            return jsonify({'error': 'Student ID and message are required'}), 400

        try:
            # Save the message to the database
            new_message = Conversation(
                teacher_id=teacher_id,
                student_id=student_id,
                message=message,
                sender_role='teacher'
            )
            db.session.add(new_message)
            db.session.commit()

            print("Message saved successfully.")
            return jsonify({'success': True}), 200
        except Exception as e:
            # Log the error for debugging
            print(f"Error saving message: {repr(e)}")
            return jsonify({'error': 'Failed to save message'}), 500
    print("Error: Unauthorized access.")
    return jsonify({'error': 'Unauthorized'}), 403


@app.route('/teacher_management', methods=['GET', 'POST'])
@login_required
def teacher_management():
    """Teacher Management page."""
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)
        teacher_to_edit = None
        if request.method == 'POST':
            # ...existing code...
            pass

        try:
            cursor.execute("""
                SELECT teachers.*, users.email AS user_email
                FROM teachers
                LEFT JOIN users ON teachers.user_id = users.id
            """)
            teachers = cursor.fetchall()

            cursor.execute("SELECT * FROM users WHERE role = 'student'")
            students = cursor.fetchall()  # Fetch all students for assignment

            # Fetch punch-in/out records
            cursor.execute("""
                SELECT pr.id, t.name AS teacher_name, pr.punch_in, pr.punch_out
                FROM punch_records pr
                JOIN teachers t ON pr.teacher_id = t.id
                ORDER BY pr.punch_in DESC
            """)
            punch_records_raw = cursor.fetchall()

            import pytz
            from datetime import datetime
            def to_tz(dt, tz_str):
                if not dt:
                    return ''
                if isinstance(dt, str):
                    dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
                utc = pytz.utc.localize(dt) if dt.tzinfo is None else dt
                return utc.astimezone(pytz.timezone(tz_str)).strftime('%Y-%m-%d %H:%M:%S')

            punch_records = []
            for rec in punch_records_raw:
                punch_in = rec['punch_in']
                punch_out = rec['punch_out']
                punch_records.append({
                    'id': rec['id'],
                    'teacher_name': rec['teacher_name'],
                    'punch_in_est': to_tz(punch_in, 'America/New_York') if punch_in else '',
                    'punch_in_ist': to_tz(punch_in, 'Asia/Kolkata') if punch_in else '',
                    'punch_out_est': to_tz(punch_out, 'America/New_York') if punch_out else '',
                    'punch_out_ist': to_tz(punch_out, 'Asia/Kolkata') if punch_out else '',
                })

            return jsonify({'teachers': teachers, 'students': students, 'teacher_to_edit': teacher_to_edit, 'punch_records': punch_records})
        except mysql.connector.Error as err:
            print(f"Database error in teacher_management: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/teacher_profile/<int:teacher_id>', methods=['GET'])
def view_teacher_profile(teacher_id):
    """Display the profile of a specific teacher."""
    conn = connect_db()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch teacher details
        cursor.execute("""
            SELECT teachers.*, users.email AS user_email
            FROM teachers
            LEFT JOIN users ON teachers.user_id = users.id
            WHERE teachers.id = %s
        """, (teacher_id,))
        teacher = cursor.fetchone()
        if not teacher:
            return "Teacher not found", 404

        return jsonify({'teacher': teacher})
    except mysql.connector.Error as err:
        print(f"Database error in teacher_profile: {repr(err)}")
        return f"Database error: {repr(err)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/assign_student', methods=['POST'])
def assign_student():
    """Assign a student to a teacher and send confirmation emails."""
    if 'role' in session and session['role'] == 'admin':
        teacher_id = request.form.get('teacher_id')
        student_id = request.form.get('student_id')

        # Debugging: Log the IDs being processed
        print(f"Assigning student ID {student_id} to teacher ID {teacher_id}")

        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)
        try:
            # Fetch teacher details
            cursor.execute("SELECT name, email FROM teachers WHERE id = %s", (teacher_id,))
            teacher = cursor.fetchone()
            if not teacher:
                print(f"Teacher with ID {teacher_id} not found.")
                return f"Teacher with ID {teacher_id} not found.", 404

            # Fetch student details
            cursor.execute("""
                SELECT users.name AS name, users.email AS email
                FROM users
                JOIN students ON users.id = students.user_id
                WHERE students.id = %s
            """, (student_id,))
            student = cursor.fetchone()
            if not student:
                print(f"Student with ID {student_id} not found.")
                return f"Student with ID {student_id} not found.", 404

            # Update the student's teacher_id
            query = "UPDATE students SET teacher_id = %s WHERE id = %s"
            cursor.execute(query, (teacher_id, student_id))
            conn.commit()

            # Send confirmation emails
            admin_email = app.config['MAIL_DEFAULT_SENDER']
            teacher_email_body = f"""
            Dear {teacher['name']},
            
            A new student, {student['name']}, has been assigned to you. Please log in to your portal to view their details and start scheduling classes.
            
            Best regards,
            Admin
            """
            student_email_body = f"""
            Dear {student['name']},
            
            You have been assigned to {teacher['name']} as your teacher. Please log in to your portal to view their details and start your classes.
            
            Best regards,
            Admin
            """
            admin_email_body = f"""
            Admin Notification:
            
            Student {student['name']} has been successfully assigned to Teacher {teacher['name']}.
            """

            # Send emails
            send_email(to_email=teacher['email'], subject="New Student Assigned", body=teacher_email_body)
            send_email(to_email=student['email'], subject="Teacher Assigned", body=student_email_body)
            send_email(to_email=admin_email, subject="Student Assignment Confirmation", body=admin_email_body)

            return redirect(url_for('teacher_management'))
        except mysql.connector.Error as err:
            print(f"Database error in assign_student: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/convert_query_to_student/<int:query_id>', methods=['POST'])
def convert_query_to_student(query_id):
    """Convert a query to a student."""
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)
        try:
            # Fetch the query details
            cursor.execute("SELECT * FROM queries WHERE id = %s", (query_id,))
            query = cursor.fetchone()
            if not query:
                return "Query not found", 404

            # Insert the query details into the students table
            cursor.execute("""
                INSERT INTO students (name, contact, nationality, availability, notes, teacher_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (query['name'], query['contact'], query['nationality'], query['availability'], query['notes'], query['instructor_id']))
            conn.commit()

            # Optionally delete the query after conversion
            cursor.execute("DELETE FROM queries WHERE id = %s", (query_id,))
            conn.commit()

            return redirect(url_for('query_management'))
        except mysql.connector.Error as err:
            print(f"Database error in convert_query_to_student: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/query_management', methods=['GET', 'POST'])
@login_required
def query_management():
    """Query Management page."""
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)
        query_to_edit = None
        if request.method == 'POST':
            try:
                query_id = request.form.get('query_id')
                name = sanitize_input(request.form.get('name'))
                contact = sanitize_input(request.form.get('contact'))
                location = sanitize_input(request.form.get('location'))
                availability = sanitize_input(request.form.get('availability'))
                nationality = sanitize_input(request.form.get('nationality'))
                pitched_for = sanitize_input(request.form.get('pitched_for'))
                type_of_source = sanitize_input(request.form.get('type_of_source'))
                imm_status = sanitize_input(request.form.get('imm_status'))
                work_permit = sanitize_input(request.form.get('work_permit'))
                notes = sanitize_input(request.form.get('notes'))
                demo_date = request.form.get('demo_date')
                demo_instructor = sanitize_input(request.form.get('demo_instructor'))
                demo_instructor_2 = sanitize_input(request.form.get('demo_instructor_2'))
                status = sanitize_input(request.form.get('status'))
                instructor_id = sanitize_input(request.form.get('instructor_id'))
                instructor_assigned = sanitize_input(request.form.get('instructor_assigned'))
                time_of_lead = request.form.get('time_of_lead')
                qualification = sanitize_input(request.form.get('qualification'))
                current_level = sanitize_input(request.form.get('current_level'))

                # Validate required fields
                if not name or not contact or not type_of_source or not status:
                    return "Missing required fields", 400

                if query_id:  # Update existing query
                    query = """
                        UPDATE queries
                        SET name = %s, contact = %s, location = %s, availability = %s,
                            nationality = %s, pitched_for = %s, type_of_source = %s,
                            imm_status = %s, work_permit = %s, notes = %s, demo_date = %s,
                            demo_instructor = %s, demo_instructor_2 = %s, status = %s,
                            instructor_id = %s, instructor_assigned = %s, time_of_lead = %s,
                            qualification = %s, current_level = %s
                        WHERE id = %s
                    """
                    cursor.execute(query, (name, contact, location, availability, nationality,
                                           pitched_for, type_of_source, imm_status, work_permit,
                                           notes, demo_date, demo_instructor, demo_instructor_2,
                                           status, instructor_id, instructor_assigned, time_of_lead,
                                           qualification, current_level, query_id))
                else:  # Add new query
                    query = """
                        INSERT INTO queries (name, contact, location, availability, nationality,
                                             pitched_for, type_of_source, imm_status, work_permit,
                                             notes, demo_date, demo_instructor, demo_instructor_2,
                                             status, instructor_id, instructor_assigned, time_of_lead,
                                             qualification, current_level)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(query, (name, contact, location, availability, nationality,
                                           pitched_for, type_of_source, imm_status, work_permit,
                                           notes, demo_date, demo_instructor, demo_instructor_2,
                                           status, instructor_id, instructor_assigned, time_of_lead,
                                           qualification, current_level))
                conn.commit()
            except mysql.connector.Error as err:
                print(f"Database error in query_management: {repr(err)}")
                return f"Database error: {repr(err)}", 500
            except Exception as e:
                print(f"Error in query_management: {repr(e)}")
                return f"Error: {repr(e)}", 500

        if request.args.get('edit_query_id'):
            try:
                query_id = request.args.get('edit_query_id')
                cursor.execute("SELECT * FROM queries WHERE id = %s", (query_id,))
                query_to_edit = cursor.fetchone()
            except mysql.connector.Error as err:
                print(f"Database error in fetching query: {repr(err)}")
                return f"Database error: {repr(err)}", 500

        if request.args.get('delete_query_id'):
            try:
                query_id = request.args.get('delete_query_id')
                cursor.execute("DELETE FROM queries WHERE id = %s", (query_id,))
                conn.commit()
            except mysql.connector.Error as err:
                print(f"Database error in deleting query: {repr(err)}")
                return f"Database error: {repr(err)}", 500

        try:
            cursor.execute("SELECT * FROM queries")
            queries = cursor.fetchall()
            return jsonify({'queries': queries, 'query_to_edit': query_to_edit})
        except mysql.connector.Error as err:
            print(f"Database error in query_management: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/schedule_class', methods=['POST'])
def schedule_class():
    """Schedule a class."""
    if 'role' in session and session['role'] == 'teacher':
        teacher_user_id = session['user_id']
        class_name = request.form.get('class_name')
        class_date = request.form.get('class_date')
        class_time = request.form.get('class_time')
        subject = request.form.get('subject')
        timezone = request.form.get('timezone', 'Asia/Kolkata')
        student_ids = request.form.getlist('students[]') or request.form.getlist('students')

        from datetime import datetime
        import pytz
        # Combine date and time, localize to selected timezone, convert to UTC
        dt_str = f"{class_date} {class_time}"
        local_tz = pytz.timezone(timezone)
        local_dt = local_tz.localize(datetime.strptime(dt_str, '%Y-%m-%d %H:%M'))
        utc_dt = local_dt.astimezone(pytz.utc)
        class_date_utc = utc_dt.strftime('%Y-%m-%d')
        class_time_utc = utc_dt.strftime('%H:%M:%S')

        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor()
        try:
            # Insert the class schedule in UTC
            query = """
                INSERT INTO schedules (teacher_id, class_name, class_date, class_time, subject)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(query, (teacher_user_id, class_name, class_date_utc, class_time_utc, subject))
            schedule_id = cursor.lastrowid

            # Link students to the schedule
            for student_id in student_ids:
                query = "INSERT INTO schedule_students (schedule_id, student_id) VALUES (%s, %s)"
                cursor.execute(query, (schedule_id, student_id))

            conn.commit()
            return redirect(url_for('teacher_portal'))
        except mysql.connector.Error as err:
            print(f"Database error in schedule_class: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/start_class/<int:schedule_id>', methods=['POST'])
def start_class(schedule_id):
    """Start a class."""
    if 'role' in session and session['role'] == 'teacher':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor()
        try:
            query = "UPDATE schedules SET status = 'in_progress' WHERE id = %s"
            cursor.execute(query, (schedule_id,))
            conn.commit()
            return redirect(url_for('teacher_portal'))
        except mysql.connector.Error as err:
            print(f"Database error in start_class: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/end_class/<int:schedule_id>', methods=['POST'])
def end_class(schedule_id):
    """End a class."""
    if 'role' in session and session['role'] == 'teacher':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor()
        try:
            query = "UPDATE schedules SET status = 'completed' WHERE id = %s"
            cursor.execute(query, (schedule_id,))
            conn.commit()
            return redirect(url_for('teacher_portal'))
        except mysql.connector.Error as err:
            print(f"Database error in end_class: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/approve_class_report/<int:report_id>', methods=['POST'])
def approve_class_report(report_id):
    """Approve a class report."""
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor()
        try:
            query = "UPDATE schedules SET status = 'approved' WHERE id = %s"
            cursor.execute(query, (report_id,))
            conn.commit()
            return redirect(url_for('admin_portal'))
        except mysql.connector.Error as err:
            print(f"Database error in approve_class_report: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/blog.html', methods=['GET'])
def blog():
    """Blog Page."""
    conn = connect_db()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor(dictionary=True)
    filter_title = request.args.get('filter_title', '')
    filter_category = request.args.get('filter_category', '')

    try:
        # Fetch blogs with optional filtering
        query = "SELECT id, title, slug, category, content, image FROM blogs WHERE 1=1"
        params = []

        if filter_title:
            query += " AND title LIKE %s"
            params.append(f"%{filter_title}%")
        if filter_category:
            query += " AND category = %s"
            params.append(filter_category)

        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        blogs = cursor.fetchall()
        return jsonify({'blogs': blogs, 'filter_title': filter_title, 'filter_category': filter_category})
    except mysql.connector.Error as err:
        print(f"Database error in blog: {repr(err)}")
        return f"Database error: {repr(err)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/blog_post/<string:category>/<string:slug>')
def blog_post(category, slug):
    """Display a specific blog post."""
    blog = Blog.query.filter_by(category=category, slug=slug).first()
    if not blog:
        return "Blog not found", 404
    return jsonify({'blog': {
        'id': blog.id,
        'title': blog.title,
        'slug': blog.slug,
        'category': blog.category,
        'content': blog.content,
        'image': blog.image
    }})

@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    """Handle student deletion."""
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor()
        try:
            # Ensure you are only deleting users with the 'student' role
            cursor.execute("DELETE FROM users WHERE id = %s AND role = 'student'", (student_id,))
            conn.commit()
            return redirect(url_for('student_management'))
        except mysql.connector.Error as err:
            print(f"Database error in delete_student: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/admin_delete_blog/<int:blog_id>', methods=['POST'])
def admin_delete_blog(blog_id):
    """Delete a blog."""
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor()
        try:
            query = "DELETE FROM blogs WHERE id = %s"
            cursor.execute(query, (blog_id,))
            conn.commit()
            return redirect(url_for('admin_portal'))
        except mysql.connector.Error as err:
            print(f"Database error in admin_delete_blog: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()

@app.route('/admin_edit_blog/<int:blog_id>', methods=['GET', 'POST'])
def admin_edit_blog_page(blog_id):
    """Render the page to edit a specific blog."""
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            # Update the blog
            title = sanitize_input(request.form['title'])
            content = sanitize_html(request.form['content'])
            image = None
            if 'image' in request.files:
                image_file = request.files['image']
                if image_file and allowed_file(image_file.filename):
                    image_filename = secure_filename(image_file.filename)
                    image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                    image = image_filename
            try:
                if image:
                    query = "UPDATE blogs SET title = %s, content = %s, image = %s WHERE id = %s"
                    cursor.execute(query, (title, content, image, blog_id))
                else:
                    query = "UPDATE blogs SET title = %s, content = %s WHERE id = %s"
                    cursor.execute(query, (title, content, blog_id))
                conn.commit()
                return redirect(url_for('blog_management'))
            except mysql.connector.Error as err:
                print(f"Database error in admin_edit_blog_page: {repr(err)}")
                return f"Database error: {repr(err)}", 500

        try:
            cursor.execute("SELECT * FROM blogs WHERE id = %s", (blog_id,))
            blog = cursor.fetchone()
            if blog:
                return jsonify({'blog': blog})
            else:
                return "Blog not found", 404
        except mysql.connector.Error as err:
            print(f"Database error in admin_edit_blog_page: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()

@app.route('/api/get_blog/<int:blog_id>', methods=['GET'])
def get_blog(blog_id):
    """API to fetch a blog by its ID."""
    conn = connect_db()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, title, content, image FROM blogs WHERE id = %s", (blog_id,))
        blog = cursor.fetchone()
        if blog:
            return jsonify(blog), 200
        else:
            return jsonify({'error': 'Blog not found'}), 404
    except mysql.connector.Error as err:
        print(f"Database error in get_blog: {repr(err)}")
        return jsonify({'error': 'Database error'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/blog/<int:blog_id>', methods=['GET'], endpoint='api_get_blog')
def api_get_blog(blog_id):
    """API to fetch blog details by ID."""
    conn = connect_db()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, title, content, image FROM blogs WHERE id = %s", (blog_id,))
        blog = cursor.fetchone()
        if blog:
            return jsonify(blog), 200
        else:
            return jsonify({'error': 'Blog not found'}), 404
    except mysql.connector.Error as err:
        print(f"Database error in api_get_blog: {repr(err)}")
        return jsonify({'error': 'Database error'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/blog_management', methods=['GET', 'POST'])
@login_required
def blog_management():
    """Blog Management page."""
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            # Add a new blog
            title = sanitize_input(request.form['title'])
            content = sanitize_html(request.form['content'])  # Ensure content is sanitized
            image = None
            if 'image' in request.files:
                image_file = request.files['image']
                if image_file and allowed_file(image_file.filename):
                    image_filename = secure_filename(image_file.filename)
                    image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                    image = image_filename
            try:
                query = "INSERT INTO blogs (title, content, image) VALUES (%s, %s, %s)"
                cursor.execute(query, (title, content, image))
                conn.commit()
            except mysql.connector.Error as err:
                print(f"Database error in blog_management: {repr(err)}")
                return f"Database error: {repr(err)}", 500
        try:
            cursor.execute("SELECT * FROM blogs")
            blogs = cursor.fetchall()
            return jsonify({'blogs': blogs})
        except mysql.connector.Error as err:
            print(f"Database error in blog_management: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))



# --- Student Management ---
@app.route('/student_management', methods=['GET', 'POST'])
@login_required
def student_management():
    """Student Management page."""
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500

        cursor = conn.cursor(dictionary=True)
        student_to_edit = None
        if request.method == 'POST':
            student_id = request.form.get('student_id')
            name = sanitize_input(request.form['name'])
            contact = sanitize_input(request.form['contact'])
            teacher_id = int(request.form['teacher_id'])
            user_id = int(request.form['user_id'])  # Use 'id' if it's the primary key
            total_classes = int(request.form['total_classes'])
            remaining_classes = int(request.form['remaining_classes'])
            nationality = sanitize_input(request.form['nationality'])
            availability = sanitize_input(request.form['availability'])
            notes = sanitize_input(request.form['notes'])

            try:
                if student_id:  # Update existing student
                    query = """
                        UPDATE students
                        SET name = %s, contact = %s, teacher_id = %s, user_id = %s,
                            total_classes = %s, remaining_classes = %s,
                            nationality = %s, availability = %s, notes = %s
                        WHERE id = %s
                    """
                    cursor.execute(query, (name, contact, teacher_id, user_id, total_classes,
                                           remaining_classes, nationality, availability, notes, student_id))
                else:  # Add new student
                    query = """
                        INSERT INTO students (name, contact, teacher_id, user_id, total_classes,
                                             remaining_classes, nationality, availability, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(query, (name, contact, teacher_id, user_id, total_classes,
                                           remaining_classes, nationality, availability, notes))
                conn.commit()
            except mysql.connector.Error as err:
                print(f"Database error in student_management: {repr(err)}")
                return f"Database error: {repr(err)}", 500

        try:
            cursor.execute("""
                SELECT students.*, users.email AS user_email, teachers.name AS teacher_name
                FROM students
                LEFT JOIN users ON students.user_id = users.id
                LEFT JOIN teachers ON students.teacher_id = teachers.id
            """)
            students = cursor.fetchall()

            cursor.execute("SELECT * FROM teachers")
            teachers = cursor.fetchall()
            cursor.execute("SELECT * FROM users WHERE role = 'student'")
            users = cursor.fetchall()
            return jsonify({'students': students, 'teachers': teachers, 'users': users, 'student_to_edit': student_to_edit})
        except mysql.connector.Error as err:
            print(f"Database error in student_management: {repr(err)}")
            return f"Database error: {repr(err)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/student_profile/<int:student_id>', methods=['GET'])
def student_profile(student_id):
    """Display the profile of a specific student."""
    conn = connect_db()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch student details
        cursor.execute("""
            SELECT students.*, users.email AS user_email, teachers.name AS teacher_name
            FROM students
            LEFT JOIN users ON students.user_id = users.id
            LEFT JOIN teachers ON students.teacher_id = teachers.id
            WHERE students.id = %s
        """, (student_id,))
        student = cursor.fetchone()
        if not student:
            return "Student not found", 404

        return jsonify({'student': student})
    except mysql.connector.Error as err:
        print(f"Database error in student_profile: {repr(err)}")
        return f"Database error: {repr(err)}", 500
    finally:
        cursor.close()
        conn.close()

# --- Public Routes ---
@app.route('/')
@app.route('/index')
def index():
    # Fetch approved testimonials for the homepage slider
    conn = connect_db()
    if conn is None:
        return jsonify({"testimonials": []})
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM testimonials WHERE is_approved=1 ORDER BY date_submitted DESC")
        testimonials = cursor.fetchall()
        return jsonify({"testimonials": testimonials})
    except Exception as e:
        print(f"Error in index testimonials: {repr(e)}")
        return jsonify({"testimonials": []})
    finally:
        cursor.close()
        conn.close()

@app.route('/home')
def home():
    """Home page."""
    return redirect(url_for('index'))

@app.route('/about')
def about():
    """About page."""
    return jsonify({"message": "About page content."})

@app.route('/contact')
def contact():
    """Contact page."""
    return jsonify({"message": "Contact page content."})

@app.route('/services')
def services():
    """Services page."""
    return jsonify({"message": "Services page content."})

@app.route('/update_blog_rank/<int:blog_id>', methods=['POST'])
def update_blog_rank(blog_id):
    """Update the rank of a blog."""
    new_rank = request.form.get('rank')
    if not new_rank or not new_rank.isdigit():
        return redirect(url_for('admin_portal', error="Invalid rank value"))

    conn = connect_db()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor()
    try:
        query = "UPDATE blogs SET rank = %s WHERE id = %s"
        cursor.execute(query, (int(new_rank), blog_id))
        conn.commit()
        return redirect(url_for('admin_portal', success="Rank updated successfully"))
    except mysql.connector.Error as err:
        print(f"Database error in update_blog_rank: {repr(err)}")
        return f"Database error: {repr(err)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/add_revenue', methods=['POST'])
def add_revenue():
    """Add a new revenue entry."""
    student_id = request.form.get('student_id')
    classes_per_month = int(request.form.get('classes_per_month'))
    amount = float(request.form.get('amount'))

    conn = connect_db()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Debugging: Log the student_id being passed
        print(f"Received student_id: {student_id}")

        # Verify if the student exists in the users table
        cursor.execute("SELECT * FROM users WHERE id = %s AND role = 'student'", (student_id,))
        user = cursor.fetchone()
        print(f"User query result: {user}")

        if not user:
            return "Student not found in users table. Please ensure the student exists.", 404

        # Verify if the student exists in the students table
        cursor.execute("SELECT * FROM students WHERE user_id = %s", (student_id,))
        student_record = cursor.fetchone()
        print(f"Student table query result: {student_record}")

        if not student_record:
            return "Student not found in students table. Please ensure the student is linked to the users table.", 404

        # Fetch student and teacher details
        cursor.execute("""
            SELECT users.name AS student_name, teachers.name AS teacher_name
            FROM users
            JOIN students ON users.id = students.user_id
            JOIN teachers ON students.teacher_id = teachers.id
            WHERE users.id = %s
        """, (student_id,))
        student = cursor.fetchone()

        # Debugging: Log the query result
        print(f"Student and teacher query result: {student}")

        # Check if the student exists
        if not student:
            return "Student not found in students table. Please ensure the student is linked to a teacher.", 404

        # Add revenue entry
        query = """
            INSERT INTO revenue (student_name, classes_per_month, teacher_name, amount, category)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (student['student_name'], classes_per_month, student['teacher_name'], amount, 'Student Fee'))
        conn.commit()

        return redirect(url_for('financial_management'))
    except mysql.connector.Error as err:
        print(f"Database error in add_revenue: {repr(err)}")
        return f"Database error: {repr(err)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/add_expense', methods=['POST'])
def add_expense():
    """Add a new expense entry."""
    expense_name = request.form.get('expense_name')
    category = request.form.get('category')
    type_ = request.form.get('type')
    name = request.form.get('name') or None
    amount = float(request.form.get('amount'))

    conn = connect_db()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor()
    try:
        query = """
            INSERT INTO expenses (expense_name, category, type, name, amount)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (expense_name, category, type_, name, amount))
        conn.commit()

        return redirect(url_for('financial_management'))
    except mysql.connector.Error as err:
        print(f"Database error in add_expense: {repr(err)}")
        return f"Database error: {repr(err)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/add_student_and_revenue', methods=['POST'])
def add_student_and_revenue():
    """Add a new student and their fee to the revenue table."""
    name = sanitize_input(request.form.get('name'))
    contact = sanitize_input(request.form['contact'])
    teacher_id = int(request.form['teacher_id'])
    classes_per_month = int(request.form.get('classes_per_month'))
    amount = float(request.form.get('amount'))

    conn = connect_db()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor(dictionary=True)
    try:
        # Verify if the teacher exists
        cursor.execute("SELECT * FROM teachers WHERE id = %s", (teacher_id,))
        teacher = cursor.fetchone()
        print(f"Teacher query result: {teacher}")

        if not teacher:
            return "Teacher not found. Please ensure the teacher exists in the database.", 404

        # Add student to the students table
        query = """
            INSERT INTO students (name, contact, teacher_id, total_classes, remaining_classes)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (name, contact, teacher_id, classes_per_month, classes_per_month))
        student_id = cursor.lastrowid

        # Add revenue entry
        query = """
            INSERT INTO revenue (student_name, classes_per_month, teacher_name, amount, category)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (name, classes_per_month, teacher['name'], amount, 'Student Fee'))
        conn.commit()

        return redirect(url_for('financial_management'))
    except mysql.connector.Error as err:
        print(f"Database error in add_student_and_revenue: {repr(err)}")
        return f"Database error: {repr(err)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/view_instructor/<int:teacher_id>', methods=['GET'])
def view_instructor(teacher_id):
    """View teacher details."""
    conn = connect_db()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM teachers WHERE id = %s", (teacher_id,))
        teacher = cursor.fetchone()
        if not teacher:
            return "Teacher not found", 404
        return jsonify({'teacher': teacher})
    except mysql.connector.Error as err:
        print(f"Database error in view_instructor: {repr(err)}")
        return f"Database error: {repr(err)}", 500
    finally:
        cursor.close()
        conn.close()

@app.context_processor
def inject_current_year():
    """Inject the current year into all templates."""
    return {'current_year': datetime.now().year}

@app.route('/demo-registration', methods=['GET'])
def demo_registration():
    return jsonify({'message': 'Demo registration page. Please POST your registration data.'})

@app.route('/process-demo-registration', methods=['POST'])
def process_demo_registration():
    """Route to process the demo registration form."""
    # Collect form data
    full_name = request.form.get('full_name', '')
    email = request.form.get('email', '')
    phone = request.form.get('phone', '')
    available_time = request.form.get('available_time', '')
    available_date = request.form.get('available_date', '')
    prior_experience = request.form.get('prior_experience', '')  # Use .get() to avoid KeyError
    level = request.form.get('level', '')
    purpose = request.form.get('purpose', '')
    status = request.form.get('status', '')
    permit_expiry = request.form.get('permit_expiry', '')
    exam_planning = request.form.get('exam_planning', '')
    clb_goal = request.form.get('clb_goal', '')

    # Redirect to PayPal for payment
    return redirect("https://www.paypal.com/cgi-bin/webscr?cmd=_xclick&business=phenish125@gmail.com&item_name=Demo Class&amount=7.00&currency_code=CAD&no_note=1&no_shipping=1")

    # Send confirmation email to admin and user
    try:
        # Email to the user
        user_email_body = (
            f"Hi {full_name},\n\n"
            f"Thank you for booking a demo class with FRENCH.GTA. Here are your details:\n"
            f"Date: {available_date}\n"
            f"Time: {available_time}\n"
            f"Purpose: {purpose}\n\n"
            f"We look forward to seeing you in the class!\n\n"
            f"Best regards,\nFRENCH.GTA Team"
        )
        send_email(
            to_email=email,
            subject="Demo Class Booking Confirmation",
            body=user_email_body
        )

        # Email to the admin
        admin_email_body = (
            f"New demo class booking:\n\n"
            f"Name: {full_name}\n"
            f"Email: {email}\n"
            f"Phone: {phone}\n"
            f"Date: {available_date}\n"
            f"Time: {available_time}\n"
            f"Purpose: {purpose}\n"
            f"Status: {status}\n"
            f"Permit Expiry: {permit_expiry}\n"
            f"Exam Planning: {exam_planning}\n"
            f"CLB Goal: {clb_goal}\n"
        )
        send_email(
            to_email="admin@frenchgta.com",
            subject="New Demo Class Booking",
            body=admin_email_body
        )
    except Exception as e:
        print(f"Error sending email: {repr(e)}")

# Helper function to send emails
def send_email(to_email, subject, body):
    """Send an email."""
    try:
        msg = Message(
            subject=subject,
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[to_email],
            body=body
        )
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {repr(e)}")

@app.route('/payment-details', methods=['GET', 'POST'])
def payment_details():
    if request.method == 'POST':
        # Collect form data
        payment_data = request.form.to_dict()
        item_name = payment_data.get('item_name')
        amount = payment_data.get('amount')
        payment_method = payment_data.get('payment_method')
        full_name = payment_data.get('full_name')
        email = payment_data.get('email')
        phone = payment_data.get('phone')
        available_time = payment_data.get('available_time')
        available_date = payment_data.get('available_date')
        prior_experience = payment_data.get('prior_experience')
        level = payment_data.get('level')
        purpose = payment_data.get('purpose')
        status = payment_data.get('status', '')
        permit_expiry = payment_data.get('permit_expiry', '')
        exam_planning = payment_data.get('exam_planning', '')
        clb_goal = payment_data.get('clb_goal', '')

        if payment_method == 'interac':
            # Send email to admin with user details
            admin_message = Message(
                subject=f"New Interac Payment Request for {item_name}",
                sender=app.config['MAIL_USERNAME'],
                recipients=['frenchgta.ca@gmail.com'],
                body=f"""
                Interac Payment Details:
                Name: {full_name}
                Email: {email}
                Phone: {phone}
                Plan: {item_name}
                Amount: ${amount}
                Available Time: {available_time}
                Available Date: {available_date}
                Prior Experience: {prior_experience}
                Level: {level}
                Purpose: {purpose}
                Status: {status}
                Permit Expiry: {permit_expiry}
                Exam Planning: {exam_planning}
                CLB Goal: {clb_goal}
                """
            )
            mail.send(admin_message)
            # Display Interac payment instructions to the user as JSON
            return jsonify({
                'message': 'Interac payment instructions',
                'full_name': full_name,
                'item_name': item_name,
                'amount': amount,
                'interac_email': 'frenchgta.ca@gmail.com'
            })

        # For PayPal, redirect to PayPal
        session['payment_data'] = payment_data  # Store form data in session
        return jsonify({'message': 'Redirect to PayPal for payment.', 'paypal_url': f"https://www.paypal.com/cgi-bin/webscr?cmd=_xclick&business=phenish125@gmail.com&item_name={item_name}&amount={amount}&currency_code=CAD&no_note=1&no_shipping=1&return=http://127.0.0.1:5000/payment-success"})

    # Render the payment details form
    item_name = request.args.get('item_name', '')
    amount = request.args.get('amount', '')
    payment_method = request.args.get('payment_method', '')
    return jsonify({'item_name': item_name, 'amount': amount, 'payment_method': payment_method})

@app.route('/payment-success', methods=['GET'])
def payment_success():
    payment_data = session.get('payment_data', {})
    if not payment_data:
        return jsonify({'error': 'No payment data found. Please try again.'}), 400

    # Extract payment data
    full_name = payment_data.get('full_name')
    email = payment_data.get('email')
    phone = payment_data.get('phone')
    item_name = payment_data.get('item_name')
    amount = payment_data.get('amount')
    available_time = payment_data.get('available_time')
    available_date = payment_data.get('available_date')
    prior_experience = payment_data.get('prior_experience')
    level = payment_data.get('level')
    purpose = payment_data.get('purpose')
    status = payment_data.get('status', '')
    permit_expiry = payment_data.get('permit_expiry', '')
    exam_planning = payment_data.get('exam_planning', '')
    clb_goal = payment_data.get('clb_goal', '')

    # Send email to admin
    admin_message = Message(
        subject=f"New Payment for {item_name}",
        sender=app.config['MAIL_USERNAME'],
        recipients=['frenchgta.ca@gmail.com'],
        body=f"""
        Payment Details:
        Name: {full_name}
        Email: {email}
        Phone: {phone}
        Plan: {item_name}
        Amount: ${amount}
        Available Time: {available_time}
        Available Date: {available_date}
        Prior Experience: {prior_experience}
        Level: {level}
        Purpose: {purpose}
        Status: {status}
        Permit Expiry: {permit_expiry}
        Exam Planning: {exam_planning}
        CLB Goal: {clb_goal}
        """
    )
    mail.send(admin_message)

    # Send confirmation email to user
    user_message = Message(
        subject="Payment Confirmation - FRENCH.GTA",
        sender=app.config['MAIL_USERNAME'],
        recipients=[email],
        body=f"""
        Hi {full_name},

        Thank you for your payment for the {item_name} plan. We have received your payment of ${amount}.
        Our team will get back to you shortly to schedule your class.

        Best regards,
        FRENCH.GTA Team
        """
    )
    mail.send(user_message)

    # Clear session data
    session.pop('payment_data', None)

    return jsonify({'message': 'Payment successful', 'full_name': full_name, 'item_name': item_name, 'amount': amount})

@app.route('/api/current_time', methods=['GET'])
def current_time():
    """API to provide the current EST and IST times."""
    try:
        # Get the current UTC time
        utc_now = datetime.utcnow()

        # Convert to EST (UTC-5)
        est = pytz.timezone('America/New_York')
        est_time = utc_now.replace(tzinfo=pytz.utc).astimezone(est)

        # Convert to IST (UTC+5:30)
        ist = pytz.timezone('Asia/Kolkata')
        ist_time = utc_now.replace(tzinfo=pytz.utc).astimezone(ist)

        # Return the times in ISO format with milliseconds
        return jsonify({
            'est': est_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],  # Trim to milliseconds
            'ist': ist_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]   # Trim to milliseconds
        }), 200
    except Exception as e:
        print(f"Error in current_time API: {repr(e)}")
        return jsonify({'error': 'Failed to fetch current time'}), 500
@app.route('/terms')
def terms():
    return jsonify({"message": "Terms and conditions page content."})

@app.route('/privacy')
def privacy():
    return jsonify({"message": "Privacy policy page content."})

@app.route('/guidelines')
def guidelines():
    return jsonify({"message": "Guidelines page content."})
@app.route('/careers')
def careers():
    return jsonify({"message": "Careers page content."})

@app.route('/refer', methods=['GET', 'POST'])
def refer():
    if request.method == 'POST':
        your_name = request.form.get('your_name')
        your_email = request.form.get('your_email')
        friend_name = request.form.get('friend_name')
        friend_email = request.form.get('friend_email')
        message = request.form.get('message')
        # Send email to admin
        try:
            admin_subject = f"New Referral from {your_name} ({your_email})"
            admin_body = f"""
Referral Details:

Referrer Name: {your_name}
Referrer Email: {your_email}
Friend's Name: {friend_name}
Friend's Email: {friend_email}
Message: {message}
"""
            admin_msg = Message(
                subject=admin_subject,
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=['frenchgta.ca@gmail.com'],
                body=admin_body
            )
            mail.send(admin_msg)
            # Optionally, send an email to the friend
            if friend_email:
                friend_subject = f"{your_name} invited you to learn French at FRENCH.GTA!"
                friend_body = f"""
Hi {friend_name},

Your friend {your_name} ({your_email}) thinks you might be interested in learning French with FRENCH.GTA!

Personal message:
{message}

If you have any questions or want to learn more, visit our website or contact us at frenchgta.ca@gmail.com.

Both you and {your_name} will receive a $30 discount if you enroll!

Best regards,
FRENCH.GTA Team
"""
                friend_msg = Message(
                    subject=friend_subject,
                    sender=app.config['MAIL_DEFAULT_SENDER'],
                    recipients=[friend_email],
                    body=friend_body
                )
                mail.send(friend_msg)
            success = f"Thank you, {your_name}! Your referral has been submitted."
        except Exception as e:
            print(f"Error sending referral email: {repr(e)}")
            success = f"Thank you, {your_name}! Your referral has been submitted, but we couldn't send the email notification."
        return jsonify({'success': success})
    return jsonify({'message': 'Refer a friend. Please POST your referral data.'})



# --- Testimonial Management ---

# Helper: Testimonial image upload folder
TESTIMONIAL_UPLOAD_FOLDER = os.path.join('static', 'img', 'testimonials')
if not os.path.exists(TESTIMONIAL_UPLOAD_FOLDER):
    os.makedirs(TESTIMONIAL_UPLOAD_FOLDER)

@app.route('/admin/testimonials', methods=['GET', 'POST'])
def admin_testimonials():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    conn = connect_db()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500
    cursor = conn.cursor(dictionary=True)
    message = None
    try:
        if request.method == 'POST':
            # ... existing code ...
            message = 'Testimonial added successfully.'
        cursor.execute("SELECT * FROM testimonials ORDER BY date_submitted DESC")
        testimonials = cursor.fetchall()
        return jsonify({'testimonials': testimonials, 'testimonial_message': message, **get_admin_portal_context()})
    except Exception as e:
        print(f"Error in admin_testimonials: {repr(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

def get_admin_portal_context():
    # Helper to fetch users, blogs, categories for admin_portal.html
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id AS user_id, email, name, role, custom_number FROM users")
        users = cursor.fetchall()
        cursor.execute("SELECT * FROM blogs")
        blogs = cursor.fetchall()
        categories = ["french", "canadian_immigration", "general", "tef_specific"]
        return dict(users=users, blogs=blogs, edit_user=None, role_filter='', categories=categories)
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/testimonials/edit/<int:testimonial_id>', methods=['POST'])
def edit_testimonial(testimonial_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    conn = connect_db()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()
    try:
        name = sanitize_input(request.form.get('name'))
        text = sanitize_input(request.form.get('text'))
        is_approved = int(request.form.get('is_approved', 0))
        photo_filename = None
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and allowed_file(photo.filename):
                photo_filename = secure_filename(photo.filename)
                photo.save(os.path.join(TESTIMONIAL_UPLOAD_FOLDER, photo_filename))
        # Update testimonial
        if photo_filename:
            cursor.execute(
                "UPDATE testimonials SET name=%s, text=%s, photo=%s, is_approved=%s WHERE id=%s",
                (name, text, photo_filename, is_approved, testimonial_id)
            )
        else:
            cursor.execute(
                "UPDATE testimonials SET name=%s, text=%s, is_approved=%s WHERE id=%s",
                (name, text, is_approved, testimonial_id)
            )
        conn.commit()
        return redirect(url_for('admin_testimonials'))
    except Exception as e:
        print(f"Error in edit_testimonial: {repr(e)}")
        return f"Error: {repr(e)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/testimonials/delete/<int:testimonial_id>', methods=['POST'])
def delete_testimonial(testimonial_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    conn = connect_db()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM testimonials WHERE id=%s", (testimonial_id,))
        conn.commit()
        return redirect(url_for('admin_testimonials'))
    except Exception as e:
        print(f"Error in delete_testimonial: {repr(e)}")
        return f"Error: {repr(e)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/testimonials/approve/<int:testimonial_id>', methods=['POST'])
def approve_testimonial(testimonial_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    conn = connect_db()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE testimonials SET is_approved = 1 WHERE id=%s", (testimonial_id,))
        conn.commit()
        return redirect(url_for('admin_testimonials'))
    except Exception as e:
        print(f"Error in approve_testimonial: {repr(e)}")
        return f"Error: {repr(e)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/testimonials')
def testimonials():
    conn = connect_db()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM testimonials WHERE is_approved=1 ORDER BY date_submitted DESC")
        testimonials = cursor.fetchall()
        return jsonify({'testimonials': testimonials})
    except Exception as e:
        print(f"Error in testimonials: {repr(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- Reserve Management ---
@app.route('/add_reserve', methods=['POST'])
def add_reserve():
    if 'role' in session and session['role'] == 'admin':
        reserve_name = request.form.get('reserve_name')
        amount = float(request.form.get('amount'))
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()
        try:
            query = "INSERT INTO reserves (reserve_name, amount, date) VALUES (%s, %s, NOW())"
            cursor.execute(query, (reserve_name, amount))
            conn.commit()
            return redirect(url_for('financial_management'))
        except Exception as e:
            print(f"Error in add_reserve: {repr(e)}")
            return f"Error: {repr(e)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/edit_reserve/<int:reserve_id>', methods=['POST'])
def edit_reserve(reserve_id):
    if 'role' in session and session['role'] == 'admin':
        reserve_name = request.form.get('reserve_name')
        amount = float(request.form.get('amount'))
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()
        try:
            query = "UPDATE reserves SET reserve_name=%s, amount=%s WHERE id=%s"
            cursor.execute(query, (reserve_name, amount, reserve_id))
            conn.commit()
            return redirect(url_for('financial_management'))
        except Exception as e:
            print(f"Error in edit_reserve: {repr(e)}")
            return f"Error: {repr(e)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/delete_reserve/<int:reserve_id>', methods=['POST'])
def delete_reserve(reserve_id):
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()
        try:
            query = "DELETE FROM reserves WHERE id=%s"
            cursor.execute(query, (reserve_id,))
            conn.commit()
            return redirect(url_for('financial_management'))
        except Exception as e:
            print(f"Error in delete_reserve: {repr(e)}")
            return f"Error: {repr(e)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

# --- Revenue Management (Edit/Delete) ---
@app.route('/edit_revenue/<int:revenue_id>', methods=['POST'])
def edit_revenue(revenue_id):
    if 'role' in session and session['role'] == 'admin':
        student_name = request.form.get('student_name')
        classes_per_month = int(request.form.get('classes_per_month'))
        teacher_name = request.form.get('teacher_name')
        amount = float(request.form.get('amount'))
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()
        try:
            query = "UPDATE revenue SET student_name=%s, classes_per_month=%s, teacher_name=%s, amount=%s WHERE id=%s"
            cursor.execute(query, (student_name, classes_per_month, teacher_name, amount, revenue_id))
            conn.commit()
            return redirect(url_for('financial_management'))
        except Exception as e:
            print(f"Error in edit_revenue: {repr(e)}")
            return f"Error: {repr(e)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/delete_revenue/<int:revenue_id>', methods=['POST'])
def delete_revenue(revenue_id):
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()
        try:
            query = "DELETE FROM revenue WHERE id=%s"
            cursor.execute(query, (revenue_id,))
            conn.commit()
            return redirect(url_for('financial_management'))
        except Exception as e:
            print(f"Error in delete_revenue: {repr(e)}")
            return f"Error: {repr(e)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

# --- Expense Management (Edit/Delete) ---
@app.route('/edit_expense/<int:expense_id>', methods=['POST'])
def edit_expense(expense_id):
    if 'role' in session and session['role'] == 'admin':
        expense_name = request.form.get('expense_name')
        category = request.form.get('category')
        type_ = request.form.get('type')
        name = request.form.get('name')
        amount = float(request.form.get('amount'))
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()
        try:
            query = "UPDATE expenses SET expense_name=%s, category=%s, type=%s, name=%s, amount=%s WHERE id=%s"
            cursor.execute(query, (expense_name, category, type_, name, amount, expense_id))
            conn.commit()
            return redirect(url_for('financial_management'))
        except Exception as e:
            print(f"Error in edit_expense: {repr(e)}")
            return f"Error: {repr(e)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    if 'role' in session and session['role'] == 'admin':
        conn = connect_db()
        if conn is None:
            return "Database connection error", 500
        cursor = conn.cursor()
        try:
            query = "DELETE FROM expenses WHERE id=%s"
            cursor.execute(query, (expense_id,))
            conn.commit()
            return redirect(url_for('financial_management'))
        except Exception as e:
            print(f"Error in delete_expense: {repr(e)}")
            return f"Error: {repr(e)}", 500
        finally:
            cursor.close()
            conn.close()
    return redirect(url_for('login'))

# --- Update /financial_management to fetch reserves ---
# In the /financial_management route, after fetching expenses and revenues, add:
# cursor.execute("SELECT * FROM reserves ORDER BY date DESC LIMIT 100")
# reserves = cursor.fetchall()
# ...and pass reserves=reserves to render_template

@app.route('/edit_punch_record', methods=['POST'])
def edit_punch_record():
    record_id = request.form.get('record_id')
    punch_in = request.form.get('punch_in')
    punch_out = request.form.get('punch_out')
    conn = connect_db()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()
    try:
        # Convert datetime-local (EST) to UTC for storage
        from datetime import datetime
        import pytz
        def to_utc(dt_str):
            if not dt_str:
                return None
            # dt_str: 'YYYY-MM-DDTHH:MM'
            local = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
            est = pytz.timezone('America/New_York').localize(local)
            return est.astimezone(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')
        punch_in_utc = to_utc(punch_in)
        punch_out_utc = to_utc(punch_out)
        # Update the record
        cursor.execute("UPDATE punch_records SET punch_in=%s, punch_out=%s WHERE id=%s", (punch_in_utc, punch_out_utc, record_id))
        conn.commit()
        return redirect(url_for('teacher_management'))
    except Exception as e:
        print(f"Error editing punch record: {repr(e)}")
        return f"Error: {repr(e)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/delete_punch_record/<int:record_id>', methods=['POST'])
def delete_punch_record(record_id):
    conn = connect_db()
    if conn is None:
        return "Database connection error", 500
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM punch_records WHERE id = %s", (record_id,))
        conn.commit()
        return redirect(url_for('teacher_management'))
    except Exception as e:
        print(f"Error deleting punch record: {repr(e)}")
        return f"Error: {repr(e)}", 500
    finally:
        cursor.close()
        conn.close()

@app.route('/student_portal')
@login_required
def student_portal():
    if 'role' in session and session['role'] == 'student':
        student_id = session['user_id']
        # Fetch schedules for this student
        conn = connect_db()
        schedules = []
        calendar_events = []
        if conn is not None:
            cursor = conn.cursor(dictionary=True)
            try:
                # Find the student's internal id
                cursor.execute("SELECT id FROM students WHERE user_id = %s", (student_id,))
                student_row = cursor.fetchone()
                if student_row:
                    student_db_id = student_row['id']
                    # Join schedules, schedule_students, teachers
                    cursor.execute('''
                        SELECT s.id, s.class_name, s.class_date, s.class_time, s.subject, t.name AS teacher_name
                        FROM schedules s
                        JOIN schedule_students ss ON s.id = ss.schedule_id
                        JOIN teachers t ON s.teacher_id = t.id
                        WHERE ss.student_id = %s
                        ORDER BY s.class_date DESC, s.class_time DESC
                    ''', (student_db_id,))
                    schedules = cursor.fetchall()
                    # Build calendar events
                    for sched in schedules:
                        calendar_events.append({
                            'title': f"{sched['class_name']} ({sched['subject']})",
                            'start': f"{sched['class_date']}T{sched['class_time']}",
                            'description': f"Teacher: {sched['teacher_name']}"
                        })
            except Exception as e:
                print(f"Error fetching student schedules: {repr(e)}")
            finally:
                cursor.close()
                conn.close()
        return jsonify({'student_id': student_id, 'schedules': schedules, 'calendar_events': calendar_events})
    return redirect(url_for('login'))

# Helper function to fetch students for a teacher

def get_students_for_teacher(teacher_user_id):
    conn = connect_db()
    students = []
    if conn is not None:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id FROM teachers WHERE user_id = %s", (teacher_user_id,))
            teacher_row = cursor.fetchone()
            if teacher_row:
                teacher_id = teacher_row['id']
                cursor.execute("SELECT id, name FROM students WHERE teacher_id = %s", (teacher_id,))
                students = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    return students

# ... after app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Minimal User class for Flask-Login
class SimpleUser(UserMixin):
    def __init__(self, id, email, role, name=None):
        self.id = id
        self.email = email
        self.role = role
        self.name = name
    @property
    def is_authenticated(self):
        return True
    @property
    def is_active(self):
        return True
    @property
    def is_anonymous(self):
        return False
    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    conn = connect_db()
    if conn is not None:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, email, role, name FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                return SimpleUser(user['id'], user['email'], user['role'], user.get('name'))
        finally:
            cursor.close()
            conn.close()
    return None

if __name__ == '__main__':   
    app.run(debug=True)

