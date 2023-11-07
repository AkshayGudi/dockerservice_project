import time
from ..models import build, push
from django.db import transaction


def docker_build_push(build_id, push_id):

    print(f"Started task {build_id}")

    docker_build(build_id)
    docker_push(push_id)

    print(f"Completed task -- {build_id}")


def docker_build(build_id):
    print(f"Build started for task {build_id} ...")
    __update_build_status(build_id, build.ProcessStatus.IN_PROGRESS)

    time.sleep(30)

    __update_build_status(build_id, build.ProcessStatus.COMPLETED)
    print(f"Build completed for task {build_id}")


def docker_push(push_id):
    print(f"Push started for task {push_id} ...")
    __update_push_status(push_id, push.ProcessStatus.IN_PROGRESS)

    time.sleep(30)

    __update_push_status(push_id, push.ProcessStatus.COMPLETED)
    print(f"Push completed for task {push_id}")

@transaction.atomic
def __update_build_status(build_id, status):
    build_obj = build.objects.get(build_id=build_id)
    build_obj.status = status
    build_obj.save()    

@transaction.atomic
def __update_push_status(push_id, status):
    push_obj = push.objects.get(push_id=push_id)
    push_obj.status = status
    push_obj.save()    