from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, ForeignKey
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_gravatar import Gravatar
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime,timedelta
from collections import defaultdict

# Initialize the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# Initialize Flask-Gravatar for user avatars
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

# Define the database base class and SQLAlchemy instance
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Define the User model for the database
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    theme: Mapped[str] = mapped_column(String(50), default="Light")
    font_size: Mapped[str] = mapped_column(String(50), default="Medium")
    language: Mapped[str] = mapped_column(String(50), default="English")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")

# Define the Task model for the database
class Task(db.Model):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(250))
    category: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[str] = mapped_column(String(50), nullable=False)
    due_date: Mapped[str] = mapped_column(String(50), nullable=True)
    completed_at: Mapped[str] = mapped_column(String(100), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    user = relationship('User', back_populates='tasks')

# Flask-Login user loader function
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, int(user_id))

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if the email is already registered
        existing_user = db.session.execute(db.select(User).where(User.email == email)).scalar_one_or_none()
        if existing_user:
            flash("Email already registered. Please sign in.", "warning")
            return redirect(url_for("signin"))

        # Hash the password for security
        hashed_password = generate_password_hash(password, method='sha256', salt_length=8)
        new_user = User(name=name, email=email, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully', 'success')
        login_user(new_user)
        return redirect(url_for('add_task'))
    return render_template('signup.html', current_user=current_user)

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid password, Please try again.', 'danger')
                return redirect(url_for('signin'))
        else:
            flash('Email not found. Please sign up first.', 'warning')
            return redirect(url_for('signup'))
    return render_template('signin.html', current_user=current_user)

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', active_page="dashboard", current_user=current_user)

@app.route('/tasks')
@login_required
def tasks():
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    user_tasks = db.session.execute(
        db.select(Task).where(Task.user_id == current_user.id)
    ).scalars().all()

    grouped = {
        "today": defaultdict(list),
        "tomorrow": defaultdict(list),
        "upcoming": defaultdict(list),
    }

    for task in user_tasks:
        if not task.due_date:
            grouped["upcoming"][task.category].append(task)
            continue

        due_dt = datetime.strptime(task.due_date.strip(), "%d %b %Y").date()

        if due_dt == today:
            grouped["today"][task.category].append(task)
        elif due_dt == tomorrow:
            grouped["tomorrow"][task.category].append(task)
        else:
            grouped["upcoming"][task.category].append(task)

    return render_template(
        "all_tasks.html",
        active_page="all_tasks",
        current_user=current_user,
        grouped=grouped
    )

@app.route('/task/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task_status(task_id):
    task = Task.query.get_or_404(task_id)
    
    task.completed = 1 - task.completed
    
    db.session.commit()
    
    flash('Task status updated successfully!', 'success')
    
    return redirect(request.referrer)


@app.route("/today")
@login_required
def today():
    today_date = datetime.now().strftime("%d %b %Y")
    today_tasks = db.session.execute(db.select(Task).where(Task.user_id == current_user.id, Task.due_date == today_date)).scalars().all()
    return render_template("today.html", active_page="today", current_user=current_user, tasks=today_tasks)

@app.route("/completed")
@login_required
def completed():
    completed_tasks = db.session.execute(db.select(Task).where(Task.user_id == current_user.id, Task.completed == True)).scalars().all()
    return render_template("completed.html", active_page="completed", current_user=current_user, tasks=completed_tasks)

@app.route("/add_task", methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('details')
        category = request.form.get('category')
        due_date = request.form.get('due_date')
        completed = request.form.get('completed')

        if due_date:
            due_date = datetime.strptime(due_date, '%Y-%m-%d').strftime("%d %b %Y")
        else:
            due_date = None

        completed_at = None
        if completed:
            completed_at = datetime.now().strftime("%d %b %Y %I:%M %p")

        new_task = Task(
            user_id=current_user.id,
            title=title,
            description=description,
            category=category.title(),
            created_at=datetime.now().strftime("%d %b %Y"),
            due_date=due_date,
            completed=bool(completed),
            completed_at=completed_at
        )

        db.session.add(new_task)
        db.session.commit()
        return redirect(url_for('tasks'))
    return render_template("add_task.html", active_page="add_task", current_user=current_user)

@app.route("/delete_task/<int:task_id>")
@login_required
def delete_task(task_id):
    task_to_delete = db.get_or_404(Task, task_id)
    db.session.delete(task_to_delete)
    db.session.commit()
    return redirect(url_for('tasks'))

@app.route("/update_task/<int:task_id>", methods=['GET', 'POST'])
@login_required
def update_task(task_id):
    task_to_update = db.get_or_404(Task, task_id)
    formatted_due_date = ''

    if request.method == 'POST':
        task_to_update.title = request.form.get('title')
        task_to_update.description = request.form.get('details')
        task_to_update.category = request.form.get('category')
        due_date = request.form.get('due_date')
        completed = request.form.get('completed')

        if due_date:
            task_to_update.due_date = datetime.strptime(due_date, '%Y-%m-%d').strftime("%d %b %Y")
        else:
            task_to_update.due_date = None

        if completed and not task_to_update.completed:
            task_to_update.completed = True
            task_to_update.completed_at = datetime.now().strftime("%d %b %Y %I:%M %p")
        elif not completed and task_to_update.completed:
            task_to_update.completed = False
            task_to_update.completed_at = None

        db.session.commit()
        return redirect(url_for('tasks'))
    
    if task_to_update.due_date:
        formatted_due_date = datetime.strptime(task_to_update.due_date, '%d %b %Y').strftime('%Y-%m-%d')

    return render_template("update_task.html", current_user=current_user, task=task_to_update,formatted_due_date=formatted_due_date)


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", active_page="settings", current_user=current_user)

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", current_user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Main entry point for the application
if __name__ == '__main__':
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully.")
    app.run(debug=True)
