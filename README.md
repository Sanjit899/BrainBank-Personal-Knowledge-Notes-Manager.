BrainBank – Personal Knowledge & Notes Manager

BrainBank is a modern note-taking web application built with Flask and MongoDB, designed for developers, students, and teams. It allows users to create, organize, and manage notes with text, images, tags, and code snippets. Admins can manage all users and content. Notes support Markdown, PDF export, and drag-and-drop reordering.

Key Features
User Authentication

Register & Login

Role-based access (regular user, admin)

Password hashing with Flask-Bcrypt

Create & Organize Notes

Text, images, code snippets with syntax highlighting

Tags/Categories for organization

Markdown support

Favorite/bookmark important notes

Versioning & edit history

Drag & drop note ordering

Search & Filter

Full-text search across notes

Filter by tags, date, or favorites

Admin Dashboard

View all users and their notes

Delete inappropriate content

Optional Extras

Export notes as PDF

Mobile-friendly responsive UI (Bootstrap)

Quick access dashboard

Tech Stack

Backend: Python, Flask, Flask-Login, Flask-Bcrypt

Database: MongoDB (local or Atlas)

Frontend: HTML, Bootstrap 5, JavaScript, jQuery

Markdown Rendering: markdown2

Project Structure
BrainBank/
│
├── app.py                  # Main Flask application
├── .env                    # Environment variables (Mongo URI, SECRET_KEY)
├── templates/              # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── create_note.html
│   ├── edit_note.html
│   ├── view_note.html
│   ├── note_history.html
│   └── admin_dashboard.html
│
├── static/
│   └── images/             # Uploaded images
├── README.md               # This file
└── requirements.txt        # Python dependencies


Installation & Setup
1. Clone the Repository
   git clone https://github.com/<your-username>/BrainBank.git
cd BrainBank

2. Create a Virtual Environment
   python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

3. Install Dependencies
   pip install -r requirements.txt
   Requirements (requirements.txt) should include:
   Flask
Flask-Login
Flask-Bcrypt
pymongo
python-dotenv
FPDF
markdown2
Werkzeug

4. Setup Environment Variables

Create a .env file in the root directory:
MONGO_URI=mongodb://localhost:27017/brainbank
SECRET_KEY=supersecretkey
Replace MONGO_URI if using a remote MongoDB cluster.

5. Run MongoDB

Ensure MongoDB is running locally or point to a MongoDB Atlas cluster.
# Local MongoDB
mongod


6. Run the App
   python app.py
Open your browser at http://127.0.0.1:5000/.

Usage

Register: Create a new user account.

Login: Access your personal dashboard.

Create Notes: Add text, tags, and optionally images.

Edit Notes: Update content and track version history.

Favorite Notes: Mark important notes with ★.

Search & Filter: Use the search bar or tags to quickly find notes.

Admin: Admins can view all users and notes, and delete content.

Export PDF: Export notes to PDF for sharing or offline access.

Drag & Drop: Rearrange notes in the dashboard with drag-and-drop.


License

This project is MIT License – feel free to use, modify, and share.


PDF Export: FPDF

File Uploads: Images stored in static/images
