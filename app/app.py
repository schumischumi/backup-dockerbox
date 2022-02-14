import tempfile
import shutil
import logging
import sys
import requests
from config import settings
import json
import re
import datetime
import sysrsync
import os

### Backup: Initialize stage
## Initialize: Logger
logger = logging.getLogger()
streamHandler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
level = logging.getLevelName(settings.LOGLEVEL)
logger.setLevel(level)

## Initialize: Set Variables
PORTAINER_EXPORT_PW = settings.PORTAINER_EXPORT_PW
PORTAINER_URL = settings.PORTAINER_URL
PORTAINER_ACCESSKEY = settings.PORTAINER_ACCESSKEY

print(PORTAINER_ACCESSKEY)
## Initialize: Portainer Request
# Initialize: set authentication header
headers = {
    'X-API-Key': PORTAINER_ACCESSKEY
}

# Initialize: remove tailing slash from url
print('PORTAINER_URL:',PORTAINER_URL)
if PORTAINER_URL.endswith('/'):
    PORTAINER_URL = PORTAINER_URL[:-1]

## Initialize: set directories
backup_dir_yaml = tempfile.mkdtemp(prefix="stack_yaml_")
backup_dir_yaml_sub = backup_dir_yaml + '/portainer_yaml/'
os.mkdir(backup_dir_yaml_sub)
logger.debug('backup_dir_yaml_sub: ' + backup_dir_yaml_sub)
backup_dir_portainer = tempfile.mkdtemp(prefix="portainer_config_")
backup_dir_portainer_sub = backup_dir_portainer + '/portainer_config/'
os.mkdir(backup_dir_portainer_sub)

logger.debug('backup_dir_portainer_sub: ' + backup_dir_portainer_sub)

## Initialize: rsync config
current_date = datetime.date.today()
week_number = int(current_date.isocalendar()[1])
month_number =int(current_date.strftime("%m"))

if week_number % 4 == 0:
    backup_remote_folder = "month_" + str(month_number % 2)
else:
    backup_remote_folder = "week_" + str(week_number % 2)

#rsync_source = settings.PORTAINER_VOLUME_MOUNT
rsync_destination = settings.BACKUP_REMOTE_DIR + backup_remote_folder #+ '/'
rsync_server = settings.BACKUP_HOST
rsync_user = settings.BACKUP_USERNAME
rsync_options = settings.RSYNC_OPTIONS

logger.info("Portainer Backup: Starting")
### Backup
## Backup Portainer Config
logger.info("Portainer Config: Start Backup")
logger.info("Portainer Config: Start Export")
payload = json.dumps({
  "password": settings.PORTAINER_EXPORT_PW
})
request_url = PORTAINER_URL + '/api/backup'
response = requests.request("POST", request_url, headers=headers, data=payload)
if response.status_code != 200:
    logger.error('Call ' + request_url + ' with non 200 status code: ' + str(response.status_code))
    exit()

portainer_config_filename = re.findall("filename=(.+)", response.headers['content-disposition'])[0]
portainer_config_file = open(backup_dir_portainer_sub + portainer_config_filename, "wb")
portainer_config_file.write(response.content)
portainer_config_file.close()
logger.info("Portainer Config: Finished Export")
logger.info("Portainer Config: Start Rsync Transfer")
try: 
    rsync_source = backup_dir_portainer
    logger.debug(rsync_destination)
    sysrsync.run(source=rsync_source,
                destination=rsync_destination,
                destination_ssh=rsync_user+'@'+rsync_server,
                options=[rsync_options])
except Exception as e:
    logger.error('Exception when using rsync: ' + str(e))
    exit()
logger.info("Portainer Config: Finished Rsync Transfer")
logger.info("Portainer Config: Finished Backup")

## Export stack yamls
logger.info("Portainer YAMLs: Start Backup")
logger.info("Portainer YAMLs: Start Export")
payload={}
request_url = PORTAINER_URL + '/api/stacks'
response = requests.request(
                                "GET", 
                                request_url, 
                                headers=headers, 
                                data=payload)
if response.status_code != 200:
    logger.error('Call ' + request_url+ ' with non 200 status code: ' + str(response.status_code))
    exit()
api_response_stack_list  = response.json()

stack_id_list  = []
for api_response_stack in api_response_stack_list:
    try:
        logger.info("Portainer YAMLs: Export" + api_response_stack['Name'])
        request_url = PORTAINER_URL + '/api/stacks/' + str(api_response_stack['Id']) + '/file'
        response = requests.request(
                                "GET", 
                                request_url, 
                                headers=headers, 
                                data=payload)
        if response.status_code != 200:
            logger.error('Call ' + request_url+ ' with non 200 status code: ' + str(response.status_code))
            exit()
        api_response_stack_file = response.json()
        
    except Exception as e:
        logger.error('Exception when calling StacksApi->stack_file_inspect',str(e))
        exit()
    try:
        stack_filename = backup_dir_yaml_sub + api_response_stack['Name'] + ".yaml"
        with open(stack_filename, "w") as stack_file:
            stack_file.write(api_response_stack_file['StackFileContent'])
            stack_file.close()
    except Exception as e:
        logger.error('Exception when saving yaml files: ' + str(e))
        exit()
    
    stack_id_list.append({  'stack_id':api_response_stack['Id'], 
                            'stack_name':api_response_stack['Name'], 
                            'stack_status':api_response_stack['Status']
                        })
logger.info("Portainer YAMLs: Finished Export")

logger.info("Portainer YAMLs: Start Rsync Transfer")
try: 
    rsync_source = backup_dir_yaml
    logger.debug(rsync_destination)
    sysrsync.run(source=rsync_source,
                destination=rsync_destination ,
                destination_ssh=rsync_user+'@'+rsync_server,
                options=[rsync_options])
except Exception as e:
    logger.error('Exception when using rsync: ' + str(e))
    exit()
logger.info("Portainer YAMLs: Finished Rsync Transfer")
logger.info("Portainer YAMLs: Finished Backup")

## Backup: Volume Mouts
logger.info("Portainer Volumes: Start Backup")
logger.info("Portainer Volumes: Start Export & Rsync Transfer")
if settings.BACKUP_STACK_EXCLUDE != '':
    stack_exclude = settings.BACKUP_STACK_EXCLUDE.lower().replace(' ','').split(',')
else:
    stack_exclude = []
for stack_id_item in stack_id_list:
    rsync_source = os.path.join(settings.PORTAINER_VOLUME_MOUNT,'.',stack_id_item['stack_name'])
    if os.path.exists(rsync_source) and stack_exclude.count(stack_id_item['stack_name'].lower()) == 0:
        logger.info("Portainer Volumes: Start Export" + stack_id_item['stack_name'])
        if stack_id_item['stack_status'] == 1:
            try:
                request_url = PORTAINER_URL + '/api/stacks/' + str(stack_id_item['stack_id']) + '/stop'
                response = requests.request(
                                        "POST", 
                                        request_url, 
                                        headers=headers)
                if response.status_code != 200:
                    logger.error('Call ' + request_url+ ' with non 200 status code: ' + str(response.status_code))
                    exit()            
            except Exception as e:
                logger.error('Exception when calling StacksApi->stack_stop with stack "' + stack_id_item['stack_name'] + '": ' + str(e))
                exit()
        logger.info("Portainer Volumes: Finished Export" + stack_id_item['stack_name'])

        logger.info("Portainer Volumes: Start Rsync Transfer" + stack_id_item['stack_name'])
        try:            
            logger.debug(rsync_destination)
            logger.debug(rsync_source)
            logger.debug(rsync_options)
            sysrsync.run(source=rsync_source,
                        destination=rsync_destination ,
                        destination_ssh=rsync_user+'@'+rsync_server,
                        options=[rsync_options+'R'])
        except Exception as e:
            logger.error('Exception when using rsync: ' + str(e))
            exit()
        logger.info("Portainer Volumes: Finished Rsync Transfer" + stack_id_item['stack_name'])
        if stack_id_item['stack_status'] == 1:
            try:
                request_url = PORTAINER_URL + '/api/stacks/' + str(stack_id_item['stack_id']) + '/start'
                response = requests.request(
                                        "POST", 
                                        request_url, 
                                        headers=headers)
                if response.status_code != 200:
                    logger.error('Call ' + request_url+ ' with non 200 status code: ' + str(response.status_code))
                    exit()            
            except Exception as e:
                logger.error('Exception when calling StacksApi->stack_start with stack "' + stack_id_item['stack_name'] + '": ' + str(e))
                exit()

logger.info("Portainer Volumes: Finished Export & Rsync Transfer")

### cleanup
logger.info("Cleanup: Start")

## Cleanup directories
logger.info("Cleanup: Removing directories")
shutil.rmtree(backup_dir_yaml)
shutil.rmtree(backup_dir_portainer)

logger.info("Cleanup: Finished")

logger.info("Portainer Backup: Finished")