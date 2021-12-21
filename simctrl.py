import subprocess
from flask import Flask, jsonify, request
from flask_redis import FlaskRedis
import psutil

# create app
app = Flask(__name__)
#app.config["REDIS_URL"] = "redis://sr1:6379"
redis_client = FlaskRedis(app)

# analyze and elaborate the provided VHDL file
def process_uploaded_file():
    subprocess.run(["ghdl-llvm", "-a", "circuit.vhdl"], check=True)
    subprocess.run(["ghdl-llvm", "-e", "gpio_test"], check=True)

# api endpoint to start simulation
@app.route('/start', methods = ['GET'])
def start():
    # check if a file has been successfully uploaded
    uploaded = redis_client.get('uploaded')
    # and whether the simulation is currently running
    pid = redis_client.get('pid')
    
    if not uploaded:
        code = 1
        msg = "No VHDL file uploaded!"
    elif pid:
        code = 1
        msg = "Simulation already started!"
    else:
        #proc = subprocess.Popen(["ghdl-llvm", "-r", "gpio_test", "--vpi=./vpi_test.vpi"])
        # launch simulation
        proc = subprocess.Popen(["ghdl-llvm", "-r", "gpio_test", "--vpi=/vpi_build/sim.vpi"])
        # record PID of simulation process
        redis_client.set('pid', proc.pid)
        # set return data
        code = 0
        msg = "Simulation started successfully!"
    return jsonify({'code': code, 'msg': msg})

# api endpoint to stop simulation
@app.route('/stop', methods = ['GET'])
def stop():
    # check if simulation is running
    pid = redis_client.get('pid')
    if pid:
        pid = int(pid)
        try:
            # attempt to kill simulation and child processes
            parent = psutil.Process(pid)    
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()
            parent.wait()
            # set return data on success
            code = 0
            msg = "Simulation stopped successfully!"
        except:
            # something went wrong
            code = 1
            msg = "Error stopping simulation!"
        finally:
            # remove PID from database
            redis_client.delete('pid')
    else:
        code = 1
        msg = "Simulation not running!"
    return jsonify({'code': code, 'msg': msg})

# api endpoint to upload simulation file
@app.route('/upload', methods = ['POST'])
def upload():
    # check if simulation is currently running
    pid = redis_client.get('pid')
    if pid:
        code = 1
        msg = "Simulation currently running!"
    else:
        # save file
        f = request.files['file']
        f.save("circuit.vhdl")
        try: 
            # attempt to process VHDL file
            process_uploaded_file()
            # set return data on success
            code = 0
            msg = "VHDL file processed successfully!"
            # record upload
            redis_client.set('uploaded', 1)
        except:
            code = 1
            msg = "Processing VHDL file failed!"
    return jsonify({'code': code, 'msg': msg})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)