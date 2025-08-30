from flask import Flask,render_template

app=Flask(__name__)

@app.route('/')
def home():
    return  render_template('index.html')

@app.route('/signup')
def signup():
    return  render_template('signup.html')

@app.route('/signin')
def signin():
    return  render_template('signin.html')

@app.route('/dashboard')
def dashboard():
    return  render_template('dashboard.html',active_page="dashboard")

@app.route('/tasks')
def tasks():
    return  render_template('all_tasks.html',active_page='all_tasks')

@app.route("/today")
def today():
    return render_template("today.html", active_page="today")

@app.route("/completed")
def completed():
    return render_template("completed.html", active_page="completed")

@app.route("/add_task") 
def add_task():
    return render_template("add_task.html", active_page="add_task")

# @app.route("/update_task/<int:task_id>")
# def update_task(task_id):
#     return render_template("update_task.html", task_id=task_id)

@app.route("/update_task")
def update_task():
    return render_template("update_task.html")

@app.route("/settings")
def settings():
    return render_template("settings.html", active_page="settings")

@app.route("/profile")
def profile():
    return render_template("profile.html")

if __name__=='__main__':
    app.run(debug=True)