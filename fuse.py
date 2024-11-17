import re
import subprocess
import os
from flask import Flask, request, jsonify
from vaults import Vault, set_root_path
import venv
import os_utils
from log_utils import logger as log
import shutil

root_path = os.path.dirname(os.path.abspath(__file__))

default_venv_activate_path = os.path.join(root_path, os.path.normpath('venvs/default_venv/Scripts/activate'))
set_root_path(os.path.join(root_path, 'runnables'))

venvs_vault = Vault('virtual_environments')
remote_repos_vault = Vault('remote_runnables_repositories')
runnables = []

app = Flask(__name__)


def create_directories():
    # Create 'runnables' folder if it doesn't exist
    if not os.path.exists("venvs"):
        os.makedirs("venvs")

    if not os.path.exists("runnables"):
        os.makedirs("runnables")
    # Create 'runnables_repo_list' file if it doesn't exist
    if not os.path.exists("runnables/runnables_repo_list.txt"):
        with open("runnables/runnables_repo_list.txt", 'w') as f:
            f.write("# Repository list\n")


def create_venv(env_path):
    env_path_added = os.path.join('venvs', env_path)
    abs_venv_path = os.path.abspath(env_path_added)

    if not os.path.exists(abs_venv_path):
        try:
            log.info(f"Creating virtual environment at {abs_venv_path}")
            # Create the virtual environment
            resu = os_utils.start_system_barrel_process([f"python -m venv {abs_venv_path}"], wait_for_result=True)
            print(resu)
            print(abs_venv_path)
            log.info("Virtual environment created successfully")
            venvs_vault.put(env_path, abs_venv_path)
            return {'status': 'created'}
        except Exception as e:
            log.error(f"Failed to create virtual environment: {e}")
            return {'status': 'error', 'error': str(e)}, 400
    else:
        venvs_vault.put(env_path, abs_venv_path)
        log.info(f"Venv {env_path} exists already")
        return {'status': 'already exists'}


def delete_folder_with_contents(folder_path):
    """Delete a folder and all of its contents."""
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        try:
            shutil.rmtree(folder_path)  # Recursively deletes the folder and its contents
            log.info(f"Folder '{folder_path}' and its contents have been deleted.")
            return {'status': 'deleted'}
        except Exception as e:
            log.exception(f"Error deleting folder: {e}")
            return {'status': 'error'}
    else:
        log.error(f"Folder '{folder_path}' does not exist.")
        return {'status': 'does not exist'}


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


@app.route('/add_repo', methods=['POST'])
def add_repo():
    data = request.get_json()
    # post only adds entire url, I dont need the rest, the rest will be deducted from url
    username, repository = parse_github_url(data.get('url'))
    keep_alive = data.get('keepAlive', True)
    remote_repos_vault.put(repository, {
        'url': data.get('url'),
        'name': repository,
        'author': username,
        'instructions': [],
        'PID': None,
        'status': 'stopped',
        'keepalive': keep_alive
    })
    return jsonify({'message': 'Repository added successfully'}), 201


@app.route('/remove_repo', methods=['DELETE'])
def remove_repo():
    name = request.args.get('name')
    remote_repos_vault.pop(name)
    return jsonify({'message': 'Repository removed successfully'})


@app.route('/list_repos', methods=['GET'])
def list_repos():
    keys = remote_repos_vault.list_keys()
    dict = {key: remote_repos_vault.get(key) for key in keys}
    return jsonify(dict)

def manipulate_instructions(dict_name, instructions):
    if dict_name in remote_repos_vault.list_keys():
        repo_element = remote_repos_vault.get(dict_name)
        repo_element['instructions'] = instructions
        remote_repos_vault.put(dict_name, repo_element)
        return {'message': 'Instructions added successfully'}
    return {'message': 'Instructions not added'}



@app.route('/add_instructions', methods=['POST'])
def add_instructions():
    data = request.get_json()
    name = data.get('name')
    instructions = data.get('instructions', [])
    return jsonify(manipulate_instructions(name, instructions))


@app.route('/delete_instructions', methods=['DELETE'])
def delete_instructions():
    name = request.args.get('name')
    return jsonify(manipulate_instructions(name, []))


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




def find_file(filename, search_path='.'):
    """
    Finds the specified filename in the given directory and its subdirectories.

    :param filename: Name of the file to search for.
    :param search_path: Directory to start the search from. Defaults to the current directory.
    :return: Absolute path to the file if found, otherwise None.
    """
    # Handle relative paths
    if not os.path.isabs(search_path):
        search_path = os.path.abspath(search_path)

    # Use glob to search for the file in the directory and its subdirectories
    for root, dirs, files in os.walk(search_path):
        if filename in files:
            return os.path.join(root, filename)

    return None

# Example usage
file_to_find = "requirements.txt"
search_directory = "./foldername"

found_file_path = find_file(file_to_find, search_directory)
if found_file_path:
    print(f"File found: {found_file_path}")
else:
    print("File not found.")


def replace_venv_placeholders(input_data):
    pattern = r"\{(.*?)\}"
    def replacement(match):
        key = match.group(1)
        cut_path = venvs_vault.get(key) or 'default_venv'
        if os_utils.is_windows_running():
            return os.path.join(cut_path, 'Scripts', 'python.exe')
        else: # Linux/macOS
            return os.path.join(cut_path, 'bin', 'python')

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
    for root, dirs, files in os.walk(folder_path):
        if filename in files:
            return os.path.join(root, filename)
    return None



@app.route('/launch_process', methods=['POST'])
def launch_process():
    name = request.json.get('name')
    print('launch triggered')
    print(f"name: {name}")
    if name in remote_repos_vault.list_keys():
        repo_dict = remote_repos_vault.get(name)
        runnables_path = os.path.join(root_path, 'runnables')
        repo_path = os.path.join(runnables_path, name)



        if not os.path.exists(repo_path):
            print(f"This will be eexecuted first: {[f"git clone {repo_dict['url']}"]}")
            os_utils.start_system_barrel_process([f"git clone {repo_dict['url']}"], folder=runnables_path, wait_for_result=True)


        venv_curated_instructions = replace_venv_placeholders(repo_dict['instructions'])
        filename_curated_instructions = replace_file_placeholders(venv_curated_instructions, repo_path)
        print(filename_curated_instructions)
        process = os_utils.start_system_barrel_process(filename_curated_instructions, folder=repo_path)
        repo_dict['PID'] = process.pid
        repo_dict['status'] = 'running'
        remote_repos_vault.put(name, repo_dict)
        return jsonify({'message': 'Process launched successfully', 'pid': process.pid})
        # return jsonify({'message': 'Process launched successfully', 'pid': 555})
    return jsonify({'message': 'Process was not launched'})

@app.route('/stop_process', methods=['POST'])
def stop_process():
    name = request.json.get('name')
    if name in remote_repos_vault.list_keys():
        repo_dict = remote_repos_vault.get(name)
        if os_utils.is_linux_running():
            command = f"kill {repo_dict['PID']}"
        else:
            command = f"taskkill /PID {repo_dict['PID']} /F"
        os_utils.start_system_barrel_process([command])
        repo_dict['PID'] = None
        remote_repos_vault.put(name, repo_dict)
    return jsonify({'message': 'Process stopped successfully'})

@app.route('/statuses', methods=['GET'])
def statuses():
    keys = remote_repos_vault.list_keys()
    dict = {key: remote_repos_vault.get(key) for key in keys}
    return jsonify([{repo['name']: repo['status']} for repo in dict.values()])




# TODO: used anywhere?
@app.route('/purge_venvs_vault', methods=['GET'])
def purge_venvs_vault_endpoint():
    purge_venvs_vault()
    return jsonify({'respone': 'Vaults purged'}), 200


# @app.route('/create_venv/<venv_name>', methods=['GET'])
# def create_venv_endpoint(venv_name):
#     return jsonify(create_venv(venv_name))


# @app.route('/delete_venv/<venv_name>', methods=['GET'])
# def delete_venv_endpoint(venv_name):
#     return jsonify(delete_venv(venv_name))


def main():
    # 1. if doesnt exist yet, create default venv
    # 2. create runnables folder if doesnt exist, create runnables_repo_list if doesnt exist

    create_directories()

    create_venv('default_venv')
    # todo for life ping add venv checker folder, so it equals what is in folders with vault( and local repo checker)
    # shared folder for vault can be printed?

    # shared module can be added to python venv.. but what about requirements then?
    # maybe for now dont use vaults for modules then? but if I make default venv, I can add it there.

    app.run(host="0.0.0.0", port=4053)


if __name__ == '__main__':
    main()
