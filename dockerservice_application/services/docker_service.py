from ..models import build, push
from django.db import transaction
import docker
import os
import traceback
import shutil

if os.environ.get('DOCKERHUB_NAMESPACE') is None:
    namespace = None
else:
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
    """
    Orchestrates the build and push process for a Docker image.

    This function initiates the Docker build process, checks the build status, and proceeds with the push if the build is successful.
    It logs relevant information and updates the status of the build and push in the database.

    Parameters:
    - build_id: Unique identifier for the build process.
    - push_id: Unique identifier for the push process.
    """
    print(f"Started task {build_id}")

    logger.info(f"Started task {build_id}")

    build_status, docker_image_tag, dockerfile_dir = docker_build(build_id, push_id)

    if build_status:
        push_status = docker_push(push_id)

        if push_status:
            remove_task_metadata(docker_image_tag, dockerfile_dir)
            print(f"Completed task -- {build_id}")
            logger.info(f"Completed task -- {build_id}")
        else:
            print(f"Failed task -- {build_id}")
            logger.error(f"Failed task -- {build_id}")


    else:
        print(f"Failed task -- {build_id}")
        logger.error(f"Failed task -- {build_id}")

def docker_build(build_id, push_id):
    """
    Initiates the Docker build process for a given build_id and push_id.

    This function updates the build status in the database, performs the Docker build, and updates the status accordingly.

    Parameters:
    - build_id: Unique identifier for the build process.
    - push_id: Unique identifier for the push process.

    Returns:
    - Tuple: A tuple containing a boolean indicating the build status, the Docker image repository name, and the Dockerfile directory.
    """    
    print(f"Build started for build_id {build_id} ...")
    logger.info(f"Build started for build_id {build_id} ...")

    build_obj = update_build_status(build_id, build.ProcessStatus.IN_PROGRESS)

    image_name_tag = build_obj.image_name + ":" + build_obj.image_tag
    dockerfile_name = build_obj.file_name
    dockerfile_dir = build_obj.file_loc
    if namespace is None:
        repository_name = image_name_tag
    else:
        repository_name = namespace + "/" + image_name_tag

    try:
        client = docker.from_env()

        # Build the Docker image
        client.images.build(path=dockerfile_dir, dockerfile=dockerfile_name, tag=repository_name)

    except Exception as e:
        traceback.print_exc()
        print(f"Build failed for build id {build_id} ...")
        logger.error(f"Build failed for build id {build_id} ...")
        print(f"An error occurred: {e}")
        update_build_status(build_id, build.ProcessStatus.FAILED, reason="Error while building the image")
        update_push_status(push_id, push.ProcessStatus.FAILED, reason="Error while building the image")
        return False, repository_name, dockerfile_dir

    update_build_status(build_id, build.ProcessStatus.COMPLETED)
    print(f"Build completed for build id {build_id}")
    logger.info(f"Build completed for build id {build_id}")

    return True, repository_name, dockerfile_dir


def docker_push(push_id):
    """
    Initiates the Docker push process for a given push_id.

    This function updates the push status in the database, performs the Docker push, and updates the status accordingly.

    Parameters:
    - push_id: Unique identifier for the push process.

    Returns:
    - bool: A boolean indicating the success of the push process.
    """    
    print(f"Push started for push id {push_id} ...")
    logger.info(f"Push started for push id {push_id} ...")

    push_obj:push = update_push_status(push_id, push.ProcessStatus.IN_PROGRESS)
    
    image_name_tag = push_obj.image_name + ":" + push_obj.image_tag
    
    if namespace is None:
        final_repository_name = image_name_tag
    else:    
        final_repository_name = namespace + "/" + image_name_tag

    try:
        client = docker.from_env()
        credential_map = client.login(username=registry_username, password=registry_password, registry=registry_url)

    except Exception as e:
        traceback.print_exc()
        logger.error("Error while logging into docker hub")
        print(f"An error occurred: {e}")
        update_push_status(push_id, push.ProcessStatus.FAILED, reason="Failed to Login")
        return False

    try:
        for line in client.images.push(repository=final_repository_name, stream=True, auth_config=auth_config, decode=True):
            print(line)
            if 'errorDetail' in line:
                raise Exception("Error while pushing the image")

        print(f"Image {image_name_tag} successfully pushed to {registry_url}")
        logger.info(f"Image {image_name_tag} successfully pushed to {registry_url}")

    except Exception as e:
        traceback.print_exc()
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

def remove_task_metadata(docker_image_tag, dockerfile_dir):
    """
    Removes metadata related to a completed Docker build and push task.

    This function removes the Docker image with the provided image tag and deletes the folder containing the Dockerfile.

    Parameters:
    - docker_image_tag: Tag of the Docker image to be removed.
    - dockerfile_dir: Path to the folder containing the Dockerfile.

    Returns:
    - bool: True if the removal process is successful.
    """    
    __delete_docker_image(docker_image_tag)
    __delete_files_in_folder(dockerfile_dir)
    return True

def __delete_docker_image(image_tag):
    """
    Deletes a Docker image with the specified image tag.

    This function uses the Docker API to remove a Docker image forcefully.

    Parameters:
    - image_tag: Tag of the Docker image to be removed.
    """    
    client = docker.from_env()
    
    try:
        image = client.images.get(image_tag)
        image.remove(force=True)
        print(f"Image {image_tag} successfully removed.")
    except docker.errors.ImageNotFound:
        print(f"Image {image_tag} not found.")
    except docker.errors.APIError as e:
        print(f"Error: {e}")

def __delete_files_in_folder(folder_path):
    """
    Deletes all files in a specified folder and then removes the folder itself.

    This function iterates through all files in the folder and deletes them. Afterward, it deletes the folder itself.

    Parameters:
    - folder_path: Path to the folder to be deleted.
    """    
    try:
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"File {file_path} successfully deleted.")
        shutil.rmtree(folder_path)
        print(f"Folder {folder_path} successfully deleted.")
    except OSError as e:
        print(f"Error: {e}")