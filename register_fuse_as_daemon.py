import os
import subprocess
import venv
import sys


def is_windows_running():
    return os.name == 'nt'


def create_venv(venv_dir):
    venv.create(venv_dir, with_pip=True)
    change_permissions(venv_dir)
    print(f"Created virtual environment in {venv_dir}")


def setup_service(project_dir, service_file, service_name, user, group, use_venv):
    if use_venv:
        venv_dir = os.path.join(project_dir, 'default_venv')
        create_venv(venv_dir)
        python_executable = os.path.join(venv_dir, 'bin', 'python')
    else:
        python_executable = os.path.abspath(sys.executable)

    working_directory = project_dir
    subprocess.run(
        [os.path.join(venv_dir, 'bin', 'pip'), 'install', '-r', os.path.join(working_directory, 'fuse_requirements.txt')],
        check=True)
    print("Installed requirements from requirements.txt")

    exec_start = f'{python_executable} {os.path.join(project_dir, service_name)}.py'

    service_content = f"""
[Unit]
Description=Fuse Service Manager
After=network.target

[Service]
User={user}
Group={group}
WorkingDirectory={working_directory}
ExecStart={exec_start}
Restart=always

[Install]
WantedBy=multi-user.target
"""

    service_path = f'/etc/systemd/system/{service_name}.service'
    with open(service_path, 'w') as f:
        f.write(service_content)
    print(f"Created service file at {service_path}")


def change_permissions(path):
    print(f"Changing permissions of {path}")
    os.chmod(path, 0o755)  # Set read-write-execute permissions
    for root, dirs, files in os.walk(path):
        for d in dirs:
            os.chmod(os.path.join(root, d), 0o755)
        for f in files:
            os.chmod(os.path.join(root, f), 0o755)


def reload_and_start_service(service_name):
    subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
    print("Reloaded systemd daemon")

    subprocess.run(['sudo', 'systemctl', 'start', service_name], check=True)
    print(f"Started {service_name} service")

    subprocess.run(['sudo', 'systemctl', 'enable', service_name], check=True)
    print(f"Enabled {service_name} service")


if __name__ == "__main__":
    project_dir = os.getcwd()
    service_file_name = 'fuse.service'
    service_name = 'fuse'
    # I highly suggest to replace root with your user and group
    user = 'root'  # Replace with the user to run the service
    group = 'root'  # Replace with the group to run the service
    use_venv = True  # Set to False to use the current Python interpreter

    change_permissions(project_dir)
    setup_service(project_dir, service_file_name, service_name, user, group, use_venv)
    reload_and_start_service(service_name)
