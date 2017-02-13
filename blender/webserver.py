#!/usr/bin/python3

from flask import Flask, send_from_directory, render_template, send_file, g, session, make_response
from flask_socketio import SocketIO, emit
import eventlet.green.zmq as zmq
import eventlet
import json
import sys
from functools import wraps, update_wrapper
from datetime import datetime
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-n", "--host", dest="zmqhost",
                  help="connect to HOST for the zeroMQ queue", metavar="HOST", default="localhost")
parser.add_option("-p", "--port", dest="zmqport",
                  help="connect to zeromq port PORT", metavar="PORT", default="5556")
parser.add_option("-P", "--webport", dest="webport",
                  help="webserver listens on PORT", metavar="PORT", default="5000")

(options, args) = parser.parse_args()


app = Flask(__name__)
app.secret_key = "boo"
socketio = SocketIO(app)


def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
        
    return update_wrapper(no_cache, view)


@app.route('/')
def index():
    return send_file('index.html')


@socketio.on('connect')
def start_pushing():
    print("got connect on pos")
    session['running']=True


@socketio.on('disconnect')
def stop_pushing():
    print("disconnecting")
    session['running']=False


state = {
    'pos': (0,0,0,0,0,0)
}

# def inc_pos():
#     (x,y,z) = state['pos']
#     x += 0.01
#     y += 0.01
#     state['pos'] = (x,y)

# def bg_emit():
#     inc_pos()
#     (x,y,z) = state['pos']
#     socketio.emit('posupdate', dict(x=x,y=y,z=z))


def ros_to_3js(state_ros):
    '''
        in 3js:
            * X is van links naar rechts
            * Y is van boven naar onder
            * Z is van dichtbij naar veraf
        
        in ros:
            * X is van links naar rechts
            * Y is van veraf naar dichtbij
            * Z is van boven naar onder


    '''
    state_3js = {}
    state_3js['x']=state_ros['x']
    state_3js['y']=state_ros['z']
    state_3js['z']=state_ros['y']

    state_3js['rx']=state_ros['rx']
    state_3js['ry']=state_ros['ry']
    state_3js['rz']=state_ros['rz']
    return state_3js



def listen():
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    #socket.setsockopt(zmq.SUBSCRIBE,"1")
    socket.setsockopt_string(zmq.SUBSCRIBE,'')
    zmq_url = "tcp://%s:%s" % (options.zmqhost, options.zmqport)
    print("ZMQ: subscribe to %s" % zmq_url)
    socket.connect (zmq_url)
    while True:
        string = socket.recv().decode('utf-8')
        print(string)
        sys.stdout.flush()
        inp = json.loads(string)
        socketio.emit('posupdate', inp)


eventlet.spawn(listen)


@app.route("/<path:path>")
@nocache
def send_static(path):
    return send_from_directory('.',path)


if __name__ == "__main__":
    socketio.run(app,host='0.0.0.0',port=int(options.webport))

