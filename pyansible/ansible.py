import sys

import os

from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.module_utils._text import to_bytes, to_text
from ansible.parsing.dataloader import DataLoader
from ansible.parsing.vault import VaultSecret
from ansible.plugins.callback.default import CallbackModule
from ansible.utils.display import Display as AnsibleDisplay
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager


class AnsiblePlaybookNotFoundError(Exception):
	pass


RUN_OK = 'RUN_OK'
RUN_ERROR = 'RUN_ERROR'
RUN_FAILED_HOSTS = 'RUN_FAILED_HOSTS'
RUN_UNREACHABLE_HOSTS = 'RUN_UNREACHABLE_HOSTS'
RUN_FAILED_BREAK_PLAY = 'RUN_FAILED_BREAK_PLAY'
RUN_UNKNOWN_ERROR = 'RUN_UNKNOWN_ERROR'


class InventoryOptions:
	# TODO: Inventory maybe used as name tuple but what happens during
	# ansible execution when you try to change the user which is set
	# via the name tuple. An error may be occur. So, in this version, we
	# use an object to represent which is easy to deal with ansible.

	def __init__(self, remote_user, private_key_file, module_path):
		self.set_default_options()
		self.remote_user = remote_user
		self.private_key_file = private_key_file
		self.module_path = module_path

	def set_default_options(self):
		self.listtags = False
		self.listtasks = False
		self.listhosts = False
		self.syntax = True
		self.check = False
		self.diff = False
		self.forks = 5
		self.timeout = 10
		self.verbosity = 4
		self.roles_path = './roles'
		self.become = None
		self.become_method = 'sudo'
		self.become_user = 'root'
		self.connection = 'ssh'


class Display(AnsibleDisplay):
	"""
	Display catcher which allows to get all stack trace druing execution
	Available verbosity level is 0=v, 1=vv, 2=vvv, 3=vvvv, 4=vvvvv, 5=vvvvvv
	"""

	def __init__(self, verbosity=0):
		super().__init__(verbosity)
		self.log_storage = []

	def display(self, msg, color=None, stderr=False,
				screen_only=False, log_only=False):
		print(f'display method was called with these args: msg={msg},'
			  f'color={color}, stderr={stderr}, screen_only={screen_only},'
			  f'log_only={log_only}')

		msg2 = to_bytes(msg, encoding=self._output_encoding(stderr=stderr))
		if sys.version_info >= (3,):
			# Convert back to text string on python3
			# We first convert to a byte string so that we get rid of
			# characters that are invalid in the user's locale
			encoded_output = self._output_encoding(stderr=stderr)
			msg2 = to_text(msg2, encoded_output, errors='replace')

		self.log_storage.append(msg2)

	def get_logs(self):
		return self.log_storage


class LogCallBack(CallbackModule):

	def __init__(self, verbosity):
		super().__init__()
		self._display = Display(verbosity=verbosity)

		self.host_ok = []
		self.host_unreachable = []
		self.host_failed = []
		self.host_skipped = []

		self.display_ok_hosts = []
		self.display_unreachable_hosts = []
		self.display_failed_hosts = []
		self.display_skipped_hosts = []
		self.display_failed_stderr = []

	def get_logs(self):
		return self._display.get_logs()


class Driver:
	"""
	Python basic pyansible which executes ansible plays

	In order to use the drivers, a configuration should be provided
	during instantiation of the object. This configuration should contain:
		`ANSIBLE_REMOTE_USER` -> the user to use to connect the target host
		`ANSIBLE_PRIVATE_KEY_FILE` -> private key file if you use it to connect to the host
		`ANSIBLE_PLAYBOOKS_WORKING_DIR` -> the working directory which the playbooks are located
		`ANSIBLE_VAULT_PASSWORD` -> vault password if some files are encrypted via ansible
		`ANSIBLE_VERBOSITY` -> the verbosity level for execution logs. By default, the verbosity is 0
	"""

	logger_cb = None
	play_executor = None

	def __init__(self, config):
		self._remote_user = config['ANSIBLE_REMOTE_USER']
		self._private_key_file = config['ANSIBLE_PRIVATE_KEY_FILE']
		self._base_plays_path = config['ANSIBLE_PLAYBOOKS_WORKING_DIR']
		self._verbosity = config.get('ANSIBLE_VERBOSITY', 0)

		vault_password = config['ANSIBLE_VAULT_PASSWORD']
		password = to_bytes(vault_password)
		vault_secret = VaultSecret(_bytes=password)
		self._default_secret = [('default', vault_secret)]

	def run(self, playbook_path, host, extra_vars):
		full_playbook_path = f'{self._base_plays_path}/{playbook_path}'
		if not os.path.exists(full_playbook_path):
			error = f'the given playbook `{playbook_path}` does not exist ' \
				f'in the working dir `{self._base_plays_path}`'
			raise AnsiblePlaybookNotFoundError(error)

		self._prepare_for_run(
			host=host, extra_vars=extra_vars,
		    playbook=full_playbook_path)

		result_code = self.play_executor.run()
		# TODO : If you want: _status contains
		# the execution summary per host of playbook
		# stats= self.pbex._tqm._stats
		result_msg = self.convert_result_code(result_code)
		execution_logs = self.logger_cb.get_logs()

		return result_msg, '\n'.join(execution_logs)

	def _prepare_for_run(self, host, extra_vars, playbook):
		module_path = f'{self._base_plays_path}/modules'

		options = InventoryOptions(
			remote_user=self._remote_user,
			private_key_file=self._private_key_file,
			module_path=module_path)

		loader = DataLoader()
		loader.set_vault_secrets(self._default_secret)
		inventory = InventoryManager(loader=loader, sources=f'{host},')
		variable_manager = VariableManager(loader=loader, inventory=inventory)
		variable_manager.extra_vars = extra_vars

		self.play_executor = PlaybookExecutor(
			playbooks=[playbook],
			options=options,
			loader=loader,
			inventory=inventory,
			variable_manager=variable_manager,
			passwords={}
		)
		self.logger_cb = LogCallBack(self._verbosity)
		# TODO: make a PR to ansible core to allowing access to task queue
		# manager property in order to get all execution logs
		self.play_executor._tqm._stdout_callback = self.logger_cb

	@staticmethod
	def convert_result_code(status):
		status_map = {
			0: RUN_OK, 1: RUN_ERROR, 2: RUN_FAILED_HOSTS,
			4: RUN_UNREACHABLE_HOSTS, 8: RUN_FAILED_BREAK_PLAY,
			255: RUN_UNKNOWN_ERROR
		}
		return status_map.get(status, RUN_UNKNOWN_ERROR)
