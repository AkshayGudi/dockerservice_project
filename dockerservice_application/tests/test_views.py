from django.test import TestCase
from unittest.mock import patch, MagicMock, ANY
from rest_framework import status
from rest_framework.test import APIRequestFactory
from ..views import build_and_push_docker, get_build_push_status, retry_build
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile

import io

class BuildAndPushDockerViewTest(TestCase):

    @patch('dockerservice_application.views.build_and_push_service')
    def test_build_and_push_docker_view(self, mock_build_and_push_service):
        
        # Create a mock build_id to be returned by the mock service
        mock_build_id = '585c7054-2e6a-45e9-80fc-92cd3c153ca1'
        mock_build_and_push_service.return_value = mock_build_id

        # Create a mock file for testing
        # mock_file = io.BytesIO(b'This is content of DockerFile')
        # # mock_file = MagicMock(name='mock_file')  
        # mock_file.name = 'MyDockerFile'
        # mock_file.seek(0)

        file_content = b"Mock Dockerfile Content"
        mock_file = InMemoryUploadedFile(io.BytesIO(file_content), None, 'MyDockerFile', 'text/plain', len(file_content), None)

        # Create a request with the necessary data
        factory = APIRequestFactory()
        request_data = {
            'file': mock_file,
            'image_name': 'test_image',
            'image_tag': 'latest',
        }
        request = factory.post('/build-push/', data=request_data, format='multipart')

        # Call the view function
        response = build_and_push_docker(request)

        # Check that the build_and_push_service was called with the correct arguments
        mock_build_and_push_service.assert_called_once_with(ANY, 'test_image', 'latest')

        # Check the response status code and content
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Build started')
        self.assertEqual(response.data['build_id'], mock_build_id)


    @patch("dockerservice_application.models.push.objects.get")
    @patch("dockerservice_application.models.build.objects.get")
    def test_get_build_push_status(self, mock_build_objects_get, mock_push_objects_get):
        
        factory = APIRequestFactory()

        build_id = "585c7054-2e6a-45e9-80fc-92cd3c153ca1"
        push_id = "485c7054-2e6a-45e9-80fc-92cd3c153ca1"
        reason = 'Failed due to error during image build'        

        mock_build_obj = MagicMock()		
        mock_build_obj.image_name = "my_busy_box_image"
        mock_build_obj.image_tag = "latest"
        mock_build_obj.status = "Failed"
        mock_build_obj.build_id = build_id
        mock_build_obj.failed_reason = reason

        mock_build_objects_get.return_value = mock_build_obj

        mock_push_obj = MagicMock()
        mock_push_obj.image_name = "my_busy_box_image"
        mock_push_obj.image_tag = "latest"
        mock_push_obj.status = "Failed"
        mock_push_obj.push_id = push_id
        mock_push_obj.failed_reason = reason

        mock_push_objects_get.return_value = mock_push_obj

        request = factory.get("/build-push-status/?build_id=585c7054-2e6a-45e9-80fc-92cd3c153ca1")
        response = get_build_push_status(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], status.HTTP_200_OK)

        response_body = response.data['build_status']

        self.assertEqual(response_body['build_id'], build_id)
        self.assertEqual(response_body['build_status'], mock_build_obj.status)
        self.assertEqual(response_body['Build Fail Reason'], mock_build_obj.failed_reason)
        self.assertEqual(response_body['Push Fail Reason'], mock_push_obj.failed_reason)
        

    @patch("dockerservice_application.views.async_task")
    @patch("dockerservice_application.models.push.objects.get")
    @patch("dockerservice_application.models.build.objects.get")    
    def test_retry_failed_build(self, mock_build_objects_get, mock_push_objects_get, mock_async_methods):

        factory = APIRequestFactory()

        build_id = "585c7054-2e6a-45e9-80fc-92cd3c153ca1"
        push_id = "485c7054-2e6a-45e9-80fc-92cd3c153ca1"
        reason = 'Failed due to error during image build'        

        mock_build_obj = MagicMock()		
        mock_build_obj.image_name = "my_busy_box_image"
        mock_build_obj.image_tag = "latest"
        mock_build_obj.status = "Failed"
        mock_build_obj.build_id = build_id
        mock_build_obj.failed_reason = reason

        mock_build_objects_get.return_value = mock_build_obj

        mock_push_obj = MagicMock()
        mock_push_obj.image_name = "my_busy_box_image"
        mock_push_obj.image_tag = "latest"
        mock_push_obj.status = "Failed"
        mock_push_obj.push_id = push_id
        mock_push_obj.failed_reason = reason

        mock_push_objects_get.return_value = mock_push_obj


        mock_async_methods.return_value = 'task_id'

        request = factory.get("/retry-build/?build_id=585c7054-2e6a-45e9-80fc-92cd3c153ca1")
        
        response = retry_build(request)

        self.assertEquals(response.data['status'], status.HTTP_200_OK)
        self.assertEquals(response.data['message'], 'Rebuild started')
        self.assertEquals(response.data['build_id'], build_id)

    @patch("dockerservice_application.views.async_task")
    @patch("dockerservice_application.models.push.objects.get")
    @patch("dockerservice_application.models.build.objects.get")    
    def test_retry_completed_build(self, mock_build_objects_get, mock_push_objects_get, mock_async_methods):

        factory = APIRequestFactory()

        build_id = "585c7054-2e6a-45e9-80fc-92cd3c153ca1"
        push_id = "485c7054-2e6a-45e9-80fc-92cd3c153ca1"
        reason = ''        

        mock_build_obj = MagicMock()		
        mock_build_obj.image_name = "my_busy_box_image"
        mock_build_obj.image_tag = "latest"
        mock_build_obj.status = "Completed"
        mock_build_obj.build_id = build_id
        mock_build_obj.failed_reason = reason

        mock_build_objects_get.return_value = mock_build_obj

        mock_push_obj = MagicMock()
        mock_push_obj.image_name = "my_busy_box_image"
        mock_push_obj.image_tag = "latest"
        mock_push_obj.status = "Completed"
        mock_push_obj.push_id = push_id
        mock_push_obj.failed_reason = reason

        mock_push_objects_get.return_value = mock_push_obj

        mock_async_methods.return_value = 'task_id'

        request = factory.get("/retry-build/?build_id=585c7054-2e6a-45e9-80fc-92cd3c153ca1")
        
        response = retry_build(request)

        self.assertEquals(response.data['status'], status.HTTP_400_BAD_REQUEST)
        self.assertEquals(response.data['message'], 'Build and Push not failed')
        self.assertEquals(response.data['build_id'], build_id)














