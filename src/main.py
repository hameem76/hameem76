import json
import yaml
from copy import deepcopy
from typing import Any

from git import Repo
import os

class Services:
    LOAD_BALANCER = "lb"
    MQ = "message_queue"
    AWS_CLOUDTRAIL = "aws_cloudtrail"
    AWS_LAMBDA = "aws_lambda"
    CACHE = "cache"
    DATABASE = "database"
    DOCKER = "docker"
    APP_SERVER = "app_server"
    AWS_SERVICE = "aws_service"
    AWS_SQS = "aws_sqs"
    AWS_SNS = "aws_sns"
    AWS_RDS = "aws_rds"
    AWS_S3 = "aws_s3"
    STATIC_CONTENT= "static_content"


services_discovered : dict[str, Any]= {}

def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""

def parse_from_docker_file(file_content: str):
    services_discovered[Services.DOCKER] = {}
    for line in file_content.split("\n"):
        if 'CMD' in line:
            if 'npm' in line:
                services_discovered[Services.DOCKER][Services.APP_SERVER] = "Nodejs"
            elif 'flask' in line:
                services_discovered[Services.DOCKER][Services.APP_SERVER] = "Flask"
            elif 'django' in line:
                services_discovered[Services.DOCKER][Services.APP_SERVER] = 'Django'
            elif 'start-kafka' in line:
                services_discovered[Services.DOCKER][Services.MQ] = 'kafka'
            elif 'rabbitmq' in line:
                services_discovered[Services.DOCKER][Services.MQ] = 'rabbitmq'

    return


def parse_from_docker_compose(file_content: str):
    services_discovered[Services.DOCKER] = {}


def parse_from_nginx_conf(file_content: str):
    start = "upstream backend {"
    end = "}"
    server_entries = find_between(file_content, start, end)
    servers_count =0
    servers = []
    for entry in server_entries.split("\n"):
        if entry.strip().startswith("server"):
            servers_count += 1
            servers.append(entry.strip().split(" ")[1])
    services_discovered[Services.LOAD_BALANCER] = {"server_count": servers_count, "servers": servers}
    return

def parse_from_package_json(file_content: str):
    print(file_content)
    json_dict = json.loads(file_content)
    services_discovered[Services.APP_SERVER] = "node.js"
    dependencies = json_dict.get("dependencies")
    discovery_map = [
        {
            "search_service" : Services.DATABASE,
            "searchable_keywords": ["mysql", "mongodb", "postgres"]
        },
        {
            "search_service": Services.CACHE,
            "searchable_keywords": ["redis"]
        },
    ]

    if dependencies:
        for discovery_entry in discovery_map:
            search_service = discovery_entry['search_service']
            searchable_keywords = discovery_entry['searchable_keywords']
            discovered_entities = services_discovered.get(search_service, [])
            for key in dependencies.keys():
                for keyword in searchable_keywords:
                    if keyword in key:
                        discovered_entities.append(keyword)
            services_discovered[search_service] = discovered_entities
    return

def parse_from_requirements_txt(file_content: str):
    discovery_map = [
        {
            "search_service" : Services.DATABASE,
            "searchable_keywords": {"mysql": "mysqlclient" , "mongodb": "pymongo", "postgres" : "postgres"}
        },
        {
            "search_service": Services.CACHE,
            "searchable_keywords": {"redis": "redis"}
        },
    ]
    lib_entries = file_content.split("\n")
    for entry in lib_entries:
        for discovery_entry in discovery_map:
            search_service = discovery_entry['search_service']
            searchable_keywords = discovery_entry['searchable_keywords']
            discovered_entities = services_discovered.get(search_service, [])
            for key,val in searchable_keywords.items():
                if val in entry.split("==")[0]:
                    discovered_entities.append(key)
            services_discovered[search_service] = discovered_entities
    return

def parse_from_py_files(file_content: str):
    # Fetch from boto3 client access for AWS.
    # Similarly fetch for Azure services as well with appropriate key_words with respective cloud call
    boto3_services = {Services.AWS_S3: "s3", Services.AWS_SQS: "sqs", Services.AWS_SNS: "sns", Services.AWS_RDS: "rds",
                      Services.AWS_LAMBDA: "lambda", Services.AWS_CLOUDTRAIL: "cloudtrail"}
    for key, val in boto3_services.items():
        if f"boto3.client('{val}')" in file_content or f'boto3.client("{val}")' in file_content:
            services_discovered[key] = "enabled"

    return

def parse_from_js_files(file_content: str):
    return

# Clone a repository
def clone_repo(url, directory):
    if not os.path.exists(directory):
        Repo.clone_from(url, directory)
        print(f"Cloned repository to {directory}")
    else:
        print(f"Repository already exists at {directory}")

# List all files in the repository
def discover_services_in_repo(directory):
    #files = []
    services_discovered = {}
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            if filename == 'Dockerfile':
                file_content = read_file(file_path)
                parse_from_docker_file(file_content)
            elif filename.lower() == 'package.json':
                file_content = read_file(file_path)
                parse_from_package_json(file_content)
            elif filename.lower() == 'requirements.txt':
                file_content = read_file(file_path)
                parse_from_requirements_txt(file_content)
            elif filename.endswith(".py"):
                file_content = read_file(file_path)
                parse_from_py_files(file_content)
            elif filename == 'load-balancer.conf':
                file_content = read_file(file_path)
                parse_from_nginx_conf(file_content)
            services_discovered[Services.STATIC_CONTENT] = "enabled"

            #files.append(file_path)
    return services_discovered

# Read the content of a file
def read_file(filepath):
    with open(filepath, 'r') as file:
        content = file.read()
    return content


def build_aws_architecture(customerA_services, customerB_services) -> str:
    architecture_content_dict = {
        "Diagram": {
            "DefinitionFiles":[{
                "Type": "URL",
                "Url": "https://raw.githubusercontent.com/awslabs/diagram-as-code/main/definitions/definition-for-aws-icons-light.yaml"
            }],
            "Resources": {
            "Canvas": {
                "Type": "AWS::Diagram::Canvas",
                "Direction": "Vertical",
                "Preset" : "AWSCloudNoLogo",
                "Children": [
                    "AWSCloud"
                ]
            }
    }}}

    for customer, _services_discovered in {"CustomerA": customerA_services, "CustomerB": customerB_services}.items():
        aws_cloud = {"Type":"AWS::Diagram::Cloud", "Children": []}
        vpc = {
            "Type": "AWS::VPC",
            "Children": []
        }
        aws_cloud["Children"].append(customer)
        architecture_content_dict["Diagram"]["Resources"][customer] = vpc
        architecture_content_dict["Diagram"]["Resources"]["AWSCloud"] = aws_cloud
        if _services_discovered.get(Services.STATIC_CONTENT) == "enabled":
            cloud_front = {
                "Type": "AWS::CloudFront"
            }
            architecture_content_dict["Diagram"]["Resources"]["AWSCloudFront"] = cloud_front
            aws_cloud["Children"].append("AWSCloudFront")

        if _services_discovered.get(Services.DOCKER):
            ec2 = {
                "Type" : "AWS::EC2::Instance"
            }
            architecture_content_dict["Diagram"]["Resources"]["EC2_1"] = ec2
            vpc["Children"].append("EC2_1")

        # if services_discovered.get(Services.DOCKER):
        #     ec2 = {
        #         "Type" : "AWS::EC2::Instance"
        #     }
        #     architecture_content_dict["Diagram"]["Resources"]["EC2_1"] = ec2

        if _services_discovered.get(Services.AWS_SQS):
            sqs = {
                "Type": "AWS::SQS"
            }
            architecture_content_dict["Diagram"]["Resources"]["SQS"] = sqs
            aws_cloud["Children"].append("SQS")


        if _services_discovered.get(Services.AWS_SNS):
            sns = {
                "Type": "AWS::SNS"
            }
            architecture_content_dict["Diagram"]["Resources"]["SNS"] = sns
            aws_cloud["Children"].append("SNS")

        if _services_discovered.get(Services.AWS_S3):
            s3 = {
                "Type": "AWS::S3"
            }
            architecture_content_dict["Diagram"]["Resources"]["S3"] = s3
            aws_cloud["Children"].append("SNS")

    print(architecture_content_dict)
    return yaml.dump(architecture_content_dict)


if __name__ == '__main__':

    # Example usage
    # repo_url = 'https://github.com/hameem76/hameem76.git'  # Replace with your repository URL0
    repo_directory = '/home/hameem/git_repos/hameem76/test_repos/customerA'  # Replace with the desired directory
    #clone_repo(repo_url, repo_directory)
    customerA = deepcopy(discover_services_in_repo(repo_directory))
    repo_directory = '/home/hameem/git_repos/hameem76/test_repos/customerB'  # Replace with the desired directory
    #clone_repo(repo_url, repo_directory)
    customerB = deepcopy(discover_services_in_repo(repo_directory))
    #print("discovery", services_discovered)
    #print(customerA)
    architecture_content = build_aws_architecture(customerA, customerB)
    print("architecture \n", architecture_content)
    # print("Files in repository:")
    # for file in files:
    #     print(file)

