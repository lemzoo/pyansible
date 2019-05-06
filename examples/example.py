import getpass
import os

from pyansible import AnsibleDriver


remote_user = getpass.getuser()
private_key_file = ''
chdir = os.getcwd()
working_dir = f'{chdir}/examples'
verbosity = 0
vault_password = ''
configuration = {
    'ANSIBLE_REMOTE_USER': remote_user,
    'ANSIBLE_PRIVATE_KEY_FILE': private_key_file,
    'ANSIBLE_PLAYBOOKS_WORKING_DIR': working_dir,
    'ANSIBLE_VERBOSITY': verbosity,
    'ANSIBLE_VAULT_PASSWORD': ''
}

driver = AnsibleDriver(config=configuration)
playbook = 'list.yml'
host = 'localhost'
extra_vars = {'chdir': chdir}

result = driver.run(playbook, host, extra_vars)
assert result[0] == 0  # This is the result code
assert result[1] == 'RUN_OK'  # additional info
