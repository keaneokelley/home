from flask import Flask, render_template, request, redirect, make_response, flash, abort, session
from flask_socketio import SocketIO, emit, disconnect
from flask_login import LoginManager, login_required, login_user, current_user, logout_user
from pywebpush import WebPusher

from threading import Thread
import os
import functools
import hashlib
import json

from modules.bulb import Bulb
#from modules.gcm import GCM
from modules.utils import RGBfromhex
from models import *

app = Flask(__name__)
app.secret_key = '\xff\xe3\x84\xd0\xeb\x05\x1b\x89\x17\xce\xca\xaf\xdb\x8c\x13\xc0\xca\xe4'
API_KEY = 'AIzaSyCa349yW3-oWMbYRHl21V1IgGRyM6O7PW4'
app.debug = True
socketio = SocketIO(app)
login_manager = LoginManager()
login_manager.init_app(app)
devices = []

# Temporary, until we allow multiple instances of a thing
b = Bulb()
# End Temporary

some_random_string = lambda: hashlib.sha1(os.urandom(128)).hexdigest()


def ws_login_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            print("D/C WS attempt")
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped


def login_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return abort(403)
        return f(*args, **kwargs)
    return wrapped


@app.route('/', methods=['GET', 'POST'])
def index(*args, **kwargs):
    bulbs = [bulb for bulb in devices if bulb.category == 'bulb']
    return render_template('index.html', bulbs=bulbs,
                                         devices=devices,
                                         )


### TEST ###
@app.route('/jarvis_test')
def jarvis(*args, **kwargs):
    return render_template('jarvis.html')


@app.route('/jarvis')
def altjarvis(*args, **kwargs):
    return render_template('altjarvis.html')
###


@app.route('/api/command', methods=['POST'])
@login_required
def command():
    pass

@app.route('/api/admin/<action>')
@login_required
def admin(action):
    pass


@socketio.on('admin', namespace='/ws')
@ws_login_required
def admin_ws(data):
    if not current_user.admin:
        disconnect()
    if data['action'] == 'add':
        d, created = Device.create_or_get(id=data['id'], name=data['name'], category=data['category'], data=data['data'] or '{}')
        if created:
            devices.append(d.get_object())
        else:
            d.category = data['category']
            d.data = data['data']
            d.save()
            old = devices.filter(lambda x: x.name == d.name)[0]
            devices.insert(devices.index(old), d.get_object)
            devices.delete(old)
        emit('message', 'Devices updated, please refresh.', broadcast=True)
    if data['action'] == 'delete':
        d = Device.get(id=data['id'])
        device.remove([device for device in devices if device.id == d.id][0])
        d.delete_instance()

### TEST ###
@socketio.on('send transcript', namespace='/jarvis')
def test_jarvis(transcript):
    if "off" in transcript:
        b.change_color(0, 0, 0)
    elif "on" in transcript or \
            "white" in transcript:
        b.change_color(255, 255, 255)
    elif "red" in transcript:
        b.change_color(255, 0, 0)
    elif "green" in transcript:
        b.change_color(0, 255, 0)
    elif "blue" in transcript:
        b.change_color(0, 0, 255)
    emit('return transcript', transcript)
###

@socketio.on('subscribe', namespace='/ws')
@ws_login_required
def subscribe(subscriber):
    s, created = Subscriber.get_or_create(
        endpoint=subscriber.get('endpoint'),
        auth=subscriber.get('keys')['auth'],
        p256dh=subscriber.get('keys')['p256dh'],
        user=current_user.id)
    if created or True:
        WebPusher(subscriber).send(
            json.dumps({'body': "Subscribed to push notifications!"}),
            gcm_key=API_KEY)


@socketio.on('change color', namespace='/ws')
@ws_login_required
def request_change_color(message):
    emit('push color', {"device": message['device'], "color": message['color']}, broadcast=True)
    for bulb in devices[int(message['device']) - 1].devices:
        Thread(target=bulb.change_color, args=(
            tuple(RGBfromhex(message['color'])) +
            (message.get('bright', 100),)
        ))
        bulb.change_color(*RGBfromhex(message['color']),
                        brightness=message.get('bright', 100))


@socketio.on('outmap', namespace="/ws")
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
    #response.headers['Content-Security-Policy'] = "connect-src 'self'"
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


app.jinja_env.globals['csrf_token'] = generate_csrf_token


if __name__ == '__main__':
    db_init()
    for device in Device.select():
        devices.append(device.get_object())
    devices.append(DeviceMapper(2, "Living Room", "bulb", devices=[
        Bulb('172.16.42.199'),
        Bulb('172.16.42.200'),
    ]))
    devices.append(DeviceMapper(3, "Bedroom", "bulb", devices=[
        Bulb('192.168.1.123'),
    ]))
    try:
        import eventlet
        eventlet.monkey_patch()
        print('Using eventlet')
        create_thread_func = lambda f: f
        start_thread_func = lambda f: eventlet.spawn(f)
    except ImportError:
        try:
            import gevent
            import gevent.monkey
            gevent.monkey.patch_all()
            print('Using gevent')
            create_thread_func = lambda f: gevent.Greenlet(f)
            start_thread_func = lambda t: t.start()
        except ImportError:
            import threading
            print('Using threading')
            create_thread_func = lambda f: threading.Thread(target=f)
            start_thread_func = lambda t: t.start()
    socketio.run(app, debug=True)
