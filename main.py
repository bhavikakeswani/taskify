from flask import Flask,render_template

app=Flask(__name__)

@app.route('/')
def home():
    return  render_template('index.html')

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

if __name__=='__main__':
    app.run(debug=True)