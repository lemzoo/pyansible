# Basic Ansible driver to allow running ansible playbooks in python

This python driver provide a simple python implementation which allow to run
ansible playbooks in python. It's just a simple driver based on Python Ansible
API to allow developer to run directly ansible through python application. 

In my case, I have a python application based in flask (endpoints) and celery 
for asynchronous tasks. I also use Ansible Tower to run playbooks. And the 
execution of the playbook is monitored by celery worker to update the 
database basing in the status of the executed playbook. 

After few months, I found the workflow of the application more complicated due 
to the dependency. So, I decided to execute directly the playbook inside
celery worker trough tasks.

Getting started:
===============

First create a playbook with this name and this content:

filename: my-playbook.yml and below the content of the playbook

```
    ---
    - hosts: all
    - gather_fact: no
    
      tasks:    
        - debug: msg="key=`{{ key }}` and number=`{{ value }}`"
    ...

```


```
    >>> configuration = {
            'ANSIBLE_REMOTE_USER': 'my-remote-user',
            'ANSIBLE_PRIVATE_KEY_FILE': 'path-of-my-private-key-file',
            'ANSIBLE_PLAYBOOKS_WORKING_DIR': 'path-where-playbooks-located',
            'ANSIBLE_VERBOSITY': 0,
            'ANSIBLE_VAULT_PASSWORD': 'my-vaul-password-to-devault-files',
        }
        
    >>> from ansible_driver import Driver as AnsibleDriver
    >>> driver = AnsibleDriver(config=configuration)
    >>> playbook = 'my-playbook.yml'
    >>> host = 'remote-server'
    >>> extra_vars = {'key': 'value', 'number': 1}
    >>> result = driver.run(playbook_path, host, extra_vars)
    >>> assert result[0] == 0 # This is the result code
    >>> assert result[1] == 'RUN_OK' # additional info
    
```
