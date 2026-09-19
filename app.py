from flask import Flask,render_template,url_for,redirect,request,session,flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)

app.config["SECRET_KEY"] = "secret"


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///taskflow.db"

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

    tasks = db.relationship("Task", backref="user", lazy=True)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),nullable = False)

with app.app_context():
    db.create_all()

def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))

        return route_function(*args, **kwargs)

    return wrapper

def api_login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return {
                "error": "Authentication required"
            }, 401

        return route_function(*args, **kwargs)

    return wrapper

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register/",methods = ["POST","GET"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        if not username or not email or not password:
            return render_template(
                "register.html",
                error="All fields are required"
            )

        existingusername = User.query.filter_by(username = username).first()
        existingemail = User.query.filter_by(email = email).first()

        if existingusername:
            return render_template(
            "register.html",
            error="Username already exists"
        )

        if existingemail :
            return render_template(
                "register.html",
                error="Email already exists"
            )

        hashed_password = generate_password_hash(password)

        user = User(
            username = username,
            email = email,
            password = hashed_password
        )

        db.session.add(user)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("register.html")


@app.route("/login/",methods = ["POST","GET"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username = username).first()

        if user and check_password_hash(user.password,password):
            session["user_id"] = user.id
            flash("Welcome back!")
            return redirect(url_for("tasks"))

        return "invalid username or password"

    return render_template("login.html")

@app.route("/about/")
def about():
    return render_template("about.html")

@app.route("/tasks/")
@login_required
def tasks():
    tasks = Task.query.filter_by(user_id = session["user_id"]).all()
    total_tasks = len(tasks)
    completed_tasks = len([task for task in tasks if task.completed])
    pending_tasks = total_tasks-completed_tasks
    return render_template("tasks.html",tasks= tasks,total_tasks = total_tasks,completed_tasks = completed_tasks,pending_tasks = pending_tasks)

@app.route("/tasks/create_task/",methods = ["POST","GET"])
@login_required
def create_task():
    if request.method =="POST":
        title = request.form["title"]
        description = request.form["description"]
        if not title:
            return render_template(
                "create_task.html",
                error="Title is required"
            )
        userid = session["user_id"]
        task = Task(
            title = title,
            description = description,
            user_id = userid
        )
        db.session.add(task)
        db.session.commit()
        flash("Task created successfully!")
        return redirect(url_for('tasks'))

    return render_template("create_task.html")


@app.route("/tasks/edit/<int:id>",methods=["POST","GET"])
@login_required
def edit_task(id):
    task = Task.query.filter_by(id = id, user_id = session["user_id"]).first_or_404()
    if request.method == "POST":   
        task.title = request.form["title"]
        task.description = request.form["description"]
        db.session.commit()
        flash("Task updated successfuly")
        return redirect(url_for("tasks"))
    return render_template("edit_task.html",task = task)

@app.route("/tasks/delete/<int:id>")
@login_required
def delete_task(id):
    task = Task.query.filter_by(id=id,user_id = session["user_id"]).first_or_404()
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted successfully")
    return redirect(url_for("tasks"))

@app.route("/tasks/toggle/<int:id>",methods = ["POST"])
@login_required
def toggle_status(id):
    task = Task.query.filter_by(id=id,user_id = session["user_id"]).first_or_404()
    task.completed = not task.completed
    db.session.commit()
    flash("Task status updated successfully!")
    return redirect(url_for('tasks'))

@app.route("/logout/")
def logout():
    session.pop("user_id",None)
    flash("You have been logged out.")
    return redirect(url_for('login'))

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template("500.html"), 500



# API's

@app.route("/api/tasks/",methods = ["POST","GET"])
@api_login_required
def tasks_api():
    if request.method == "POST":
        data  = request.get_json()

        if not data:
            return {
                "error":"Request body required"
            },400


        title = data["title"]
        description = data.get("description")

        if not title:
            return {
                "error":"title is required"
            },400

        task = Task(
            title = title,
            description = description,
            user_id = session["user_id"]
        )

        db.session.add(task)
        db.session.commit()

        return {
            "message": "Task created successfully",
            "id": task.id,
            "title" : task.title,
            "description": task.description,
            "completed": task.completed
        },201
    tasks = Task.query.filter_by(user_id = session["user_id"]).all()

    return [
        {
            "id": task.id,
            "title" : task.title,
            "description" : task.description,
            "completed": task.completed
        } for task in tasks ]


@app.route("/api/tasks/<int:id>",methods = ["GET","PUT","PATCH"])
@api_login_required
def task_api(id):
    task = Task.query.filter_by(id=id,user_id = session["user_id"]).first()

    if not task:
        return {
            "error":"Task not Found"
        },404

    if request.method =="PUT":
        data = request.get_json()

        if not data:
            return{
                "error" : "body required"
            },400

        title = data.get("title")
        description = data.get("description")

        if not title:
            return {
                "error":"title is required"
            },400

        task.title = title
        task.description = description

        db.session.commit()

        return {
            "message": "task updated successfully",
            "id":task.id,
            "title" : task.title,
            "description": task.description,
            "completed": task.completed
        },200

    if request.method == "PATCH":
        data = request.get_json()

        if not data:
            return{
                "error":"Request body required"
            },400

        if "completed" in data:
            if isinstance(data["completed"],bool):
                task.completed  = data["completed"]
            else:
                return{
                    "error": "Completed must be a boolean"
                },400

        db.session.commit()

        return {
            "id":task.id,
                    "title":task.title,
                    "description":task.description,
                    "completed":task.completed
            },200
    return{
        "id":task.id,
        "title":task.title,
        "description":task.description,
        "completed":task.completed
    },200


@app.route("/api/tasks/<int:id>",methods = ["DELETE"])
@api_login_required
def task_delete_api(id):
    task = Task.query.filter_by(id = id,user_id = session["user_id"]).first()

    if not task:
        return{
            "error":"task not found"
        },404

    db.session.delete(task)
    db.session.commit()
    return{
        "message":"task deleted successfully"
    },200

if __name__ == "__main__":
    app.run(debug = True)

