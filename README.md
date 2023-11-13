# Implementation details and Instructions to run the project

___Note: File "architecture.jpeg" provides overview of architecture and components of the project___

### Requirements
1. Python 3.8.2
2. Virtual environment using venv
3. docker service and daemon

### Design choice
1. __Django Rest Framework:__ We use Django Rest Framework to create a web application, which accepts dockerfile, and builds the docker image and pushes it to dockerhub
2. __Django Q:__ We use Django-Q to create a asynchronous task queue. Since building and pushing a docker image can take considerable amount of time, we use a asynchronous task queue, Django-Q to execute the tasks for building and pushing the docker image.
3. __Redis db:__ Django-Q uses redis to store the task queue. We use a docker container to run the Redis db.
4. __SQLite db:__ We use lightweight SQLite db to store the details of each created and pushed docker image, along with its build and push status.

### API Design
1. __Upload dockerfile:__ Endpoint to upload Dockerfile and provide 2 more mandatory fields, image name and image tag.
    
    Endpoint to upload docker file
    > __URL:__ http://localhost:8000/build-push

    ```JSON
    Input

    Body (form fields):
        file: <Dockerfile> !without any file extension
        image_name: <Your user defined image name>
        image_tag: <Your user defined image tag>

    Response (Sample Response):
        { "status": 200,
        "message": "Build started",
        "build_id": "c5b0844f-c8ae-43d2-9c02-6d80e0e8f021" }

    ```

2. __Get Build and Push Status:__: Endpoint to check the status of the uploaded dockerfile. To check the status of image built and image pushed.

    We provide __"build_id"__ as query parameter for our endpoint
    > __URL:__ http://localhost:8000/build-push-status?build_id=5f37391b-28eb-44f2-89af-0c89f894811f

    ``` JSON
    Response (Sample Response):
        {
        "status": 200,
        "build_status": {
            "build_id": "5f37391b-28eb-44f2-89af-0c89f894811f",
            "build_status": "Completed",
            "push_status": "In Progress",
            }
        }

    ```

3. __Retry Failed Build or Push:__ Endpoint to retry the failed image build process or image push process

    We provide __"build_id"__ as query parameter for this endpoint to retry the build
    > __URL:__ http://localhost:8000/retry-build?build_id=58ac48f8-cd12-4785-81c0-7d1463f88619


### Steps to start the project

1. Start docker redis
2. Start python django
3. Start python django Q along with dockerhub namespace, username, password