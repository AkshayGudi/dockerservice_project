from ..models import build, push
from django.db import transaction
import docker
import os


namespace = str(os.environ.get('DOCKERHUB_NAMESPACE')).strip()
registry_username = str(os.environ.get('DOCKERHUB_USERNAME')).strip()
registry_password = str(os.environ.get('DOCKERHUB_PASSWORD')).strip()



registry_url = "https://index.docker.io/v2/"
auth_config = {
            'username': registry_username,
            'password': registry_password
        }    


import logging

logger = logging.getLogger(__name__)

def docker_build_push(build_id, push_id):

    print(f"Started task {build_id}")

    logger.info(f"Started task {build_id}")

    build_status = docker_build(build_id, push_id)

    if build_status:
        docker_push(push_id)
        print(f"Completed task -- {build_id}")
        logger.info(f"Completed task -- {build_id}")

    else:
        print(f"Failed task -- {build_id}")
        logger.error(f"Failed task -- {build_id}")

def docker_build(build_id, push_id):
    print(f"Build started for build_id {build_id} ...")
    logger.info(f"Build started for build_id {build_id} ...")

    build_obj = update_build_status(build_id, build.ProcessStatus.IN_PROGRESS)

    image_name_tag = build_obj.image_name + ":" + build_obj.image_tag
    dockerfile_name = build_obj.file_name
    dockerfile_dir = build_obj.file_loc

    try:
        client = docker.from_env()

        # Build the Docker image
        client.images.build(path=dockerfile_dir, dockerfile=dockerfile_name, tag=namespace + "/" + image_name_tag)

    except Exception as e:

        print(f"Build failed for build id {build_id} ...")
        logger.error(f"Build failed for build id {build_id} ...")
        print(f"An error occurred: {e}")
        update_build_status(build_id, build.ProcessStatus.FAILED, reason="Error while building the image")
        update_push_status(push_id, push.ProcessStatus.FAILED, reason="Error while building the image")
        return False

    update_build_status(build_id, build.ProcessStatus.COMPLETED)
    print(f"Build completed for build id {build_id}")
    logger.info(f"Build completed for build id {build_id}")

    return True


def docker_push(push_id):
    print(f"Push started for push id {push_id} ...")
    logger.info(f"Push started for push id {push_id} ...")

    print("User name ==========================================")
    print(registry_username)

    print("Password ===========================================")
    print(registry_password)

    push_obj:push = update_push_status(push_id, push.ProcessStatus.IN_PROGRESS)
    
    image_name_tag = push_obj.image_name + ":" + push_obj.image_tag
    
    final_repository_name = namespace + "/" + image_name_tag

    try:
        client = docker.from_env()
        credential_map = client.login(username=registry_username, password=registry_password, registry=registry_url)

    except Exception as e:
        logger.error("Error while logging into docker hub")
        print(f"An error occurred: {e}")
        update_push_status(push_id, push.ProcessStatus.FAILED, reason="Failed to Login")
        return False

    try:
        for line in client.images.push(repository=final_repository_name, stream=True, auth_config=auth_config, decode=True):
            print(line)

        print(f"Image {image_name_tag} successfully pushed to {registry_url}")
        logger.info(f"Image {image_name_tag} successfully pushed to {registry_url}")

    except Exception as e:
        logger.error("Error occurred while pushing docker image to dockerhub")
        print(f"An error occurred: {e}")
        update_push_status(push_id, push.ProcessStatus.FAILED, reason="Failed to Push the image")
        return False

    update_push_status(push_id, push.ProcessStatus.COMPLETED)
    print(f"Push completed for build id {push_id}")
    logger.info(f"Push completed for build id {push_id}")

    return True

@transaction.atomic
def update_build_status(build_id, status, reason=""):
    build_obj = build.objects.get(build_id=build_id)
    build_obj.status = status
    build_obj.failed_reason = reason
    build_obj.save()
    return build_obj

@transaction.atomic
def update_push_status(push_id, status, reason=""):
    push_obj = push.objects.get(push_id=push_id)
    push_obj.status = status
    push_obj.failed_reason = reason
    push_obj.save()
    return push_obj