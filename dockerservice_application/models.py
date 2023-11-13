from django.db import models
import uuid
from datetime import timedelta
from django.utils import timezone

class build(models.Model):

    class Meta:
        db_table = "build"

    class ProcessStatus(models.TextChoices):
        PENDING = 'Pending'
        IN_PROGRESS = 'In Progress'
        COMPLETED = 'Completed'
        FAILED = 'Failed'

    current_time = timezone.now()

    build_id =  models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    build_time =  models.DateField(default=timezone.now()) 
    expiration_time = models.DateField(default=timezone.now() + timedelta(days=10))
    status = models.CharField(max_length=20, choices=ProcessStatus.choices, default=ProcessStatus.PENDING)
    file_loc = models.CharField(max_length=1000)
    file_name = models.CharField(max_length=100)
    image_loc = models.CharField(max_length=1000)
    failed_reason = models.CharField(max_length=500)
    image_name = models.CharField(max_length=100)
    image_tag = models.CharField(max_length=100)

class push(models.Model):

    class Meta:
        db_table = "push"

    class ProcessStatus(models.TextChoices):
        PENDING = 'Pending'
        IN_PROGRESS = 'In Progress'
        COMPLETED = 'Completed'
        FAILED = 'Failed'


    current_time = timezone.now()

    push_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    build = models.ForeignKey(to=build, null=True, blank=True, on_delete=models.CASCADE)
    
    push_time =  models.DateField(default=current_time) 
    expiration_time = models.DateField(default=current_time + timedelta(days=10))
    status = models.CharField(max_length=20, choices=ProcessStatus.choices, default=ProcessStatus.PENDING)
    image_loc = models.CharField(max_length=1000)
    failed_reason = models.CharField(max_length=500)
    image_name = models.CharField(max_length=100)
    image_tag = models.CharField(max_length=100)

