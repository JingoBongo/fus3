Overview

This project provides a Flask-based backend and an optional Streamlit-based GUI for managing virtual environments, repositories, and runnable processes. It includes robust mechanisms for process control, vault management, and dynamic configuration. Users can enable or disable the Streamlit interface for a web-based GUI.
Key Features

- Virtual Environment Management: Create, delete, and list virtual environments.
- Repository Management: Add, remove, and list runnable repositories from GitHub.
- Instruction Handling: Parse and manipulate instruction files for repositories.
- Process Management: Launch and stop processes dynamically based on repository instructions.
- Streamlit Integration: Enable/disable a Streamlit-based GUI for enhanced usability.

The main goal is to have Fuse as a daemon background on Linux and to be able to easily manage your python services across your home network

Some details to be mentioned:
- Usage of Vaults. They are basically persistent dictionaries that different services can use at the same time, as well as use to change Fuse's behavior. See https://github.com/JingoBongo/vaults
- Fuse can clone locally repositories you tell him to clone, provide them with virtual environments on the go.
- Usage of so called barrel processes and instructions will allow Fuse to prepare venv and launch projects that require multiple steps to be launched. Instructions can be set manually or Fuse will try to find fuseinstructions.txt file in your project himself. Instructions also support dynamic data, for example {third_venv} will be replaced with virtual environment called third_ven, you don't have to remember it's path etc. Also using [requirements.txt] will tell Fuse to try to find such file in your repo, so in instructions you can simply use the line "{default_venv -m pip install [requirements.txt]}", Fuse will substitute proper files with absolute paths if possible. Barrel processes will allow to launch all commands you specify in instructions in a single popen process.
- In case you want to disable web ui or replace it with your own, you can tell Fuse to [GET] /start-streamlit or [GET] /stop-streamlit

Example of simplest service that uses fuse instructions file and dynamic values in it is https://github.com/JingoBongo/test_runnable

The idea of Fuse is to be highly modular, meaning I plan to develop separate modules in order to add features if needed and to avoid having large project in multiple smaller devices like home server/laptop/raspberry. You can expand this code however you want, that's the entire idea.