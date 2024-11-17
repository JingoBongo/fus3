import streamlit as st
import requests

# Function to interact with Flask API
def interact_with_flask(endpoint, method='GET', data=None, params=None):
    base_url = "http://127.0.0.1:4053"
    url = f"{base_url}/{endpoint}"
    if method == 'GET':
        response = requests.get(url, params=params)
    elif method == 'POST':
        response = requests.post(url, json=data)
    elif method == 'DELETE':
        response = requests.delete(url, params=params)
    return response.json()

# Initialize session state variables
if "repos" not in st.session_state:
    st.session_state.repos = interact_with_flask("list_repos")

if "venvs" not in st.session_state:
    st.session_state.venvs = interact_with_flask("list_venvs")

# GitHub Repositories Section
st.title("GitHub Repositories")

if st.button("Show Repos"):
    st.session_state.repos = interact_with_flask("list_repos")
st.write(st.session_state.repos)

# Add Repo Section
st.title("Add Repository")
cols = st.columns([3, 1])
with cols[0]:
    new_repo_url = st.text_input("New Repo URL")
with cols[1]:
    if st.button("Add Repo"):
        interact_with_flask("add_repo", method='POST', data={'url': new_repo_url})
        st.session_state.repos = interact_with_flask("list_repos")  # Refresh repos

# Delete Repo Section
if st.session_state.repos:
    st.title("Delete Repository")
    cols = st.columns([3, 1])
    with cols[0]:
        del_repo_name = st.selectbox("Select Repo to Delete", options=[repo['name'] for repo in st.session_state.repos.values()])
    with cols[1]:
        if st.button("Delete Repo"):
            interact_with_flask("remove_repo", method='DELETE', params={'name': del_repo_name})
            st.session_state.repos = interact_with_flask("list_repos")  # Refresh repos

# Manage Instructions Section
st.title("Manage Instructions")

if st.session_state.repos:
    selected_repo = st.selectbox("Select Repo to Manage Instructions", options=[repo['name'] for repo in st.session_state.repos.values()])

    cols = st.columns([3, 1])
    with cols[0]:
        instructions_to_add = st.text_area("Instructions to Add (comma-separated)")
    with cols[1]:
        if st.button("Add Instructions"):
            instructions_list = [instr.strip() for instr in instructions_to_add.splitlines() if instr.strip()]
            interact_with_flask("add_instructions", method='POST', data={'name': selected_repo, 'instructions': instructions_list})

        if st.button("Remove Instructions"):
            interact_with_flask("delete_instructions", method='DELETE', params={'name': selected_repo})
else:
    st.write("No repositories available. Please add a repository first.")

# Virtual Environments Section
st.title("Virtual Environments")

if st.button("Show Venvs"):
    st.session_state.venvs = interact_with_flask("list_venvs")
st.write(st.session_state.venvs)

# Add Venv Section
cols = st.columns([3, 1])
with cols[0]:
    new_venv_name = st.text_input("New Venv Name")
with cols[1]:
    if st.button("Add Venv"):
        interact_with_flask("add_venv", method='POST', data={'name': new_venv_name})
        st.session_state.venvs = interact_with_flask("list_venvs")  # Refresh venvs

# Delete Venv Section
if st.session_state.venvs:
    st.title("Delete Virtual Environment")
    cols = st.columns([3, 1])
    with cols[0]:
        del_venv_name = st.selectbox("Select Venv to Delete", options=list(st.session_state.venvs.keys()))
    with cols[1]:
        if st.button("Delete Venv"):
            interact_with_flask("delete_venv", method='DELETE', params={'name': del_venv_name})
            st.session_state.venvs = interact_with_flask("list_venvs")  # Refresh venvs

# Process Management Section
st.title("Process Management")

if st.session_state.repos:
    cols = st.columns([3, 1])
    # Select repository to launch process
    with cols[0]:
        repo_name_to_launch = st.selectbox("Select Repo to Launch Process", options=[repo['name'] for repo in st.session_state.repos.values() if repo['status'] != 'running'])
    with cols[1]:
        if st.button("Launch Process"):
            interact_with_flask("launch_process", method='POST', data={'name': repo_name_to_launch})

    # Select repository to stop process
    with cols[0]:
        repo_name_to_stop = st.selectbox("Select Repo to Stop Process", options=[repo['name'] for repo in st.session_state.repos.values() if repo['status'] == 'running'])
    with cols[1]:
        if st.button("Stop Process"):
            interact_with_flask("stop_process", method='POST', data={'name': repo_name_to_stop})

if st.button("Show Repo Statuses"):
    statuses = interact_with_flask("statuses")
    st.write(statuses)
