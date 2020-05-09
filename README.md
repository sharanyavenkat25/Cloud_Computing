
Cloud Computing Course Assignments and projects

The following zip file contains three folders
- ASSIGNMENT_1
- ASSIGNMENT_2
- ASSIGNMENT_3
- FINAL_PROJECT

#### NOTE : 
The first three assignments are use Postgres as the Database
The final project however uses SQLite as the Database

--------------------------------

USER INSTANCE IP : 3.230.137.46

RIDES INSTANCE IP : 52.87.95.202

DBAAS INSTANCE IP : 34.236.79.177

LOAD BALANCER DNS : ridesharelb-397737146.us-east-1.elb.amazonaws.com

--------------------------------

This project is entirely built using docker containers.
Requests are made through Postman on the load-balancer and on port 80 if directly calling the instances.

### Steps for running the project :

The project consists of 3 folders
- rides
- users
- dBaaS

The rides and users folders correspond to the respective rides and user instances
the dbaas folder corresponds to the dbaas instance

### Running flask app for rides and users
- ssh into the instance using its IP
- cd into the respective folder (called a3_rides and a3_users on the instance)
- run docker-compose up --build


### Running Orchestrator in the dBaaS instance
- ssh into the instance using its IP
- cd into the folder (called sqlproj on the instance)
- execute the bash command ./run.sh
 the bash script builds the orchestrator, zookeeper, rmq and the workers and prunes previous volumes,images and containers.

