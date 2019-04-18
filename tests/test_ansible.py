import getpass

import os

import pytest

from driver.ansible import Driver as AnsibleDriver
from driver.ansible import AnsiblePlaybookNotFoundError


class TestDriver:
    def setup(self):
        self.remote_user = getpass.getuser()
        self.private_key_file = ''
        chdir = os.getcwd()
        self.working_dir = f'{chdir}/tests'
        self.verbosity = 0
        self.vault_password = ''
        self.config = {
            'ANSIBLE_REMOTE_USER': self.remote_user,
            'ANSIBLE_PRIVATE_KEY_FILE': self.private_key_file,
            'ANSIBLE_PLAYBOOKS_WORKING_DIR': self.working_dir,
            'ANSIBLE_VERBOSITY': self.verbosity,
            'ANSIBLE_VAULT_PASSWORD': self.vault_password,
        }
        self.driver = AnsibleDriver(config=self.config)

    def test_should_raise_when_playbooks_does_not_exist(self):
        # Given
        playbook_path = 'not-existing-playbook.yml'
        host = 'foo-host'
        extra_vars = {'key': 'value', 'number': 1}

        # When
        with pytest.raises(AnsiblePlaybookNotFoundError) as error:
            self.driver.run(playbook_path, host, extra_vars)

        # Then
        error_message = f'the given playbook `{playbook_path}` does not ' \
            f'exist in the working dir `{self.working_dir}`'
        assert error.value.args[0] == error_message

    def test_returns_success_after_execution_ok(self):
        # Given
        playbook_path = 'test-playbook.yml'
        host = 'localhost'
        extra_vars = {'host': host, 'chdir': self.working_dir}

        # When
        result = self.driver.run(playbook_path, host, extra_vars)

        # Then
        assert result[0] == 'RUN_OK'
        assert result[1] == 'RUN_OK'

    def test_returns_failed_after_execution_due_to_dir_not_exist(self):
        # Given
        playbook_path = 'test-playbook.yml'
        host = 'localhost'
        extra_vars = {'host': host, 'chdir': f'{self.working_dir}/unknown-dir'}

        # When
        result = self.driver.run(playbook_path, host, extra_vars)

        # Then
        assert result[0] == 'RUN_FAILED_HOSTS'
        assert result[1] is not None

    def test_returns_unreachable_when_host_not_know(self):
        # Given
        playbook_path = 'test-playbook.yml'
        host = 'unknown-host'
        extra_vars = {'host': host, 'chdir': self.working_dir}

        # when
        result = self.driver.run(playbook_path, host, extra_vars)

        # Then
        assert result[0] == 'RUN_UNREACHABLE_HOSTS'
        assert result[1] is not None
