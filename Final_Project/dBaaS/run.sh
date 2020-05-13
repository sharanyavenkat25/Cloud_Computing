#!/bin/bash
docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)
sudo docker system prune --volumes -a
sudo nginx -s stop
docker-compose up --build
