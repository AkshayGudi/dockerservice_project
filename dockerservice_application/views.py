from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework import status
from .services.docker_service import docker_build_push, docker_push

from django_q.tasks import async_task

import uuid
from .models import build, push
from datetime import timedelta
from django.utils import timezone
from django.db import transaction

from rest_framework.parsers import MultiPartParser, FormParser
from .file_serializers import FileUploadSerializer
import os

import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def build_and_push_docker(request):
    """
    View function to handle HTTP POST requests to take a dockerfile and build an image and push it to dockerhub.

    Parameters:
    - request: HttpRequest object containing the HTTP request data with input dockerfile, image name and image tag.

    Returns:
    - JsonResponse: Acknowledgement about start of image bulid and push process
    """    
    print("Starting build and push")
    logger.info('Starting build and push')

    serializer = FileUploadSerializer(data=request.data)

    if serializer.is_valid():
        
        file = serializer.validated_data["file"]
        image_name = serializer.validated_data["image_name"]
        image_tag = serializer.validated_data["image_tag"]

        try:
            build_id = build_and_push_service(file, image_name, image_tag)        
        except Exception as e:
            print(e)

        return Response({'status':status.HTTP_200_OK, 'message':"Build started", "build_id": build_id})
    else:
        return Response({'status':status.HTTP_400_BAD_REQUEST, 'message':serializer.errors})


@api_view(['GET'])
def get_build_push_status(request):
    """
    View function to handle HTTP GET request to check the status of build given a build_id.

    Parameters:
    - request: HttpRequest object containing the HTTP request data with query parameter having build_id

    Returns:
    - JsonResponse: status of build and push tasks
    """
    build_id = request.GET.get('build_id')

    if build_id != None:
        try:
            build_obj = build.objects.get(build_id=build_id)
            push_obj = push.objects.get(build=build_obj)
            data = dict()
            data["build_id"] = build_id
            data["build_status"] = build_obj.status

            if build_obj.status == build.ProcessStatus.FAILED:
                data["Build Fail Reason"] = build_obj.failed_reason

            data["push_status"] = push_obj.status

            if push_obj.status == push.ProcessStatus.FAILED:
                data["Push Fail Reason"] = push_obj.failed_reason

            return Response({'status': status.HTTP_200_OK, "build_status": data})
        except:
            return Response({'status':status.HTTP_400_BAD_REQUEST, 'message':'Invalid build id'} )
    else:
        return Response({'status':status.HTTP_400_BAD_REQUEST, 'message':'Invalid input'}  )


@api_view(["GET"])
def retry_build(request):
    """
    View function to handle HTTP GET request to retry build and push of a failed task given a build_id.

    Parameters:
    - request: HttpRequest object containing the HTTP request data with query parameter having build_id

    Returns:
    - JsonResponse: Acknowledgement about retry of image bulid and push process
    """
    build_id = request.GET.get('build_id')
    
    push_id, build_failed_flag, push_failed_flag, reason = check_build_and_push_status(build_id)

    if (not build_failed_flag) and (not push_failed_flag):
        return Response({'status': status.HTTP_400_BAD_REQUEST, 'message':reason, "build_id": build_id})

    if build_failed_flag:
        async_task(docker_build_push, str(build_id),  str(push_id))

    elif (not build_failed_flag) and (push_failed_flag):
        async_task(docker_push, push_id)

    return Response({'status':status.HTTP_200_OK, 'message':"Rebuild started", "build_id": build_id})

def check_build_and_push_status(build_id):

    if build_id == None:
        return None, False, False, "Please provide the build_id"

    build_obj = build.objects.get(build_id=build_id)
    push_obj = push.objects.get(build = build_obj)

    if build_obj == None:
        return None, False, False, f"Build with id {build_id} does not exist"

    if build_obj.status != build.ProcessStatus.FAILED:
        if push_obj.status != push.ProcessStatus.FAILED:
            return push_obj.push_id, False, False, f"Build and Push not failed"
        else:
            return push_obj.push_id, False, True, ""

    return push_obj.push_id, True, True, ""

# Save the entry in the database within a transaction
@transaction.atomic
def build_and_push_service(dockerfile, image_name, image_tag):
    """
    Builds and pushes a Docker image with the provided Dockerfile, image name, and image tag.

    This function does the following:
    1. Generates unique build and push IDs using UUID.
    2. Saves the provided Dockerfile to a folder and records the file location.
    3. Creates database entries for build and push processes with initial status as PENDING.
    4. Initiates an asynchronous task (`docker_build_push`) to perform the actual build and push.
    5. Returns the build ID as a string.

    Parameters:
    - dockerfile: Uploaded Dockerfile.
    - image_name: Name of the Docker image.
    - image_tag: Tag for the Docker image.

    Returns:
    - str: The build ID of the initiated build process.
    """

    print("Entered build_and_push_service")
    build_id = uuid.uuid4()
    push_id = uuid.uuid4()

    folder_path, file_name = __save_file(dockerfile, str(build_id))
    
    print("Creating build")
    new_build_entry = build.objects.create(
        build_id=build_id,
        build_time=timezone.now(),
        expiration_time=timezone.now() + timedelta(days=10),
        status=build.ProcessStatus.PENDING,
        file_loc=folder_path,
        file_name = file_name,
        image_loc='',  # Assign an appropriate value
        image_name=image_name,
        image_tag=image_tag
    )

    print("Completed creating build")
    new_push_entry = push.objects.create(
        push_id = push_id,
        build = new_build_entry,
        push_time = timezone.now(),
        expiration_time = timezone.now() + timedelta(days=10),
        status=build.ProcessStatus.PENDING,
        image_loc = '',
        failed_reason = '',
        image_name=image_name,
        image_tag=image_tag
    )

    # docker_build_push(str(new_build_entry.build_id), str(new_push_entry.push_id))
    task_id = async_task(docker_build_push, str(new_build_entry.build_id),  str(new_push_entry.push_id))

    return str(new_build_entry.build_id)

def __save_file(dockerfile, build_id):
    """
    Saves the provided Dockerfile to a folder and returns the folder path and file name.

    Parameters:
    - dockerfile: Uploaded Dockerfile.
    - build_id: Unique identifier for the build.

    Returns:
    - Tuple: A tuple containing the folder path and file name where the Dockerfile is saved.
    """
    folder_path = os.path.join('uploaded_files', build_id)
    os.makedirs(folder_path, exist_ok=True)

    file_path = os.path.join(folder_path, dockerfile.name)
    with open(file_path, 'wb+') as destination:
        for chunk in dockerfile.chunks():
            destination.write(chunk)
    
    return folder_path+"/", dockerfile.name