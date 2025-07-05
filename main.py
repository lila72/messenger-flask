from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
import jwt, datetime, os
from functools import wraps

app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev_secret")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ==================== МОДЕЛИ ====================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    contacts = db.relationship('Contact', backref='user', lazy=True)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contact_username = db.Column(db.String(80), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(80), nullable=False)
    recipient = db.Column(db.String(80), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# ==================== JWT ====================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Токен отсутствует'}), 403
        try:
            data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
        except:
            return jsonify({'message': 'Недействительный токен'}), 403
        return f(current_user, *args, **kwargs)
    return decorated

# ==================== API ====================
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    hashed_pw = generate_password_hash(data['password'])
    new_user = User(username=data['username'], password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'Регистрация прошла успешно'})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        token = jwt.encode({'user_id': user.id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=12)}, app.config['SECRET_KEY'])
        return jsonify({'token': token})
    return jsonify({'message': 'Неверные данные'}), 401

@app.route('/contacts', methods=['GET', 'POST'])
@token_required
def contacts(current_user):
    if request.method == 'POST':
        username = request.json['username']
        contact = Contact(user_id=current_user.id, contact_username=username)
        db.session.add(contact)
        db.session.commit()
        return jsonify({'message': 'Контакт добавлен'})
    return jsonify([c.contact_username for c in current_user.contacts])

@app.route('/users/<query>')
@token_required
def search_users(current_user, query):
    users = User.query.filter(User.username.contains(query)).all()
    return jsonify([u.username for u in users if u.username != current_user.username])

@app.route('/')
def index():
    return render_template("index.html")

@socketio.on('private_message')
def handle_private_message(data):
    room = get_room_id(data['sender'], data['recipient'])
    msg = Message(sender=data['sender'], recipient=data['recipient'], content=data['content'])
    db.session.add(msg)
    db.session.commit()
    emit('private_message', data, room=room)

@socketio.on('join')
def handle_join(data):
    room = get_room_id(data['sender'], data['recipient'])
    join_room(room)

def get_room_id(user1, user2):
    return '-'.join(sorted([user1, user2]))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))