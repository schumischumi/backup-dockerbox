import portainer_ce_api
import subprocess
import sysrsync
from portainer_ce_api.rest import ApiException
import os
import requests
import datetime
import sys

# https://gist.github.com/deviantony/77026d402366b4b43fa5918d41bc42f8


# function
# exit and mail status
def exit_and_report(exit_code: int,msg:str,error_msg:str=""):
    print(msg)
    print(error_msg)
    exit(exit_code)

# vars
if len(sys.argv) >= 1:
    backup_mode = sys.argv[0]
else:
    exit_and_report(1,'backup mode ("month" or "week") not set')
current_date = datetime.date.today()
week_number = int(current_date.isocalendar()[1])
month_number =int(current_date.strftime("%m"))

if backup_mode == 'month':
    backup_num_mod = str(month_number % 2)
elif backup_mode == 'week':
    backup_num_mod = str(week_number % 2)

backup_path_yaml = "./src/yaml/"
protainer_url = "http://portainer.dockerbox.local/api"
rsync_source = '/storage/*'
rsync_destination = '/volume1/Backup/dockerbox/storage/'+backup_mode+'_'+backup_num_mod+'/'
rsync_server = '192.168.1.162'
rsync_user = 'root'

# checks
# - test if key exists
if 'PORTAINER_API_KEY' in os.environ:
    portainer_apikey = os.environ['PORTAINER_API_KEY']
else:
    exit_and_report(1,'portainer api key not found')

# - test if url reachable
try:
    #Get Url
    url_verify_call = requests.get(protainer_url)
    # if the request succeeds 
    if url_verify_call.status_code != 200:
        exit_and_report(1,'portainer is Not reachable, status code:'+str(url_verify_call.status_code),str(url_verify_call.text))
	#Exception
except requests.exceptions.RequestException as e:
    exit_and_report(1,'portainer is Not reachable',str(e))
# - test if ssh key available and valid


# Configure API key authorization: jwt
portainer_config = portainer_ce_api.Configuration()
portainer_config.api_key['Authorization'] = portainer_apikey
portainer_config.host = protainer_url
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['Authorization'] = 'Bearer'

# create an instance of the API class
portainer_session = portainer_ce_api.StacksApi(portainer_ce_api.ApiClient(portainer_config))
#filters = 'filters_example' # str | Filters to process on the stack list. Encoded as JSON (a map[string]string). For example, { (optional)
filters=''

try:
    # List stacks
    api_response_stack_list = portainer_session.stack_list(filters=filters)
except ApiException as e:
    exit_and_report(1,'Exception when calling StacksApi->stack_list',str(e))

i = 0
stack_id_online_list  = []
# replace with for each
while i < len(api_response_stack_list):
    stack_id = api_response_stack_list[i].id
    stack_name = api_response_stack_list[i].name
    stack_status = api_response_stack_list[i].status
    try:
        # Retrieve the content of the Stack file for the specified stack
        api_response_stack_file = portainer_session.stack_file_inspect(stack_id)
    except ApiException as e:
        exit_and_report(1,'Exception when calling StacksApi->stack_file_inspect',str(e))
    stack_filename = backup_path_yaml + stack_name + ".yaml"
    try:
        with open(stack_filename, "w") as stack_file:
            stack_file.write(api_response_stack_file.stack_file_content)
            stack_file.close()
    except Exception as e:
        exit_and_report(1,'Exception when saving yaml files',str(e))

    if stack_status == 1:

        # write id to list for start
        stack_id_online_list.append(stack_id)
        try:
            # Stops a stopped Stack
            api_response_stack_stop = portainer_session.stack_stop(stack_id)
        except ApiException as e:
            exit_and_report(1,'Exception when calling StacksApi->stack_stop',str(e))
    i += 1

docker_session = docker.DockerClient(base_url='unix://var/run/docker.sock')
portainer_service_id = docker_session.services.list(filters={'name':'portainer_portainer'})[0].id
portainer_service = docker_session.services.get(portainer_service_id)
portainer_service.scale(0)
docker_session.containers.run(image='ubuntu', command='tar cvf /backup/backup.tar /data', volumes={'/storage/portainer/':{'bind': '/backup', 'mode': 'rw'},'portainer_portainer_data':{'bind': '/data', 'mode': 'ro'},},remove=True)
portainer_service_id = docker_session.services.list(filters={'name':'portainer_portainer'})[0].id
portainer_service = docker_session.services.get(portainer_service_id)
portainer_service.scale(1)

try: 
    sysrsync.run(source=rsync_source,
                destination=rsync_destination,
                destination_ssh=rsync_user+'@'+rsync_server,
                options=['-avzP'])
except Exception as e:
        exit_and_report(1,'Exception when using rsync',str(e))


# replace with for each
for stack_id in stack_id_online_list:

        try:
            # Stops a stopped Stack
            api_response_stack_start = portainer_session.stack_start(stack_id)
        except ApiException as e:
            exit_and_report(1,'Exception when calling StacksApi->stack_start',str(e))


# sysrsync.run(source='/storage/*',
#              destination='/volume1/Backup/dockerbox/storage/month/',
#              destination_ssh='root@192.168.1.162',
#              options=['-avzP'])
# runs 'rsync -a /home/users/files/ myserver:/home/server/files'

#print(s1)
#json.load(s1)

# id = 44 # int | Stack identifier

# try:
#     # Inspect a stack
#     api_response = portainer_session.stack_inspect(id)
#     print(api_response)
# except ApiException as e:
#     print("Exception when calling StacksApi->stack_inspect: %s\n" % e)

# try:
#     # Retrieve the content of the Stack file for the specified stack
#     api_response = portainer_session.stack_file_inspect(id)
#     print(api_response)
# except ApiException as e:
#     print("Exception when calling StacksApi->stack_file_inspect: %s\n" % e)

# id = 56 # int | Stack identifier

# try:
#     # Stops a stopped Stack
#     api_response = portainer_session.stack_stop(id)
#     print(api_response)
# except ApiException as e:
#     print("Exception when calling StacksApi->stack_stop: %s\n" % e)

# try:
#     # Starts a stopped Stack
#     api_response = portainer_session.stack_start(id)
#     pprint(api_response)
# except ApiException as e:
#     print("Exception when calling StacksApi->stack_start: %s\n" % e)
# docker service scale portainer=0
# docker run --rm --volumes-from portainer -v $(pwd):/backup ubuntu tar cvf /backup/backup.tar /data
