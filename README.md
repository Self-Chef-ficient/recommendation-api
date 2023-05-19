# recommendation-api

## Building Docker image

docker build -t recommendation .

## Run docker image

docker run -d recommendation 

Do a POST request on 127.0.0.1:5000/getRecs with data in below format to get a response

## Sample input and outpt 

### Input
{
    "user": "f1393d83-fef8-439a-8fb3-3fb018632fb0",
    "quiz": {
        "orange": "liked",
        "garlic": "disliked",
        "pork": "disliked",
        "coffee": "liked",
        "ginger": "disliked"
    }
}

### Output 
{
    "recommendations": [
        "7ad34d727c"
    ],
    "user": "f1393d83-fef8-439a-8fb3-3fb018632fb0"
}
