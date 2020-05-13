#!/usr/bin/env python3
import pika
import uuid
import sys
import json
from flask import * 
from flask import request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import *
from sqlalchemy import exc
from datetime import datetime
import requests
import sqlite3
from sqlite3 import Error
import docker
import threading
import os 
import logging
from kazoo.client import KazooClient
from kazoo.client import KazooState
from apscheduler.schedulers.background import BackgroundScheduler
import time


global final_count
final_count = 0
global num
num = 0
global dont_trigger
dont_trigger = 0
global reset
reset = 0



#-----------------removing old db copies --------------------
if(os.path.exists('query.db')):
	print("Old copy of db exists...removing it") 
	os.remove('query.db')




#-------------------------------------------------------ZOO KEEPER -----------------------------------------------------

zk = KazooClient(hosts='zoo:2181')
zk.start()

class Child(object):
    prev_children=list()

crashed=[]
  
c=Child()
print("Connecting to zoo keeper")
zk.ensure_path("/election")
@zk.ChildrenWatch("/election")
def watch_children(children):
		global reset
		print("Change in worker activity sensed....\n")
		
		print("Children are now : %s" % children)
		print("prev children : %s" % c.prev_children)
		print("dont trigger is set to..",dont_trigger)
		print("reset is set to..",reset)
		
		if(reset==1 and len(c.prev_children)>1 and len(children)>1):
			c.prev_children=children
			print("In Reset")
			print("Children are now : %s" % children)
			print("prev children : %s" % c.prev_children)
			reset=0

		print(set(c.prev_children).difference(set(children)))
		if(set(c.prev_children).difference(set(children)) and ('master' not in set(c.prev_children).difference(set(children))) and dont_trigger!=1):
			print("WATCH TRIGERRED...\n")
			print("available containers after slave crashed...")
			for container in client.containers.list():
				print(container.name)
			crashed=list(set(c.prev_children).difference(set(children)))
			print("Number of workers deleted",len(crashed))
			print("workers deleted are...",crashed)
			for node in crashed:
				slave_no=node
				print("slave which was crashed is..",slave_no)
				container_obj='container'+slave_no
				slave_name="new"+slave_no
				print("bringing up %s" % slave_name)
				container_obj= client.containers.run(
					privileged=True,
					image='worker:latest',
					name=slave_name,
					command='sh -c "python3 worker.py"',
					environment={'NODE_ENV':'SLAVE','ID':slave_name},
					links={'rmq':'rmq','zoo':'zoo'},
					network='sqlproj_default',
					restart_policy={'Name':'on-failure'},
					detach=True)

			print("available containers after slave recovery...")
			for container in client.containers.list():
				print(container.name)

		c.prev_children=children

#-----------------------------------------------------------------------------------------------------------------------------

#------------------------------------------------------ SQLite connections ----------------------------------------------------


def create_connection(db_file):
		conn = None
		try:
			conn = sqlite3.connect(db_file)
			return conn
		except Error as e:
			print(e)

		return conn


def create_table(conn, create_table_sql):
	
	try:
		c = conn.cursor()
		c.execute(create_table_sql)
	except Error as e:
		print(e)

database = r"query.db"

sql_create_query_table = """ CREATE TABLE IF NOT EXISTS write_queries (
										query text NOT NULL
								); """


# create a database connection
conn = create_connection(database)

# create tables
if conn is not None:
	# create query table
	create_table(conn, sql_create_query_table)
	print("table created successfully")
else:
	print("Error! cannot create the database connection.")
# -------------------------------------------------------------------------------------------------------------------------------------


app = Flask(__name__)

def myCounterfunc():
	global mycounter
	mycounter = mycounter+ 1

@app.before_request
def incrementcounter():
	if request.path in ('/api/v1/db/read'):
		myCounterfunc()

#----------------------------------------- SPAWNING INITIAL SLAVE AND MASTER --------------------------------------------------------------
client = docker.DockerClient(base_url='unix:///var/run/docker.sock')

print("CURRENTLY RUNNING CONTAINERS ARE...")

for container in client.containers.list():
	print(container.name)

print("CREATING CONTAINER 1 - MASTER")

container1 = client.containers.run(
	privileged=True,
	image='worker:latest',
	name='master',
	command='sh -c "python3 worker.py"',
	environment={'NODE_ENV':'MASTER','ID':'master'},
	links={'rmq':'rmq','zoo':'zoo'},
	network='sqlproj_default',
	restart_policy={'Name':'on-failure'},
	detach=True)

for container in client.containers.list():
	print(container.name)

print("CREATING CONTAINER 2 - SLAVE")

container2 = client.containers.run(
	privileged=True,
	image='worker:latest',
	name='slave',
	command='sh -c "python3 worker.py"',
	environment={'NODE_ENV':'SLAVE','ID':'slave'},
	links={'rmq':'rmq','zoo':'zoo'},
	network='sqlproj_default',
	restart_policy={'Name':'on-failure'},
	detach=True)  

print("FINISHED SPAWNING MASTER AND SLAVE") 

#present number of containers
for container in client.containers.list():
	print(container.name)


#----------------------------------------------------------------------------------------------------------------------------

#--------------------------------------------------- AUTO SCALING -----------------------------------------------------------


def auto_scaling():
	global mycounter

	print("--------------------Auto Scaling--------------------------")
	currentDT = datetime.now()
	print(" Current Time : ",currentDT)

	number_of_containers=(mycounter//20)+1
	curr_containers=(len(client.containers.list())-4)

	if(curr_containers<number_of_containers):
		print("Starting Scale up")
		 # exclude rabbitmq, orchestrator , zoo and master
		print("Current number of containers \t",curr_containers)
		print("Req Number of containers \t",number_of_containers)
		print("IN SCALE UP")
		global num
		num = num + 1
		scale_up=number_of_containers-curr_containers
		print("Inc number of slaves by \t",scale_up)
		for i in range(scale_up):

			number=str(num)
			container_obj='container'+number
			print(container_obj)
			container_obj= client.containers.run(
			privileged=True,
			image='worker:latest',
			name='slave'+number,
			command='sh -c "python3 worker.py"',
			environment={'NODE_ENV':'SLAVE','ID':'slave'+number},
			links={'rmq':'rmq','zoo':'zoo'},
			network='sqlproj_default',
			restart_policy={'Name':'on-failure'},
			detach=True)

	if(curr_containers>number_of_containers):
		global dont_trigger
		dont_trigger = 1
		print("Starting scale down")
		print("Dont Trigger set to : ",dont_trigger)

		# number_of_containers=(mycounter//20)+1
		# curr_containers=(len(client.containers.list())-4) # exclude rabbitmq, orchestrator, zoo and master
		print("Current number of containers \t",curr_containers)
		print("Req Number of containers \t",number_of_containers)
		print("IN SCALE DOWN")
		scale_down=curr_containers-number_of_containers
		slaves=[]		
		for i in client.containers.list():
			if(i.name not in ['rmq','orchestrator','master','zoo','sqlproj_worker_1'] and i.attrs['State']['Pid']!=0 and scale_down>0):
				i.stop()
			scale_down=scale_down-1
				

	if(curr_containers==number_of_containers):
		print("Current number of containers \t",curr_containers)
		print("Req Number of containers \t",number_of_containers)
		print("No Scaling req....")
		dont_trigger = 0
		global reset
		reset = 1

	mycounter=0 # set counter to 0 every 2 min
	print("My counter is reset to : ",mycounter)

# if(final_count==1):

# 	sched = BackgroundScheduler(daemon=True)
# 	sched.add_job(auto_scaling,'interval',minutes=2)
# 	sched.start()

#----------------------------------------------------------------------------------------------------------------------------------------

#----------------------------------------------------------- API CALLS ------------------------------------------------------------------		

class Readreq(object):

	def __init__(self):
		self.connection = pika.BlockingConnection(
			pika.ConnectionParameters(host='rmq'))

		self.channel = self.connection.channel()
		result = self.channel.queue_declare(queue='res_queue', durable=True)

		# result = self.channel.queue_declare(queue='', exclusive=True)
		self.callback_queue = result.method.queue

		self.channel.basic_consume(
			queue=self.callback_queue,
			on_message_callback=self.on_response,
			auto_ack=True)

	def on_response(self, ch, method, props, body):
		if self.corr_id == props.correlation_id:
			self.response = body

	def call(self, query):
		self.response = None
		self.corr_id = str(uuid.uuid4())
		self.channel.basic_publish(
			exchange='',
			routing_key='read_queue',
			properties=pika.BasicProperties(
				reply_to=self.callback_queue,
				correlation_id=self.corr_id,
				delivery_mode=2,
			),
			body=json.dumps(query))
		
		while self.response is None:
			self.connection.process_data_events()
		self.connection.close()

		return json.loads(self.response)



	
@app.route("/api/v1/db/sync",methods=["GET"])
def sync():
	command='SELECT * FROM write_queries'
	conn = sqlite3.connect('query.db')
	r = conn.cursor()
	r.execute(command)
	conn.commit()
	res = r.fetchall()
	print("Printing from sync api...\n",res,type(res))
	return jsonify(res)
	


@app.route("/api/v1/db/write",methods=["POST"])
def write_db():
	print("in write api")
	connection = pika.BlockingConnection(
		pika.ConnectionParameters(host='rmq'))
	channel = connection.channel() 
	channel.queue_declare(queue='write_queue', durable=True)
	
	table=request.get_json()["table"]
	cond=request.get_json()["cond"]
	vals=request.get_json()["vals"]
	check=request.get_json()["check"]
	
	# makes a table for storing every write query
	if(check=="delete"):
		command="DELETE FROM "+table+" WHERE "+cond
	if(check =="insert"):
		command="INSERT INTO "+table+" VALUES "+vals
	if(check=="update"):
		command=" UPDATE "+table+" SET "+vals+" WHERE "+cond
	print("Command stored for syncing in query db :", command)
	query = 'INSERT INTO write_queries(query) VALUES ('+'"'+command+'"'+')'
	print("Query to be executed\n",query)
	conn = sqlite3.connect('query.db')
	r = conn.cursor()
	r.execute(query)
	conn.commit()
	message = {"table":table,"cond":cond,"vals":vals,"check":check}
	channel.basic_publish(
		exchange='',
		routing_key='write_queue',
		body=json.dumps(message),
		properties=pika.BasicProperties(
		delivery_mode=2,  # make message persistent
		))
	print(" [x] Sent %r" % message)
	connection.close()
	return "Success",200


@app.route("/api/v1/db/read",methods=["POST"])
def read_db():
	global final_count
	final_count+=1

	print("in read api")
	print("Total Number of read requests sent in total \t",final_count)
	print("Read Counter in this interval \t",mycounter)
	if(final_count==1):
		print("Starting the app schedular")
		sched = BackgroundScheduler(daemon=True)
		sched.add_job(auto_scaling,'interval',minutes=2)
		sched.start()

	table=request.get_json()["table"]
	columns=request.get_json()["columns"]
	where=request.get_json()["where"]

	message = {"table":table,"columns":columns,"where":where}
	readreq = Readreq()
	response = readreq.call(message)
	del readreq
	print(" [x] Sent %r" % message)
	return json.dumps(response)



@app.route("/api/v1/db/clear",methods=["POST"])
def clear_db():
	print("in clear api")
	
	connection = pika.BlockingConnection(
		pika.ConnectionParameters(host='rmq'))
	channel = connection.channel() 
	channel.queue_declare(queue='write_queue', durable=True)
	
	message = {"table":"userdata","cond":"1==1","vals":"","check":"delete"}
	channel.basic_publish(
		exchange='',
		routing_key='write_queue',
		body=json.dumps(message),
		properties=pika.BasicProperties(
		delivery_mode=2,  # make message persistent
		))
	print(" [x] cleared userdata %r" % message)
	message = {"table":"rides","cond":"1==1","vals":"","check":"delete"}
	channel.basic_publish(
		exchange='',
		routing_key='write_queue',
		body=json.dumps(message),
		properties=pika.BasicProperties(
		delivery_mode=2,  # make message persistent
		))
	print(" [x] cleared rides %r" % message)
	connection.close()
	return "Success",200



@app.route("/api/v1/crash/master",methods=["POST"])
def crash_master():
		# global dont_trigger
		# dont_trigger=0
		print("in crash master api ......")
		client = docker.from_env()
		a = list()
		a = client.containers.list(all)
		for i in a:
			print("THE NAME METHOD \t",i.attrs['Name'])
			if i.name=='master' and i.attrs['State']['Pid'] != 0:
				pid = i.attrs['State']['Pid']
				i.kill()
			elif i.name=='master' and i.attrs['State']['Pid'] == 0:
				print("Master already killed.")
				abort(400,description="Master killed already")
				#return Response(,status=200,mimetype='application/json')
		message=pid
		#error handling
		return Response(json.dumps(message),status=200,mimetype='application/json')


@app.route("/api/v1/crash/slave",methods=["POST"])
def crash_slave():
		global dont_trigger
		dont_trigger=0
		print("in crash slave api ......")
		
		client = docker.from_env()
		a = list()
		a = client.containers.list(all)
		pid_dict = {}
		#first filter
		for i in a:
			if(i.name not in ['rmq','orchestrator','master','zoo','sqlproj_worker_1']):
				print("i.attrs['Name'] : \t", i.attrs['Name'])
				pid_dict[i]=i.attrs['State']['Pid']

		pid_dict = sorted(pid_dict.items(), key=lambda kv: kv[1])
		#second filter
		for i in pid_dict:
			if i[1]==0:
				pid_dict.remove(i)
		slave_tuple = pid_dict[-1]
		slave_container_object = slave_tuple[0]
		message = list()
		message.append(slave_tuple[1])
		print(message)
		try:
			slave_container_object.kill()
			return Response(json.dumps(message),status=200,mimetype='application/json')
		except:
			abort(400,description="No more slaves to kill.")


@app.route("/api/v1/worker/list",methods=["GET"])
def worker_list():
	print("In worker list API")
	client = docker.from_env()
	a = list()
	a = client.containers.list(all)
	pid_dict = {}
	for i in a:
		if i.name not in ['rmq','orchestrator','zoo','sqlproj_worker_1'] and i.attrs['State']['Pid'] != 0 :
			pid_dict[i]=i.attrs['State']['Pid']
	pid_dict = sorted(pid_dict.values())
	return jsonify(pid_dict)



if(__name__=="__main__"):
	global mycounter
	mycounter = 0  
	app.run(host="0.0.0.0",debug=True,use_reloader=False) 
	

