from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services.docker_service import docker_build_push

from django_q.tasks import async_task

import uuid
from .models import build, push
from datetime import timedelta
from django.utils import timezone
from django.db import transaction


@api_view(['GET'])
def build_and_push_docker(request):
    print("Starting build and push")

    build_id = build_and_push_service()

    return Response({'status':status.HTTP_200_OK, 'message':"test code", "build_id": build_id})


@api_view(['GET'])
def get_build_push_status(request):

    build_id = request.GET.get('build_id')

    if build_id != None:
        try:
            build_obj = build.objects.get(build_id=build_id)
            push_obj = push.objects.get(build=build_obj)
            return Response({'status':status.HTTP_200_OK, 'build_id':build_id, "build_status": build_obj.status, "push_status": push_obj.status})
        except:
            return Response({'status':status.HTTP_400_BAD_REQUEST, 'message':'Invalid build id'} )
    else:
        return Response({'status':status.HTTP_400_BAD_REQUEST, 'message':'Invalid input'}  )


@transaction.atomic
def build_and_push_service():
    
    build_id = uuid.uuid4()
    push_id = uuid.uuid4()

    # Save the entry in the database within a transaction
    new_build_entry = build.objects.create(
        build_id=build_id,
        task_id='',  # Assign an appropriate value
        build_time=timezone.now(),
        expiration_time=timezone.now() + timedelta(days=10),
        status=build.ProcessStatus.PENDING,
        file_loc='',  # Assign an appropriate value
        image_loc=''  # Assign an appropriate value
    )

    new_push_entry = push.objects.create(
        push_id = push_id,
        build = new_build_entry,
        task_id = '',
        push_time = timezone.now(),
        expiration_time = timezone.now() + timedelta(days=10),
        status=build.ProcessStatus.PENDING,
        failed_reason = ''
    )

    task_id = async_task(docker_build_push, str(new_build_entry.build_id),  str(new_push_entry.push_id))

    new_build_entry.task_id = task_id
    new_build_entry.save()

    new_push_entry.task_id = task_id
    new_push_entry.save()

    return str(new_build_entry.build_id)