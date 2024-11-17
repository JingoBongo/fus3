import subprocess
import platform
import psutil

one_thousand_to_the_power_3 = 1024 ** 3
slash = "/"


def is_linux_running():
    return platform.system() == "Linux"


def is_windows_running():
    return platform.system() == "Windows"


def get_memory_percent_load():
    return psutil.virtual_memory().percent


def get_free_memory_percend_load():
    return psutil.virtual_memory().available * 100 / psutil.virtual_memory().total


def get_cpu_percent_load():
    return psutil.cpu_percent(interval=1, percpu=True)


def get_cpu_load_avg():
    load = get_cpu_percent_load()
    return sum(load) / len(load)


def get_folder_total_space_gbyte(folder):
    disk_usage = psutil.disk_usage(folder)
    return disk_usage.total / one_thousand_to_the_power_3


def get_folder_free_space_gbyte(folder):
    disk_usage = psutil.disk_usage(folder)
    return disk_usage.free / one_thousand_to_the_power_3


def get_folder_used_space_gbyte(folder):
    return get_folder_total_space_gbyte(folder) - get_folder_free_space_gbyte(folder)


def get_hard_drive_total_space_gbyte():
    return get_folder_total_space_gbyte(slash)


def get_hard_drive_free_space_gbyte():
    return get_folder_free_space_gbyte(slash)


def check_there_is_enough_free_space():
    return get_folder_free_space_gbyte(slash) > 20


def get_hard_drive_used_space_gbyte():
    return get_folder_used_space_gbyte(slash)


def start_system_barrel_process(commands: list, folder = None, wait_for_result = False):
    if len(commands) == 0:
        print('0 commands was passed to start_system_revoler_process')
        return
    if len(commands) > 1:
        prefix = ' & ' if is_windows_running() else ' && '
        str_commands = prefix.join(commands)
    else:
        str_commands = ' '.join(commands)
    if wait_for_result:
        proc = subprocess.Popen(str_commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd=folder)
        output, err = proc.communicate()
        return output
    else:
        return subprocess.Popen(str_commands, shell=True, cwd=folder)


# print(start_system_barrel_process(['pip3 list'], wait_for_result=True))