import os

class Settings():

    env_list  = [
        {'name':'PORTAINER_ACCESSKEY', 'mandatory': True, 'default':''},
        {'name':'PORTAINER_URL', 'mandatory': True, 'default':''},
        {'name':'BACKUP_USERNAME', 'mandatory': True, 'default':''},
        {'name':'BACKUP_HOST', 'mandatory': True, 'default':''},
        {'name':'PORTAINER_VOLUME_MOUNT', 'mandatory': True, 'default':''},
        {'name':'BACKUP_REMOTE_DIR', 'mandatory': True, 'default':''},
        {'name':'LOGLEVEL', 'mandatory': False, 'default':'INFO'},
        {'name':'BACKUP_STACK_EXCLUDE', 'mandatory': False, 'default':''},
        {'name':'RSYNC_OPTIONS', 'mandatory': False, 'default':'-avzP'},
        {'name':'PORTAINER_EXPORT_PW', 'mandatory': False, 'default':''}
    ]
    for env_item in env_list:
        if os.environ.get(env_item['name']) is None and env_item['mandatory'] == True:
            print("The enviroment variable '" + env_item['name'] + "' must be set. Aborting")
            exit()
        elif os.environ.get(env_item['name']) is None and not env_item['mandatory']:
            vars()[env_item['name']] = env_item['default']
        else:
            vars()[env_item['name']] = os.environ[env_item['name']]

settings = Settings() 
