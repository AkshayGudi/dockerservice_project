# Implementation details and Instructions to run the project

## Note: 
1. Project code base has a sample dockerfile with the name __"CustomDockerFile"__ to test the application.
2. For the sake of simplicity project code has lightweight SQLite DB.

## Requirements
1. Python 3.11
2. Virtual environment using venv
3. Docker service and daemon
4. DockerHub account with username, password and namespace

## Design choice
1. __Django Rest Framework:__ We use Django Rest Framework to create a web application, which accepts dockerfile, and builds the docker image and pushes it to dockerhub
2. __Django Q:__ We use Django-Q to create a asynchronous task queue. Since building and pushing a docker image can take considerable amount of time, we use a asynchronous task queue, Django-Q to execute the tasks for building and pushing the docker image.
3. __Redis db:__ Django-Q uses redis to store the task queue. We use a docker container to run the Redis db.
4. __SQLite db:__ We use lightweight SQLite db to store the details of each created and pushed docker image, along with its build and push status.

## API Design
1. __Upload dockerfile:__ Endpoint to upload Dockerfile and provide 2 more mandatory fields, image name and image tag.
    
    Endpoint to upload docker file
    > __URL:__    
    http://localhost:8000/build-push

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
    > __URL:__    
    http://localhost:8000/build-push-status?build_id=5f37391b-28eb-44f2-89af-0c89f894811f

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
    > __URL:__    
    http://localhost:8000/retry-build?build_id=58ac48f8-cd12-4785-81c0-7d1463f88619


## Steps to start the project
- __Step1:__ Clone the project in your IDE enabled for python 3.11
    > git clone https://github.com/AkshayGudi/dockerservice_project.git

- __Step2:__ For ease of use, create a virtual environment in your IDE using python 3.11 and venv. And enable the virtual environment.    
_Copy and run the below commands_
    > python -m venv .my_env
    
    > __In Windows__   
    > .my_env/Scripts/activate
    
    > __In Linux__   
    > source .my_env/Scripts/activate

- __Step3:__ Install requirements: Root of the project has requirements.txt file, which contains all the dependencies required for the project.   
_Copy and run the below command_
    > pip install -r requirements.txt

- __Step4:__ We need redis db for our project. We can easily deploy a redis db using docker container.
Run the following docker command to pull the latest redis db and run it on port 6379 on localhost   
_Copy and run the below command_
    > docker run --name my-redis-server -d -p 127.0.0.1:6379:6379 redis

- __Step5:__ Start django project.   
    _Copy and run the below command_
    > python manage.py runserver

- __Step6:__ Start python django Q.    
    Django-Q is a Django application that provides an interface for handling asynchronous tasks in a Django project.   
    __Django-Q uses redis-db internally for task-queue, Hence Redis db needs to be up before you start the Django-Q__  
    Django-Q cluster uses 3 environment variables in our case 
    - Add Namespace for Dockerhub (in lowercase) by replacing ___<Dockerhub_Namespace_here>___ in below command 
    - Add User name for Dockerhub by replacing ___<Dockerhub_Username_here>___ in below command
    - Add Password for Dockerhub by replacing ___<Dockerhub_Password_here>___ in below command

    _Copy and run the below command based on you OS_
    > __In Windows__   
    >
    > set DOCKERHUB_USERNAME=___<Dockerhub_Username_here>___ && set DOCKERHUB_PASSWORD=___<Dockerhub_Password_here>___  && set DOCKERHUB_NAMESPACE=___<Dockerhub_namespace_here>___ && python manage.py qcluster

    > __In Linux or Git bash__
    >
    > DOCKERHUB_NAMESPACE=___<Dockerhub_namespace_here>___   
    DOCKERHUB_USERNAME=___<Dockerhub_Username_here>___    
    DOCKERHUB_PASSWORD=___<Dockerhub_Password_here>___        
    python manage.py qcluster

- __Step7:__ Use the ___API Design___ section above to interact with the application.
Note that project code base has a sample dockerfile with the name __"CustomDockerFile"__ to test the application.   
Use any RestClient like Postman or insomnia to test the APIs.