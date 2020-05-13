
## Cloud Computing Course *UE17CS352 Spring-2020, PES University* ### Assignments and Final semester project

--------------------------------
### Contributions by,

Sharanya Venkat *PES1201700218*

Mithali Shashidhar *PES1201700190*

Aishwarya M A Ramanath *PES1201700872*

--------------------------------

The following repository contains source code and other dependent files for
- ASSIGNMENT 1
- ASSIGNMENT 2
- ASSIGNMENT 3
- FINAL SEMESTER PROJECT
done as a part of the course *Cloud-Computing, UE17CS352* in *Spring 2020, PES University*

### Connecting to the Instances
-------------------------------

USER INSTANCE IP : 3.230.137.46

RIDES INSTANCE IP : 52.87.95.202

DBAAS INSTANCE IP : 34.236.79.177

LOAD BALANCER DNS : ridesharelb-397737146.us-east-1.elb.amazonaws.com

--------------------------------

### Implementation

This project is entirely built using docker containers.
Requests are made through Postman on the load-balancer for the user and rides APIs and on port 80 when calling instance specific APIs directly on the orchestrator or rides & users instances.

### Steps for running the Final project :

The Final project consists of 3 folders
- rides
- users
- dBaaS

The rides and users folders correspond to the respective rides and user instances and the dbaas folder corresponds to the dbaas instance

### Running flask app for rides and users
- ssh into the instance using its IP
- cd into the respective folder (called a3_rides and a3_users on the instance)
- run docker-compose up --build


### Running Orchestrator in the dBaaS instance
- ssh into the instance using its IP
- cd into the folder (called sqlproj on the instance)
- execute the bash command ./run.sh

 The bash script builds the orchestrator, zookeeper, rmq and the workers and prunes previous volumes,images and containers.
 
 ### Tech-Stack
 - Docker
 - Docker SDK
 - Kazoo
 - Zoo keeper
 - Flask
 - SQLAlchemy
 - Pika
 - Psycopg2
 
 #### NOTE : 
The first three assignments use Postgres as the Database.

The final project however uses SQLite as the Database


