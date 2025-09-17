import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from dotenv import load_dotenv
from fpdf import FPDF
import markdown2
from werkzeug.utils import secure_filename
import json

# -------------------------------
# Auto-create folders
# -------------------------------
folders = ["templates", "static/images"]
for folder in folders:
    os.makedirs(folder, exist_ok=True)

UPLOAD_FOLDER = "static/images"

# -------------------------------
# .env
# -------------------------------
if not os.path.exists(".env"):
    with open(".env", "w") as f:
        f.write("MONGO_URI=mongodb://localhost:27017/brainbank\nSECRET_KEY=supersecretkey")

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
SECRET_KEY = os.getenv("SECRET_KEY")

# -------------------------------
# Flask setup
# -------------------------------
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
bcrypt = Bcrypt(app)
client = MongoClient(MONGO_URI)
db = client.brainbank

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

# -------------------------------
# User class
# -------------------------------
class User(UserMixin):
    def __init__(self, u):
        self.id = str(u["_id"])
        self.name = u["name"]
        self.email = u["email"]
        self.password = u["password"]
        self.role = u.get("role","user")

@login_manager.user_loader
def load_user(user_id):
    u = db.users.find_one({"_id": ObjectId(user_id)})
    if u:
        return User(u)
    return None

# -------------------------------
# Templates (minimal auto-create)
# -------------------------------
template_files = {
"templates/base.html": """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}BrainBank{% endblock %}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/default.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js"></script>
<script>hljs.highlightAll();</script>
<style>.note-row{cursor:move;}</style>
</head><body>
<nav class="navbar navbar-expand-lg navbar-light bg-light"><div class="container-fluid">
<a class="navbar-brand" href="{{ url_for('dashboard') }}">BrainBank</a>
<div class="collapse navbar-collapse">
<ul class="navbar-nav me-auto">
{% if current_user.is_authenticated %}
<li class="nav-item"><a class="nav-link" href="{{ url_for('dashboard') }}">Dashboard</a></li>
<li class="nav-item"><a class="nav-link" href="{{ url_for('create_note') }}">Create Note</a></li>
{% if current_user.role=='admin' %}
<li class="nav-item"><a class="nav-link" href="{{ url_for('admin_dashboard') }}">Admin</a></li>{% endif %}
<li class="nav-item"><a class="nav-link" href="{{ url_for('logout') }}">Logout</a></li>
{% else %}
<li class="nav-item"><a class="nav-link" href="{{ url_for('login') }}">Login</a></li>
<li class="nav-item"><a class="nav-link" href="{{ url_for('register') }}">Register</a></li>
{% endif %}
</ul></div></div></nav>
<div class="container mt-4">{% with messages = get_flashed_messages(with_categories=true) %}
{% if messages %}{% for category,msg in messages %}<div class="alert alert-{{category}}">{{msg}}</div>{% endfor %}{% endif %}{% endwith %}
{% block content %}{% endblock %}</div>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script></body></html>""",
"templates/register.html": """{% extends 'base.html' %}{% block title %}Register{% endblock %}{% block content %}
<h2>Register</h2>
<form method="POST">
<div class="mb-3"><label>Name:</label><input type="text" name="name" class="form-control" required></div>
<div class="mb-3"><label>Email:</label><input type="email" name="email" class="form-control" required></div>
<div class="mb-3"><label>Password:</label><input type="password" name="password" class="form-control" required></div>
<button type="submit" class="btn btn-success">Register</button></form>
<p class="mt-2">Already have account? <a href="{{ url_for('login') }}">Login</a></p>{% endblock %}""",
"templates/login.html": """{% extends 'base.html' %}{% block title %}Login{% endblock %}{% block content %}
<h2>Login</h2>
<form method="POST">
<div class="mb-3"><label>Email:</label><input type="email" name="email" class="form-control" required></div>
<div class="mb-3"><label>Password:</label><input type="password" name="password" class="form-control" required></div>
<button type="submit" class="btn btn-primary">Login</button></form>
<p class="mt-2">Don't have account? <a href="{{ url_for('register') }}">Register</a></p>{% endblock %}""",
"templates/dashboard.html": """{% extends 'base.html' %}{% block title %}Dashboard{% endblock %}{% block content %}
<h2>Welcome, {{ current_user.name }}</h2>
<form method="GET" class="mb-3">
<input type="text" name="q" placeholder="Search..." class="form-control" value="{{ request.args.get('q','') }}">
<select name="tag" class="form-select mt-2"><option value="">All Tags</option>{% for t in tags %}<option value="{{t}}" {% if t==request.args.get('tag') %}selected{% endif %}>{{t}}</option>{% endfor %}</select>
<select name="favorite" class="form-select mt-2"><option value="">All</option><option value="1" {% if request.args.get('favorite')=='1' %}selected{% endif %}>Favorites</option></select>
<button class="btn btn-primary mt-2">Filter</button></form>
<a href="{{ url_for('create_note') }}" class="btn btn-primary mb-2">Create Note</a>
<table class="table table-bordered" id="notes-table"><thead><tr><th>Title</th><th>Tags</th><th>Favorite</th><th>Actions</th></tr></thead>
<tbody id="notes-body">{% for note in notes %}<tr class="note-row" data-id="{{note._id}}">
<td>{{ note.title }}</td><td>{{ ', '.join(note.tags) if note.tags else '' }}</td><td>{% if note.favorite %}★{% else %}☆{% endif %}</td>
<td>
<a href="{{ url_for('view_note', note_id=note._id) }}" class="btn btn-info btn-sm">View</a>
<a href="{{ url_for('edit_note', note_id=note._id) }}" class="btn btn-warning btn-sm">Edit</a>
<a href="{{ url_for('delete_note', note_id=note._id) }}" class="btn btn-danger btn-sm">Delete</a>
<a href="{{ url_for('toggle_favorite', note_id=note._id) }}" class="btn btn-warning btn-sm">{% if note.favorite %}★{% else %}☆{% endif %}</a>
<a href="{{ url_for('export_pdf', note_id=note._id) }}" class="btn btn-secondary btn-sm">PDF</a>
<a href="{{ url_for('note_history', note_id=note._id) }}" class="btn btn-dark btn-sm">History</a>
</td></tr>{% endfor %}</tbody></table>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.0/Sortable.min.js"></script>
<script>
var el=document.getElementById('notes-body');var sortable=Sortable.create(el,{animation:150,onEnd:function(evt){let ids=[];$('#notes-body tr').each(function(){ids.push($(this).data('id'));});$.post('{{ url_for("reorder_notes") }}',{order:JSON.stringify(ids)});}});
</script>{% endblock %}""",
"templates/create_note.html": """{% extends 'base.html' %}{% block title %}Create Note{% endblock %}{% block content %}
<h2>Create Note</h2>
<form method="POST" enctype="multipart/form-data">
<div class="mb-3"><label>Title:</label><input type="text" name="title" class="form-control" required></div>
<div class="mb-3"><label>Content (Markdown supported):</label><textarea name="content" class="form-control" rows="5" required></textarea></div>
<div class="mb-3"><label>Tags (comma separated):</label><input type="text" name="tags" class="form-control"></div>
<div class="mb-3"><label>Upload Image:</label><input type="file" name="image" class="form-control"></div>
<button type="submit" class="btn btn-success">Save Note</button></form>{% endblock %}""",
"templates/edit_note.html": """{% extends 'base.html' %}{% block title %}Edit Note{% endblock %}{% block content %}
<h2>Edit Note</h2>
<form method="POST" enctype="multipart/form-data">
<div class="mb-3"><label>Title:</label><input type="text" name="title" class="form-control" value="{{ note.title }}" required></div>
<div class="mb-3"><label>Content (Markdown supported):</label><textarea name="content" class="form-control" rows="5" required>{{ note.content }}</textarea></div>
<div class="mb-3"><label>Tags (comma separated):</label><input type="text" name="tags" class="form-control" value="{{ ', '.join(note.tags) }}"></div>
<div class="mb-3"><label>Change Image:</label><input type="file" name="image" class="form-control"></div>
<button type="submit" class="btn btn-success">Update Note</button></form>{% endblock %}""",
"templates/view_note.html": """{% extends 'base.html' %}{% block title %}View Note{% endblock %}{% block content %}
<h2>{{ note.title }}</h2>
<div>{{ note.content_html|safe }}</div>
{% if note.image %}<img src="{{ url_for('static', filename='images/'+note.image) }}" class="img-fluid mt-2">{% endif %}
<p><strong>Tags:</strong> {{ ', '.join(note.tags) if note.tags else '' }}</p>
<p><strong>Created At:</strong> {{ note.created_at }}</p>
<a href="{{ url_for('dashboard') }}" class="btn btn-primary">Back</a>{% endblock %}""",
"templates/note_history.html": """{% extends 'base.html' %}{% block title %}Note History{% endblock %}{% block content %}
<h2>History for: {{ note.title }}</h2>
{% if note.versions %}
<table class="table table-bordered"><thead><tr><th>Title</th><th>Content</th><th>Tags</th><th>Updated At</th></tr></thead>
<tbody>{% for v in note.versions %}<tr><td>{{ v.title }}</td><td>{{ v.content }}</td><td>{{ ', '.join(v.tags) if v.tags else '' }}</td><td>{{ v.updated_at }}</td></tr>{% endfor %}</tbody></table>
{% else %}<p>No previous versions.</p>{% endif %}
<a href="{{ url_for('dashboard') }}" class="btn btn-primary">Back</a>{% endblock %}""",
"templates/admin_dashboard.html": """{% extends 'base.html' %}{% block title %}Admin Dashboard{% endblock %}{% block content %}
<h2>Admin Dashboard</h2>
<h4>All Users</h4>
<table class="table table-bordered"><thead><tr><th>Name</th><th>Email</th><th>Role</th></tr></thead>
<tbody>{% for u in users %}<tr><td>{{ u.name }}</td><td>{{ u.email }}</td><td>{{ u.role }}</td></tr>{% endfor %}</tbody></table>
<h4>All Notes</h4>
<table class="table table-bordered"><thead><tr><th>Title</th><th>User</th><th>Tags</th><th>Favorite</th><th>Actions</th></tr></thead>
<tbody>{% for n in notes %}<tr><td>{{ n.title }}</td><td>{{ n.user_name }}</td><td>{{ ', '.join(n.tags) if n.tags else '' }}</td><td>{% if n.favorite %}★{% else %}☆{% endif %}</td>
<td><a href="{{ url_for('delete_note_admin', note_id=n._id) }}" class="btn btn-danger btn-sm">Delete</a></td></tr>{% endfor %}</tbody></table>{% endblock %}"""
}

for filename, content in template_files.items():
    if not os.path.exists(filename):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)

# -------------------------------
# Helper functions
# -------------------------------
def save_image(file):
    if not file:
        return None
    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    return filename

# -------------------------------
# Routes
# -------------------------------
@app.route("/")
def home():
    return redirect(url_for("dashboard"))

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        name = request.form["name"]
        email = request.form["email"]
        password = bcrypt.generate_password_hash(request.form["password"]).decode("utf-8")
        if db.users.find_one({"email": email}):
            flash("Email already exists","danger")
        else:
            db.users.insert_one({"name":name,"email":email,"password":password,"role":"user"})
            flash("Registered successfully, login now","success")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        email = request.form["email"]
        password = request.form["password"]
        u = db.users.find_one({"email": email})
        if u and bcrypt.check_password_hash(u["password"], password):
            login_user(User(u))
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials","danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out","success")
    return redirect(url_for("login"))

# -------------------------------
# Dashboard
# -------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    query = {}
    search = request.args.get("q","")
    tag = request.args.get("tag","")
    fav = request.args.get("favorite","")
    if current_user.role=="user":
        query["user_id"] = current_user.id
    if search:
        query["title"] = {"$regex": search, "$options":"i"}
    if tag:
        query["tags"] = tag
    if fav=="1":
        query["favorite"] = True
    notes = list(db.notes.find(query))
    for n in notes:
        n["_id"] = str(n["_id"])
        n["content_html"] = markdown2.markdown(n.get("content",""))
    tags = list(set([t for note in notes for t in note.get("tags",[])]))
    return render_template("dashboard.html", notes=notes, tags=tags)

# -------------------------------
# Create Note
# -------------------------------
@app.route("/create_note", methods=["GET","POST"])
@login_required
def create_note():
    if request.method=="POST":
        title = request.form["title"]
        content = request.form["content"]
        tags = [t.strip() for t in request.form.get("tags","").split(",") if t.strip()]
        image_file = request.files.get("image")
        image = save_image(image_file)
        db.notes.insert_one({
            "title": title,
            "content": content,
            "tags": tags,
            "image": image,
            "favorite": False,
            "user_id": current_user.id,
            "user_name": current_user.name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "versions": []
        })
        flash("Note created","success")
        return redirect(url_for("dashboard"))
    return render_template("create_note.html")

# -------------------------------
# Edit Note
# -------------------------------
@app.route("/edit_note/<note_id>", methods=["GET","POST"])
@login_required
def edit_note(note_id):
    note = db.notes.find_one({"_id": ObjectId(note_id)})
    if not note:
        flash("Note not found","danger")
        return redirect(url_for("dashboard"))
    if current_user.role!="admin" and note["user_id"]!=current_user.id:
        flash("Access denied","danger")
        return redirect(url_for("dashboard"))
    if request.method=="POST":
        # save old version
        old_version = {
            "title": note["title"],
            "content": note["content"],
            "tags": note.get("tags",[]),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        db.notes.update_one({"_id": ObjectId(note_id)}, {"$push":{"versions":old_version}})
        # update note
        title = request.form["title"]
        content = request.form["content"]
        tags = [t.strip() for t in request.form.get("tags","").split(",") if t.strip()]
        image_file = request.files.get("image")
        image = save_image(image_file) if image_file else note.get("image")
        db.notes.update_one({"_id": ObjectId(note_id)}, {"$set":{"title":title,"content":content,"tags":tags,"image":image}})
        flash("Note updated","success")
        return redirect(url_for("dashboard"))
    note["_id"] = str(note["_id"])
    return render_template("edit_note.html", note=note)

# -------------------------------
# View Note
# -------------------------------
@app.route("/view_note/<note_id>")
@login_required
def view_note(note_id):
    note = db.notes.find_one({"_id": ObjectId(note_id)})
    if not note:
        flash("Note not found","danger")
        return redirect(url_for("dashboard"))
    if current_user.role!="admin" and note["user_id"]!=current_user.id:
        flash("Access denied","danger")
        return redirect(url_for("dashboard"))
    note["_id"] = str(note["_id"])
    note["content_html"] = markdown2.markdown(note.get("content",""))
    return render_template("view_note.html", note=note)

# -------------------------------
# Delete Note
# -------------------------------
@app.route("/delete_note/<note_id>")
@login_required
def delete_note(note_id):
    note = db.notes.find_one({"_id": ObjectId(note_id)})
    if not note:
        flash("Note not found","danger")
    elif current_user.role!="admin" and note["user_id"]!=current_user.id:
        flash("Access denied","danger")
    else:
        db.notes.delete_one({"_id": ObjectId(note_id)})
        flash("Note deleted","success")
    return redirect(url_for("dashboard"))

# -------------------------------
# Toggle Favorite
# -------------------------------
@app.route("/toggle_favorite/<note_id>")
@login_required
def toggle_favorite(note_id):
    note = db.notes.find_one({"_id": ObjectId(note_id)})
    if note and (current_user.role=="admin" or note["user_id"]==current_user.id):
        db.notes.update_one({"_id": ObjectId(note_id)}, {"$set":{"favorite": not note.get("favorite",False)}})
    return redirect(url_for("dashboard"))

# -------------------------------
# Note History
# -------------------------------
@app.route("/note_history/<note_id>")
@login_required
def note_history(note_id):
    note = db.notes.find_one({"_id": ObjectId(note_id)})
    if not note:
        flash("Note not found","danger")
        return redirect(url_for("dashboard"))
    if current_user.role!="admin" and note["user_id"]!=current_user.id:
        flash("Access denied","danger")
        return redirect(url_for("dashboard"))
    note["_id"] = str(note["_id"])
    return render_template("note_history.html", note=note)

# -------------------------------
# Reorder Notes
# -------------------------------
@app.route("/reorder_notes", methods=["POST"])
@login_required
def reorder_notes():
    order = json.loads(request.form.get("order","[]"))
    for i,nid in enumerate(order):
        db.notes.update_one({"_id": ObjectId(nid)}, {"$set":{"order_index":i}})
    return "ok"

# -------------------------------
# Export PDF
# -------------------------------
@app.route("/export_pdf/<note_id>")
@login_required
def export_pdf(note_id):
    note = db.notes.find_one({"_id": ObjectId(note_id)})
    if not note:
        flash("Note not found","danger")
        return redirect(url_for("dashboard"))
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",16)
    pdf.multi_cell(0,10,note["title"])
    pdf.set_font("Arial","",12)
    pdf.multi_cell(0,10,note["content"])
    fname = f"{note['title']}.pdf"
    pdf.output(fname)
    return send_file(fname, as_attachment=True)

# -------------------------------
# Admin Dashboard
# -------------------------------
@app.route("/admin")
@login_required
def admin_dashboard():
    if current_user.role!="admin":
        flash("Access denied","danger")
        return redirect(url_for("dashboard"))
    users = list(db.users.find())
    for u in users:
        u["_id"] = str(u["_id"])
    notes = list(db.notes.find())
    for n in notes:
        n["_id"] = str(n["_id"])
    return render_template("admin_dashboard.html", users=users, notes=notes)

@app.route("/delete_note_admin/<note_id>")
@login_required
def delete_note_admin(note_id):
    if current_user.role!="admin":
        flash("Access denied","danger")
        return redirect(url_for("dashboard"))
    db.notes.delete_one({"_id": ObjectId(note_id)})
    flash("Note deleted","success")
    return redirect(url_for("admin_dashboard"))

# -------------------------------
if __name__=="__main__":
    app.run(debug=True)
