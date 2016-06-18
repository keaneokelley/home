from flask import Flask, render_template, request, redirect, make_response, flash, abort, session
from flask_socketio import SocketIO, emit, disconnect
from flask_login import LoginManager, login_required, login_user, current_user, logout_user
import os, functools, hashlib

from modules.bulb import Bulb
from modules.utils import RGBfromhex
from models import *

app = Flask(__name__)
app.secret_key = '\xff\xe3\x84\xd0\xeb\x05\x1b\x89\x17\xce\xca\xaf\xdb\x8c\x13\xc0\xca\xe4'
socketio = SocketIO(app)
login_manager = LoginManager()
login_manager.init_app(app)

some_random_string = lambda: hashlib.sha1(os.urandom(128)).hexdigest()

def ws_login_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped

@app.route('/', methods=['GET', 'POST'])
def index(*args, **kwargs):
    return render_template('bulb.html')

@socketio.on('change color', namespace='/bulb')
@ws_login_required
def request_change_color(message):
    emit('push color', message['color'], broadcast=True)
    b = Bulb() # Temporary
    b.change_color(*RGBfromhex(message['color']),
                 brightness=message.get('bright', 100))

@socketio.on('outmap', namespace="/bulb")
@ws_login_required
def reset_color_preview(message):
    emit('preview reset', message['color'], broadcast=True)

@login_manager.user_loader
def user_loader(user_id):
    return User.get(username=user_id)

@app.route('/login', methods=['POST'])
def login():
    user = User.get(username=request.form.get('username'))
    if user.check_password(request.form.get('password')):
        login_user(user)
        flash('Logged in successfully.')
    return redirect('/')

@app.route("/logout")
@login_required
def logout():
        logout_user()
        return redirect('/')

# This hook ensures that a connection is opened to handle any queries
# generated by the request.
@app.before_request
def _db_connect():
    db.connect()

# This hook ensures that the connection is closed when we've finished
# processing the request.
@app.teardown_request
def _db_close(exc):
    if not db.is_closed():
        db.close()

@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = session.pop('_csrf_token', None)
        if not token or token != request.form.get('_csrf_token'):
            abort(403)

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = some_random_string()
    return session['_csrf_token']

@app.after_request
def add_header(response):
    response.headers['Content-Security-Policy'] = "connect-src 'self'"
    return response

app.jinja_env.globals['csrf_token'] = generate_csrf_token

if __name__ == '__main__':
    db_init()
    socketio.run(app, debug=True)
