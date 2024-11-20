import re
import os

from flask import Flask, request, jsonify
from vaults import Vault, set_root_path
from os_utils import delete_folder_with_contents
import atexit
import os_utils
from log_utils import logger as log
import signal
import sys

root_path = os.path.dirname(os.path.abspath(__file__))
venvs_dir = os.path.join(root_path, 'venvs')
runnables_dir = os.path.join(root_path, 'runnables')
fuse_instructions_file_name = 'fuseinstructions.txt'
is_windows_running = os_utils.is_windows_running()

default_venv_activate_path = os.path.join(root_path, 'venvs', 'default_venv',
                                          'Scripts' if is_windows_running else 'bin', 'activate')

set_root_path(runnables_dir)

venvs_vault = Vault('virtual_environments')
remote_repos_vault = Vault('remote_runnables_repositories')
commons_vault = Vault('commons')

app = Flask(__name__)
streamlit_process = None


def graceful_shutdown():
    log.info("Gracefully shutting down")
    os_utils.terminate_process(streamlit_process.pid)
    for repo in remote_repos_vault.list_keys():
        repo_dict = remote_repos_vault.get(repo)
        pid = repo_dict['PID']
        if pid:
            os_utils.terminate_process(pid)
        repo_dict['PID'] = None
        remote_repos_vault.put(repo_dict['name'], repo_dict)


def handle_signal(sig, frame):
    log.error(f"Emergency shutdown initiated by signal {sig}")
    graceful_shutdown()
    sys.exit(0)


def emergency_shutdown(exc_type, exc_value, traceback):
    log.error("Unhandled exception: Emergency shutdown")
    graceful_shutdown()
    sys.exit(1)


sys.excepthook = emergency_shutdown
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)
atexit.register(graceful_shutdown)


def create_directories():
    if not os.path.exists(venvs_dir):
        os.makedirs(venvs_dir)
    if not os.path.exists(runnables_dir):
        os.makedirs(runnables_dir)


def create_venv(env_path):
    abs_venv_path = os.path.join(venvs_dir, env_path)
    if not os.path.exists(abs_venv_path):
        try:
            log.info(f"Creating virtual environment at {abs_venv_path}")
            os_utils.start_system_barrel_process([f"python -m venv {abs_venv_path}"], wait_for_result=True)
            log.info("Virtual environment created successfully")
            venvs_vault.put(env_path, abs_venv_path)
            return {'status': 'created'}
        except Exception as e:
            log.error(f"Failed to create virtual environment: {e}")
            return {'status': 'error', 'error': str(e)}
    else:
        venvs_vault.put(env_path, abs_venv_path)
        log.info(f"Venv {env_path} exists already")
        return {'status': 'already exists'}


def delete_venv(venv_name):
    global venvs_vault
    if venv_name in venvs_vault.list_keys():
        delete_folder_with_contents(venvs_vault.pop(venv_name))


def purge_venvs_vault():
    global venvs_vault
    venvs_vault.delete_vault()
    venvs_vault = Vault('virtual_environments')


def parse_github_url(url):
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)", url)
    return match.groups() if match else ("Invalid URL", None)


def try_to_extract_instructions(folder_path, file_name):
    for root, _, files in os.walk(folder_path):
        if file_name in files:
            with open(os.path.join(root, file_name), 'r') as file:
                return file.read().splitlines()
    return []


def start_streamlit():
    global streamlit_process
    if streamlit_process is None:
        env = os.environ.copy()
        env['BROWSER'] = 'none'
        # TODO check if it is opened from wsl for example
        streamlit_process = os_utils.start_system_barrel_process(["streamlit run streamlitapp.py"])
        # streamlit_process = os_utils.start_system_barrel_process(["streamlit run streamlitapp.py --server.headless true"])
        commons_vault.put("streamlit_enabled", True)


def stop_streamlit():
    global streamlit_process
    if streamlit_process is not None:
        os_utils.terminate_process(streamlit_process.pid)
        streamlit_process = None
        commons_vault.put("streamlit_enabled", False)


def stop_process(name):
    repo_dict = remote_repos_vault.get(name)
    os_utils.terminate_process(repo_dict['PID'])
    repo_dict['PID'] = None
    repo_dict['status'] = 'stopped'
    remote_repos_vault.put(name, repo_dict)


def find_file(filename, search_path='.'):
    if not os.path.isabs(search_path):
        search_path = os.path.abspath(search_path)
    for root, dirs, files in os.walk(search_path):
        if filename in files:
            return os.path.join(root, filename)

    return None


def replace_venv_placeholders(input_data):
    pattern = r"\{(.*?)\}"

    def replacement(match):
        key = match.group(1)
        cut_path = venvs_vault.get(key) or 'default_venv'
        return os.path.join(cut_path, 'Scripts' if is_windows_running else 'bin', 'python')

    if isinstance(input_data, str):
        return re.sub(pattern, replacement, input_data)
    elif isinstance(input_data, list):
        return [re.sub(pattern, replacement, string) for string in input_data]
    else:
        raise ValueError("Input data must be a string or a list of strings")


def find_bracket_placeholders(string):
    import re
    pattern = re.compile(r'\[(.* ?)\]')
    return pattern.findall(string)


def replace_file_placeholders(input_data, folder_path):
    if isinstance(input_data, str):
        input_data = [input_data]
    output_data = []
    for string in input_data:
        modified_string = string
        placeholders = find_bracket_placeholders(string)
        for placeholder in placeholders:
            file_path = find_file_in_subfolders(folder_path, placeholder)
            if file_path:
                absolute_path = os.path.abspath(file_path)
                modified_string = modified_string.replace(f'[{placeholder}]', absolute_path)
        output_data.append(modified_string)

    if len(output_data) == 1:
        return output_data[0]
    return output_data


def find_file_in_subfolders(folder_path, filename):
    if not os.path.exists(folder_path):
        log.error(f"Folder path does not exist: {folder_path}")
    else:
        for root, dirs, files in os.walk(folder_path):
            if filename in files:
                return os.path.join(root, filename)
    return None


def add_instructions(dict_name, instructions):
    if dict_name in remote_repos_vault.list_keys():
        repo_element = remote_repos_vault.get(dict_name)
        repo_element['instructions'] = instructions
        remote_repos_vault.put(dict_name, repo_element)
        return {'message': 'Instructions added successfully'}
    return {'message': 'Instructions not added'}


@app.route('/add_repo', methods=['POST'])
def add_repo():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing required field: url'}), 400
    username, repository = parse_github_url(data.get('url'))
    if repository in remote_repos_vault.list_keys():
        return jsonify({'error': 'Repository already exists'}), 400
    if not repository:
        return jsonify({'error': 'Invalid GitHub URL'}), 400
    keep_alive = data.get('keepAlive', False)
    repo_path = os.path.join(runnables_dir, repository)

    if not os.path.exists(repo_path) or not any(os.scandir(repo_path)):
        os_utils.start_system_barrel_process([f"git clone {data.get('url')}"], folder=runnables_dir,
                                             wait_for_result=True)
    instructions = try_to_extract_instructions(repo_path, fuse_instructions_file_name)
    remote_repos_vault.put(repository, {
        'url': data.get('url'),
        'name': repository,
        'author': username,
        'instructions': instructions,
        'PID': None,
        'status': 'stopped',
        'keepalive': keep_alive
    })
    return jsonify({'message': 'Repository added successfully'}), 201


@app.route('/remove_repo', methods=['DELETE'])
def remove_repo():
    name = request.args.get('name')
    if name in remote_repos_vault.list_keys():
        stop_process(name)
        # damn this is stupid. args are always string.
        if request.args.get('removeFiles') == 'True':
            delete_folder_with_contents(os.path.join(runnables_dir, name))
        remote_repos_vault.pop(name)
        return jsonify({'message': 'Repository removed successfully'})
    return jsonify({'error': 'No such repository'})


@app.route('/list_repos', methods=['GET'])
def list_repos():
    keys = remote_repos_vault.list_keys()
    dict = {key: remote_repos_vault.get(key) for key in keys}
    return jsonify(dict)


@app.route('/add_instructions', methods=['POST'])
def add_instructions_endpoint():
    data = request.get_json()
    name = data.get('name')
    instructions = data.get('instructions', [])
    return jsonify(add_instructions(name, instructions))


@app.route('/delete_instructions', methods=['DELETE'])
def delete_instructions():
    name = request.args.get('name')
    return jsonify(add_instructions(name, []))


@app.route('/list_venvs', methods=['GET'])
def list_venvs():
    keys = venvs_vault.list_keys()
    return jsonify({key: venvs_vault.get(key) for key in keys})


@app.route('/add_venv', methods=['POST'])
def add_venv():
    data = request.get_json()
    create_venv(data.get('name'))
    return jsonify({'message': 'Virtual environment added successfully'})


@app.route('/delete_venv', methods=['DELETE'])
def delete_venv_endpoint():
    name = request.args.get('name')
    delete_venv(name)
    return jsonify({'message': 'Virtual environment deleted successfully'})


@app.route('/set_name', methods=['GET'])
def set_fuse_name():
    # this is very intentional a GET, for easiest last moment change over the browser from your phone or whatever
    fuse_name = request.args.get('fuse_name')
    commons_vault.put('node_name', fuse_name)
    return jsonify({'response': "I hope you won't shoot your own knee with improper name"})


@app.route('/get_name', methods=['GET'])
def get_fuse_name():
    name = commons_vault.get('node_name')
    if not name:
        return jsonify({'node_name': 'generic_fuse_node'})
    return jsonify({'node_name': name})


@app.route('/launch_process', methods=['POST'])
def launch_process():
    name = request.json.get('name')
    if name in remote_repos_vault.list_keys():
        repo_dict = remote_repos_vault.get(name)
        repo_path = os.path.join(runnables_dir, name)
        if not os.path.exists(repo_path) or not any(os.scandir(repo_path)):
            os_utils.start_system_barrel_process([f"git clone {repo_dict['url']}"], folder=runnables_dir,
                                                 wait_for_result=True)
        if not repo_dict['instructions']:
            instructions = try_to_extract_instructions(repo_path, fuse_instructions_file_name)
            if not instructions:
                return jsonify({'error': 'Missing instructions'}), 400
            repo_dict['instructions'] = instructions
        venv_curated_instructions = replace_venv_placeholders(repo_dict['instructions'])
        filename_curated_instructions = replace_file_placeholders(venv_curated_instructions, repo_path)
        process = os_utils.start_system_barrel_process(filename_curated_instructions, folder=repo_path)
        repo_dict['PID'] = process.pid
        repo_dict['status'] = 'running'
        remote_repos_vault.put(name, repo_dict)
        return jsonify({'message': 'Process launched successfully', 'pid': process.pid})
    return jsonify({'message': 'Process was not launched'})


@app.route('/stop_process', methods=['POST'])
def stop_process_endpoint():
    name = request.json.get('name')
    if name in remote_repos_vault.list_keys():
        stop_process(name)
        return jsonify({'message': 'Process stopped successfully'})
    return jsonify({'error': 'No such process'}), 400


@app.route('/statuses', methods=['GET'])
def statuses():
    keys = remote_repos_vault.list_keys()
    repo_dict = {key: remote_repos_vault.get(key) for key in keys}
    return jsonify([{repo['name']: repo['status']} for repo in repo_dict.values()])


@app.route('/purge_venvs_vault', methods=['GET'])
def purge_venvs_vault_endpoint():
    purge_venvs_vault()
    return jsonify({'respone': 'Vaults purged'}), 200


@app.route('/start-streamlit', methods=['GET'])
def enable_streamlit():
    start_streamlit()
    return jsonify({"message": "Streamlit started"}), 200


@app.route('/stop-streamlit', methods=['GET'])
def disable_streamlit():
    stop_streamlit()
    return jsonify({"message": "Streamlit stopped"}), 200


# TODO check in linux
# TODO see where i can add lru_cache
# TODO check if logs work properly

def main():
    create_directories()
    create_venv('default_venv')
    streamlit_var = commons_vault.get('streamlit_enabled')
    if streamlit_var:
        start_streamlit()
    app.run(host="0.0.0.0", port=4053, use_reloader=False)


if __name__ == '__main__':
    main()
