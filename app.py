from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from flask_session import Session
from werkzeug.utils import secure_filename
import sqlite3
import secrets
import random
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO, emit

app = Flask(__name__, static_folder="static")
app.config["SECRET_KEY"] = "chiaggadiigga"
bcrypt = Bcrypt(app)
socketio = SocketIO(app)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


connect = sqlite3.connect("database.db")
connect.execute("""CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)""")


UPLOAD_FOLDER = "static/uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def login():
    try:
        if session["name"]:
            return redirect("/feed")
    except:
        pass
    return render_template("login.html")


@app.route("/", methods=["GET", "POST"])
def loginform():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        connect = sqlite3.connect("database.db")
        cursor = connect.cursor()
        cursor.execute("SELECT * FROM users")
        data = cursor.fetchall()

        for all in data:
            if username in all:
                if password == all[1]:
                    session["name"] = username
                    return redirect(url_for("feed"))
                else:
                    return f"<h1>bhai {username} hai but {password} ye nahi {all[1]} hai</h1>"
        return "Sorry bhai username ya fir password galat hai naya account bana"


@app.route("/logout")
def logout():

    session["name"] = None

    return redirect(url_for("login"))


@app.route("/createaccount/", methods=["POST", "GET"])
def createaccount():
    if request.method == "POST":
        username = request.form.get("username").lower()
        password = request.form.get("password")
        session["name"] = username
        print(username)
        hashed_password = bcrypt.generate_password_hash("password").decode("utf-8")

        with sqlite3.connect("database.db") as users:
            cursor = users.cursor()
            cursor.execute(
                """INSERT INTO users  
                (username,password) VALUES (?,?)""",
                (username, hashed_password),
            )
            users.commit()

            return redirect(url_for("feed"))

    return render_template("createaccount.html")


@app.route("/upload")
def upload_form():
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    if "photo" not in request.files:
        return "No file part"
    photo = request.files["photo"]
    text = request.form.get("text")

    if len(text) > 200:
        return "thora chota caption"

    if photo.filename == "":
        return "No selected file"
    if photo:
        filename = secure_filename(photo.filename)
        extension = os.path.splitext(filename)[1]
        randommm = secrets.token_urlsafe(16)
        new_filename = randommm + extension
        photo.save(os.path.join(app.config["UPLOAD_FOLDER"], new_filename))

        # upload to database
        with sqlite3.connect("database.db") as users:
            cursor = users.cursor()
            cursor.execute(
                """INSERT INTO posts  
                (username,media,caption) VALUES (?,?,?)""",
                (session["name"], new_filename, text),
            )
            users.commit()

        return redirect(url_for("feed"))


@app.route("/feed")
def feed():
    if session["name"]:

        connect = sqlite3.connect("database.db")
        cursor = connect.cursor()
        cursor.execute("SELECT * FROM posts")
        data_in = cursor.fetchall()
        random.shuffle(data_in)
        return render_template("feed.html", data=data_in)
    else:
        return redirect(url_for("login"))


@app.route("/profile/  ")
def profile():
    if session["name"]:

        connect = sqlite3.connect("database.db")
        cursor = connect.cursor()
        user = session["name"]
        cursor.execute("SELECT * FROM posts WHERE username=?", (user,))
        data_in = cursor.fetchall()
        cursor.execute("SELECT * FROM users WHERE username=?", (session["name"],))
        users = cursor.fetchall()

        return render_template("profile.html", data=data_in, profile=users)
    return render_template("profile.html")


@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        searchname = request.form.get("searchname")

        return redirect(url_for("search_user", username=searchname))
    else:

        return "No user found"


@app.route("/search/<username>")
def search_user(username):
    connect = sqlite3.connect("database.db")
    cursor = connect.cursor()

    cursor.execute("SELECT * FROM posts WHERE username=?", (username,))
    data_in = cursor.fetchall()
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    users = cursor.fetchall()

    if len(users) != 0:
        return render_template("profile.html", data=data_in, profile=users)
    else:
        return f"NO such user %s" % username


@app.route(
    "/globalchat",
)
def globalchat():
    if session["name"]:
        return render_template("globalchat.html")
    else:
        return redirect(
            url_for(
                "loginform",
            )
        )


@socketio.on("message")
def handle_message(message):
    emit("message", message, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, debug=True)
