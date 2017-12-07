import socket
import subprocess
from flask import Flask, render_template

app = Flask(__name__)
proc = None

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    return s.getsockname()[0]

@app.route('/')
def hello():
    return render_template('index.html')

@app.route('/start', methods=['GET', 'POST'])
def start_secrupi():
    global proc
    
    print('> Start SecuriPi!')
    proc = subprocess.Popen(['python', 'SecuriPi.py', '-c', 'config.json'])
    print('> Process ID {}'.format(proc.pid))
    return 'Started!'

@app.route('/stop', methods=['GET', 'POST'])
def stop_securipi():
    global proc
    
    print('> Stop SecuriPi!')
    proc.kill()
    print('> Process {} killed!'.format(proc.pid))
    return 'Stopped!'

@app.route('/status', methods=['GET', 'POST'])
def status_securipi():
    global proc
    
    if proc is None:
        print('> SecuriPi is idle.')
        return 'Idle!'
    
    if proc.poll() is None:
        print('> SecuriPi is runninng (Process {})!'.format(proc.pid))
        return 'Running!'
    else:
        print('> SecuriPi is idle.')
        return 'Stopped!'

if __name__ == '__main__':
    print 'Connect to http://{}:5555 to control your SecuriPi!'.format(get_ip_address())
    app.run(host='0.0.0.0', port=5555, debug=False)

