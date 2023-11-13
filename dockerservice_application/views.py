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
    print("Starting build and push")
    logger.info('Starting build and push')

    serializer = FileUploadSerializer(data=request.data)

    if serializer.is_valid():
        
        file = serializer.validated_data["file"]

        image_name = serializer.validated_data["image_name"]
        image_tag = serializer.validated_data["image_tag"]
        build_id = build_and_push_service(file, image_name, image_tag)
        return Response({'status':status.HTTP_200_OK, 'message':"Build started", "build_id": build_id})
    else:
        return Response({'status':status.HTTP_400_BAD_REQUEST, 'message':serializer.errors})


@api_view(['GET'])
def get_build_push_status(request):

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
    
    build_id = uuid.uuid4()
    push_id = uuid.uuid4()

    folder_path, file_name = __save_file(dockerfile, str(build_id))
    
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

    task_id = async_task(docker_build_push, str(new_build_entry.build_id),  str(new_push_entry.push_id))

    return str(new_build_entry.build_id)

def __save_file(dockerfile, build_id):

    folder_path = os.path.join('uploaded_files', build_id)
    os.makedirs(folder_path, exist_ok=True)

    file_path = os.path.join(folder_path, dockerfile.name)
    with open(file_path, 'wb+') as destination:
        for chunk in dockerfile.chunks():
            destination.write(chunk)
    
    return folder_path+"/", dockerfile.name