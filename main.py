from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, ForeignKey
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_gravatar import Gravatar
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime,timedelta
from collections import defaultdict
from flask_babel import Babel, _

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

def get_locale():
    if current_user.is_authenticated and current_user.settings:
        return current_user.settings.language
    return 'en'

babel = Babel(app, locale_selector=get_locale)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

@app.context_processor
def inject_gravatar():
    return dict(gravatar=gravatar)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(250), nullable=False)
    location: Mapped[str] = mapped_column(String(100), default="")   
    bio: Mapped[str] = mapped_column(String(250), default="")      
    github: Mapped[str] = mapped_column(String(250), default="")   
    created_at: Mapped[str] = mapped_column(String(50), default=datetime.now().strftime("%d %b %Y")) 
    theme: Mapped[str] = mapped_column(String(50), default="Light")
    font_size: Mapped[str] = mapped_column(String(50), default="Medium")
    language: Mapped[str] = mapped_column(String(50), default="English")
    created_at: Mapped[str] = mapped_column(String(50), default=datetime.now().strftime("%d %b %Y"))
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")

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

class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    theme = db.Column(db.String(20), default="light")
    font_size = db.Column(db.String(20), default="medium")
    language = db.Column(db.String(10), default="en")
    start_page = db.Column(db.String(20), default="today")
    accent_color = db.Column(db.String(20), default="blue")
    default_due_date = db.Column(db.String(20), default="none")

    user = db.relationship("User", backref=db.backref("settings", uselist=False))

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

        existing_user = db.session.execute(db.select(User).where(User.email == email)).scalar_one_or_none()
        if existing_user:
            flash(_("Email already registered. Please sign in.", "warning"))
            return redirect(url_for("signin"))

        hashed_password = generate_password_hash(password, method='sha256', salt_length=8)
        new_user = User(name=name, email=email, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        flash(_('Account created successfully', 'success'))
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
                user_settings = UserSettings.query.filter_by(user_id=user.id).first()
                if user_settings:
                    if user_settings.start_page == "today":
                        return redirect(url_for("today"))
                    elif user_settings.start_page == "all":
                        return redirect(url_for("tasks"))
                    elif user_settings.start_page == "completed":
                        return redirect(url_for("completed"))
                return redirect(url_for('dashboard'))
            else:
                flash(_('Invalid password, Please try again.', 'danger'))
                return redirect(url_for('signin'))
        else:
            flash(_('Email not found. Please sign up first.', 'warning'))
            return redirect(url_for('signup'))
    return render_template('signin.html', current_user=current_user)

@app.route('/dashboard',methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        new_task_title = request.form.get('new_task')
        if new_task_title:
            new_task = Task(
                user_id=current_user.id,
                title=new_task_title,
                description="",
                category="Personal",
                created_at=datetime.now().strftime("%d %b %Y"),
                due_date=None,
                completed=False,
                completed_at=None
            )
            db.session.add(new_task)
            db.session.commit()
            return redirect(url_for('dashboard'))
    today = datetime.now().date()

    user_tasks = db.session.execute(
        db.select(Task).where(Task.user_id == current_user.id)
    ).scalars().all()

    name=current_user.name.split(" ")[0] if current_user.name else "User"

    completed_tasks = [t for t in user_tasks if t.completed]

    for t in user_tasks:
        t.due_date_obj = datetime.strptime(t.due_date.strip(), "%d %b %Y").date() if t.due_date else None

    due_today_tasks = [t for t in user_tasks if t.due_date_obj == today]
    pending_tasks = [t for t in user_tasks if not t.completed and (not t.due_date_obj or t.due_date_obj >= today)]
    overdue_tasks = [t for t in user_tasks if not t.completed and t.due_date_obj and t.due_date_obj < today]

    events = []
    for t in user_tasks:
        if t.due_date_obj:
            events.append({
                "title": t.title,
                "start": t.due_date_obj.strftime("%Y-%m-%d"),
                "color": "#dc3545" if (not t.completed and t.due_date_obj < today) else (
                         "#28a745" if t.completed else "#ffc107")
            })

    return render_template(
        'dashboard.html',
        active_page="dashboard",
        current_user=current_user,
        completed_count=len(completed_tasks),
        due_today_count=len(due_today_tasks),
        pending_count=len(pending_tasks),
        overdue_count=len(overdue_tasks),
        due_today_tasks=due_today_tasks,
        current_date=today,
        calendar_events=events,
        name=name
    )


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
        "overdue": defaultdict(list)
    }

    for task in user_tasks:
        if task.due_date:
            due_dt = datetime.strptime(task.due_date.strip(), "%d %b %Y").date()

            if due_dt < today and task.completed:
                continue

            if due_dt == today:
                grouped["today"][task.category].append(task)
            elif due_dt == tomorrow:
                grouped["tomorrow"][task.category].append(task)
            elif due_dt < today and not task.completed:
                grouped["overdue"][task.category].append(task)
            else:
                grouped["upcoming"][task.category].append(task)
        else:
            if task.completed:
                continue
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
    
    if task.completed:
        task.completed = False
        task.completed_at = None
    else:
        task.completed = True
        task.completed_at = datetime.now().strftime("%d %b %Y %I:%M")
    
    db.session.commit()
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
    now = datetime.now()
    filter_by = request.args.get("filter", "this_week")  

    start_of_week = now - timedelta(days=now.weekday())
    start_of_month = now.replace(day=1)

    completed_tasks = db.session.execute(
        db.select(Task).where(Task.user_id == current_user.id, Task.completed == True)
    ).scalars().all()

    filtered_tasks = []
    completed_today_count = 0
    completed_this_week_count = 0
    completed_this_month_count = 0

    for task in completed_tasks:
        if task.completed_at:
            completed_dt = datetime.strptime(task.completed_at.strip(), "%d %b %Y %I:%M")
            
            if completed_dt.date() == now.date():
                completed_today_count += 1
            if completed_dt.date() >= start_of_week.date():
                completed_this_week_count += 1
            if completed_dt.date() >= start_of_month.date():
                completed_this_month_count += 1

            #dropdown filter
            if filter_by == "today" and completed_dt.date() == now.date():
                filtered_tasks.append(task)
            elif filter_by == "this_week" and completed_dt.date() >= start_of_week.date():
                filtered_tasks.append(task)
            elif filter_by == "this_month" and completed_dt.date() >= start_of_month.date():
                filtered_tasks.append(task)

    today_str = now.strftime("%d %b %Y")
    yesterday_str = (now - timedelta(days=1)).strftime("%d %b %Y")
    tomorrow_str = (now + timedelta(days=1)).strftime("%d %b %Y")

    return render_template(
        "completed.html",
        active_page="completed",
        current_user=current_user,
        tasks=filtered_tasks,
        filter_by=filter_by,
        completed_today=completed_today_count,
        completed_this_week=completed_this_week_count,
        completed_this_month=completed_this_month_count,
        today=today_str,
        yesterday=yesterday_str,
        tomorrow=tomorrow_str
    )


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
            user_settings = UserSettings.query.filter_by(user_id=current_user.id).first()
            if user_settings:
                if user_settings.default_due_date == "today":
                    due_date = datetime.now().strftime("%d %b %Y")
                elif user_settings.default_due_date == "tomorrow":
                    due_date = (datetime.now() + timedelta(days=1)).strftime("%d %b %Y")
                else:
                    due_date = None

        completed_at = None
        if completed:
            completed_at = datetime.now().strftime("%d %b %Y %I:%M")

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
    return redirect(request.referrer)

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


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    settings = UserSettings.query.filter_by(user_id=current_user.id).first()

    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.session.add(settings)
        db.session.commit()

    if request.method == "POST":
        settings.theme = request.form.get("theme", "light")
        settings.font_size = request.form.get("font_size", "medium")
        settings.language = request.form.get("language", "en")
        settings.start_page = request.form.get("start_page", "today")
        settings.accent_color = request.form.get("accent_color", "blue")
        settings.show_completed = "show_completed" in request.form
        settings.default_due_date = request.form.get("default_due_date", "none")

        db.session.commit()
        return redirect(url_for("settings"))

    return render_template(
        "settings.html",
        active_page="settings",
        current_user=current_user,
        settings=settings
    )

@app.context_processor
def inject_user_settings():
    if current_user.is_authenticated:
        settings = UserSettings.query.filter_by(user_id=current_user.id).first()
        return dict(settings=settings)
    return dict(settings=None)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current_user.name = request.form.get("name")
        current_user.location = request.form.get("location")
        current_user.bio = request.form.get("bio")
        current_user.github = request.form.get("github")
        db.session.commit()
        return redirect(url_for("profile"))

    return render_template("profile.html", current_user=current_user)

@app.route('/about')
@login_required
def about():
    return render_template('about.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
