import subprocess
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

DEFAULT_SERVICE_CONFIG = {
    "service1": {
        "env_path": "/path/to/service1/venv/bin/activate",
        "script_path": "/path/to/service1/main.py",
        "requirements_path": "/path/to/service1/requirements.txt"
    },
    "service2": {
        "env_path": "/path/to/service2/venv/bin/activate",
        "script_path": "/path/to/service2/main.py",
        "requirements_path": "/path/to/service2/requirements.txt"
    }
    # Add more services as needed
}

def install_requirements(env_path, requirements_path):
    if os.path.isfile(requirements_path):
        install_command = f"source {env_path} && pip install -r {requirements_path}"
        result = subprocess.run(install_command, shell=True, executable="/bin/bash", capture_output=True, text=True)
        if result.returncode == 0:
            return {"message": "Requirements installed successfully"}
        else:
            return {"error": "Failed to install requirements", "details": result.stderr}
    return {"message": "No requirements to install"}

@app.route('/launch', methods=['POST'])
def launch_service():
    data = request.get_json()
    service_name = data.get("service")

    if service_name not in DEFAULT_SERVICE_CONFIG:
        return jsonify({"error": "Service not found"}), 404

    service_info = DEFAULT_SERVICE_CONFIG[service_name]
    env_path = service_info["env_path"]
    script_path = service_info["script_path"]
    requirements_path = service_info["requirements_path"]

    # Install requirements
    install_result = install_requirements(env_path, requirements_path)
    if "error" in install_result:
        return jsonify(install_result), 500

    # Launch the service in the virtual environment
    command = f"source {env_path} && python {script_path}"
    process = subprocess.Popen(command, shell=True, executable="/bin/bash")

    return jsonify({"message": f"{service_name} launched", "pid": process.pid})

if __name__ == '__main__':
    # 1. if doesnt exist yet, create default venv
    
    # 1.1 if not created sucessfully 
    
    # 2. create runnables folder if doesnt exist, create runnables_repo_list if doesnt exist
    
    # shared folder for vault can be printed?
    
    # shared module can be added to python venv.. but what about requirements then?
    # maybe for now dont use vaults for modules then? but if I make default venv, I can add it there.
    
    app.run(host="0.0.0.0", port=5000)





# test vaults
# from vaults import Vault


#     class Butterfly:
#         aboba = 10


#     volt = Vault('selectTestVault')
#     volt.put('test', 'string')
#     volt.put('test', 'updatedstring')

#     vol2 = Vault('newvolt')

#     volt.put('test2', Butterfly())
#     vol2.put('qwerqwerqwergqwegrqwegrqwersdfsdfgdfgvqwerqwerqwergqwegrqwegrqwersdfsdfgdfgvqwerqwerqwergqwegrqwegrqwersdfsdfgdfgvqwerqwerqwergqwegrqwegrqwersdfsdfgdfgvqwerqwerqwergqwegrqwegrqwersdfsdfgdfgv',1)
#     print(volt.get('test'))
#     print(volt.get('test2'))
#     print(vol2.get('qwerqwerqwergqwegrqwegrqwersdfsdfgdfgvqwerqwerqwergqwegrqwegrqwersdfsdfgdfgvqwerqwerqwergqwegrqwegrqwersdfsdfgdfgvqwerqwerqwergqwegrqwegrqwersdfsdfgdfgvqwerqwerqwergqwegrqwegrqwersdfsdfgdfgv'))
    