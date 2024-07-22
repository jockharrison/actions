import subprocess
import sys
import boto3
import time
from kubernetes import client, config, utils
from kubernetes.client.rest import ApiException

# Stream output to GH action
def run_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    print(f"Command: {command}")
    print(f"Output:\n{stdout.decode('utf-8')}", flush=True)
    if stderr:
        print(f"Error:\n{stderr.decode('utf-8')}", flush=True)

# Get credentials from AWS secret manager
def get_user_token():
    print("Getting username and token from AWS Secrets Manager.", flush=True)

    secret_name = "cse-space-artifactory-test-user"
    global artifactory_user
    global artifactory_token

    session = boto3.Session()
    client = session.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_name)
    secret = response.get('SecretString')
    secret_values = eval(secret)

    artifactory_user = secret_values["user"]
    artifactory_token = secret_values["token"]

    print("DONE", flush=True)

def docker_login_and_pull(repository_host, port, docker_path, docker_image):
    print(f"***  Docker login initiated in {repository_host}:{port} for repo {docker_path}. *** \n", flush=True)
    login_exit_code = subprocess.call(['docker', 'login', '-u', "admin", f'https://{repository_host}:{port}'])
    if login_exit_code != 0:
        print(f"*** An error occurred with docker login. ***\n", flush=True)
        return

    print(f"*** Docker pull initiated from repo {docker_path}. ***\n", flush=True)
    pull_exit_code = subprocess.call(['docker', 'pull', f'{repository_host}:{port}/{docker_image}'])
    if pull_exit_code != 0:
        print(f"*** An error occurred while pulling the docker image. ***\n", flush=True)
        return

    # print("\n*** Running the docker image, to test it works. ***", flush=True)
    # run_exit_code = subprocess.call(['docker', 'run', '-d', f'{repository_host}:{port}/{docker_image}'])
    # if run_exit_code != 0:
    #     print(f"*** An error occurred while running the new container. ***\n", flush=True)
    # else:
    #     print(f"*** Docker container based on: {docker_image} is running successfully. ***\n", flush=True)

def wait_for_pod(api_instance, namespace, pod_name, timeout_seconds=120):
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        pod = api_instance.read_namespaced_pod_status(name=pod_name, namespace=namespace)
        if pod.status.phase == 'Running':
            print(f"Pod '{pod_name}' is running.", flush=True)
            return
        time.sleep(5)
    print(f"Timed out waiting for pod '{pod_name}' to be running.", flush=True)

def kubernetes_operations(docker_image, pod_name):
    try:
        # Load kubeconfig
        config.load_kube_config()
        api_instance = client.CoreV1Api()
        namespace = "cse-test-pod"

        # Create namespace
        namespaces = api_instance.list_namespace()
        namespace_exists = any(ns.metadata.name == namespace for ns in namespaces.items)
        if namespace_exists:
            print(f"Namespace '{namespace}' exists, Skip creation")
        else:
            print(f"Creating namespace: {namespace}", flush=True)
            namespace_body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
            api_instance.create_namespace(body=namespace_body)
            print(f"Namespace '{namespace}' created.", flush=True)



        # Create pod
        print(f"Creating pod with image: {docker_image}", flush=True)
        pod_body = client.V1Pod(
            api_version="v1",
            kind="Pod",
            metadata=client.V1ObjectMeta(name=pod_name),
            spec=client.V1PodSpec(containers=[
                client.V1Container(
                    name=pod_name,
                    image=docker_image,
                    ports=[client.V1ContainerPort(container_port=80)]
                )
            ])
        )
        api_instance.create_namespaced_pod(namespace=namespace, body=pod_body)
        print(f"Pod '{pod_name}' created in namespace '{namespace}'.", flush=True)

        # Wait for pod to be running

        if not wait_for_pod(api_instance, namespace, pod_name):
            # Clean up before exiting with error
            print(f"Deleting pod '{pod_name}' in namespace '{namespace}' due to timeout.", flush=True)
            api_instance.delete_namespaced_pod(name=pod_name, namespace=namespace)
            print(f"Pod '{pod_name}' deleted.", flush=True)

            print(f"Deleting namespace '{namespace}' due to timeout.", flush=True)
            api_instance.delete_namespace(name=namespace)
            print(f"Namespace '{namespace}' deleted.", flush=True)
            sys.exit(1)       
            
        #wait_for_pod(api_instance, namespace, pod_name)
        # start_time = time.time()
        # timeout_seconds = 120
        # while time.time() - start_time < timeout_seconds:
        #     pod = api_instance.read_namespaced_pod_status(name=pod_name, namespace=namespace)
        #     if pod.status.phase == 'Running':
        #         print(f"Pod '{pod_name}' is running.", flush=True)
        #         return
        # print(f"Timed out waiting for pod '{pod_name}' to be running.", flush=True)
    
        #utils.wait_for_condition(api_instance, namespace, pod_name, lambda pod: pod.status.phase == 'Running', timeout_seconds=120)
        print(f"Pod '{pod_name}' is running.", flush=True)

        # Clean up
        print(f"Deleting pod '{pod_name}' in namespace '{namespace}'.", flush=True)
        api_instance.delete_namespaced_pod(name=pod_name, namespace=namespace)
        print(f"Pod '{pod_name}' deleted.", flush=True)

        print(f"Deleting namespace '{namespace}'.", flush=True)
        api_instance.delete_namespace(name=namespace)
        print(f"Namespace '{namespace}' deleted.", flush=True)

    except ApiException as e:
        print(f"Exception when performing Kubernetes operations: {e}", flush=True)

def main():
    if len(sys.argv) < 6:
        print("Usage: python3 dockerDeployTest.py [us-east-1|us-west-2|eu-west-1] [infnonprod|infprod] [repository_host] [docker_path] [docker_image]", flush=True)
        exit(1)

    region = sys.argv[1]
    environment = sys.argv[2]
    repository_host = sys.argv[3]
    docker_path = sys.argv[4]
    docker_image = sys.argv[5]
    port = 5000
    docker_name = docker_image.split(':')
    pod_name = docker_name[0]
    #get_user_token()
    docker_login_and_pull(repository_host, port, docker_path, docker_image)
    kubernetes_operations(docker_image, pod_name)

if __name__ == "__main__":
    main()
