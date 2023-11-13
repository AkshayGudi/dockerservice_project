from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from unittest.mock import MagicMock, patch
import unittest

from ..services.docker_service import docker_build
from ..services.docker_service import docker_push

class DockerServiceTest(TestCase):

    @patch('docker.from_env')
    @patch('dockerservice_application.services.docker_service.update_build_status')
    @patch('dockerservice_application.services.docker_service.update_push_status')
    def test_docker_build(self, mock_update_push_status_func, mock_update_build_status_func, mock_docker):

        # Set up input data
        build_id = "585c7054-2e6a-45e9-80fc-92cd3c153ca1"
        push_id = "485c7054-2e6a-45e9-80fc-92cd3c153ca1"

        # Mock the build object
        mock_build_obj = MagicMock()
        mock_build_obj.image_name = "my_busy_box_image"
        mock_build_obj.image_tag = "latest"
        mock_build_obj.file_name = "busybox_dockerfile"
        mock_build_obj.file_loc = "my_dockerfile_dir"
        mock_build_obj.status = "In Progress"
        mock_build_obj.build_id = build_id

        # Mock the push object
        mock_push_obj = MagicMock()
        mock_push_obj.image_name = "my_busy_box_image"
        mock_push_obj.image_tag = "latest"
        mock_push_obj.status = "Pending"
        mock_push_obj.push_id = push_id


        mock_update_build_status_func.return_value = mock_build_obj
        mock_update_push_status_func.return_value = mock_push_obj

        mock_client = MagicMock()
        mock_client.images.build.return_value = ("your_image_id", iter(["image", "logs"]))
        mock_docker.return_value = mock_client

        self.assertTrue(docker_build(build_id, push_id))


    @patch('docker.from_env')
    @patch('dockerservice_application.services.docker_service.update_push_status')
    def test_docker_push(self, mock_update_push_status_func, mock_docker):

        push_id = "485c7054-2e6a-45e9-80fc-92cd3c153ca1"
        mock_push_obj = MagicMock()
        mock_push_obj.image_name = "my_busy_box_image"
        mock_push_obj.image_tag = "latest"
        mock_push_obj.status = "Pending"
        mock_push_obj.push_id = push_id

        mock_update_push_status_func.return_value = mock_push_obj

        mock_client = MagicMock()
        mock_client.images.push.return_value = ("Pushed 25% ...", "Pushed 50% ...", "Pushed 75% ...", "Pushed 100% ...")


        login_output = {
        'Status': 'Login Succeeded',
        'Registry': 'registry.example.com',
        'Username': 'your_username',
        'Password': 'your_password'}

        mock_client.login.return_value = login_output
        mock_docker.return_value = mock_client

        self.assertTrue(docker_push(push_id))




# if __name__ == '__main__':
#     unittest.main()
