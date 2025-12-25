from flask import Flask, request, jsonify, session
from flask_session import Session
import socketio

# Flask + Socket.IO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecret'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

sio = socketio.Server(cors_allowed_origins="*")
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

# Простая база пользователей
users = {}  # {username: {"password": "...", "allow_calls": True}}

# Регистрация
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username, password = data.get("username"), data.get("password")
    if username in users:
        return jsonify({"error": "Пользователь уже существует"}), 400
    users[username] = {"password": password, "allow_calls": True}
    session["user"] = username
    return jsonify({"status": "ok", "username": username})

# Вход
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username, password = data.get("username"), data.get("password")
    if username not in users or users[username]["password"] != password:
        return jsonify({"error": "Неверные данные"}), 401
    session["user"] = username
    return jsonify({"status": "ok", "username": username})

# Проверка по cookie
@app.route("/me", methods=["GET"])
def me():
    if "user" not in session:
        return jsonify({"error": "Не авторизован"}), 401
    return jsonify({"username": session["user"]})

# Поиск пользователей
@app.route("/search", methods=["GET"])
def search():
    q = request.args.get("q", "").lower()
    result = [u for u in users if q in u.lower()]
    return jsonify(result)

# Блокировка звонков
@app.route("/toggle_calls", methods=["POST"])
def toggle_calls():
    if "user" not in session:
        return jsonify({"error": "Не авторизован"}), 401
    user = session["user"]
    users[user]["allow_calls"] = not users[user]["allow_calls"]
    return jsonify({"allow_calls": users[user]["allow_calls"]})

# Socket.IO события для звонков
@sio.event
def connect(sid, environ):
    print("Client connected:", sid)

@sio.event
def disconnect(sid):
    print("Client disconnected:", sid)

@sio.event
def call(sid, data):
    """Отправка звонка другому пользователю"""
    target = data.get("to")
    caller = data.get("from")
    if target in users and users[target]["allow_calls"]:
        sio.emit("incoming_call", {"from": caller}, to=sid)
    else:
        sio.emit("call_blocked", {"to": target}, to=sid)

if __name__ == "__main__":
    import eventlet
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 5000)), app)
