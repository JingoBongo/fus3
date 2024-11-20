import os
import subprocess

def stop_and_disable_service(service_name):
    try:
        subprocess.run(['sudo', 'systemctl', 'stop', service_name], check=True)
        print(f"Stopped {service_name} service")

        subprocess.run(['sudo', 'systemctl', 'disable', service_name], check=True)
        print(f"Disabled {service_name} service")

        service_path = f'/etc/systemd/system/{service_name}.service'
        if os.path.exists(service_path):
            os.remove(service_path)
            print(f"Removed service file at {service_path}")
        else:
            print(f"Service file {service_path} does not exist")

        subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
        print("Reloaded systemd daemon")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    service_name = 'fuse'  # Replace with your service name
    stop_and_disable_service(service_name)
