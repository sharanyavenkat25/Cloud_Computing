#!/usr/bin/env python3
import pika
import time
from flask import * 
from flask import request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import *
from sqlalchemy import exc
from datetime import datetime
import requests
from numpy import genfromtxt
import os
import sqlite3
from sqlite3 import Error
import logging

from kazoo.client import KazooClient
from kazoo.client import KazooState

id=os.environ['ID']
id=str(id)
print("ID OF THE WORKER IS...",id)

zk = KazooClient(hosts='zoo:2181')
zk.start()
print("Connecting to zoo keeper")
# Deleting all existing nodes (This is just for the demo to be consistent)
#zk.delete("/election", recursive=True)

# Ensure a path, create if necessary
zk.ensure_path("/election")
path ="/election/"+id
print("zk node path\t",path)
#Create a node with data
if zk.exists(path):
    print("Node already exists")
else:
    zk.create(path,b"pid",ephemeral=True)
    print("Creating zk node")

children = zk.get_children("/election")
print(children)

print(os.environ['NODE_ENV'])

if(os.environ['NODE_ENV']=="SLAVE"):

	print("RUNNING SLAVE")
	
	
	
	def create_connection(db_file):
		conn = None
		try:
			conn = sqlite3.connect(db_file)
			return conn
		except Error as e:
			print(e)

		return conn


	def create_table(conn, create_table_sql):
		""" create a table from the create_table_sql statement
		:param conn: Connection object
		:param create_table_sql: a CREATE TABLE statement
		:return:
		"""
		try:
			c = conn.cursor()
			c.execute(create_table_sql)
		except Error as e:
			print(e)

	database = r"try.db"

	sql_create_users_table = """ CREATE TABLE IF NOT EXISTS userdata (
										uname text NOT NULL,
										pwd text NOT NULL,
										created_ride text
									); """
	
	sql_create_rides_table = """CREATE TABLE IF NOT EXISTS rides (
								rideId integer NOT NULL,
								created_by text,
								passengers text,
								source text,
								dest text,
								time_stamp timestamp
							);"""




	# create a database connection
	conn = create_connection(database)

	# create tables
	if conn is not None:
		# create projects table
		create_table(conn, sql_create_users_table)

		# create tasks table
		create_table(conn, sql_create_rides_table)
	else:
		print("Error! cannot create the database connection.")



	### SYNCING SLAVE WITH OLD DATA...
	



	connection = pika.BlockingConnection(
		pika.ConnectionParameters(host='rmq'))
	channel = connection.channel()

	channel.queue_declare(queue='read_queue', durable=True)
	print(' [*] Waiting for messages. To exit press CTRL+C')

	channel.exchange_declare(exchange='syncQ', exchange_type='fanout')

	result = channel.queue_declare(queue='', exclusive=True)
	queue_name = result.method.queue

	channel.queue_bind(exchange='syncQ', queue=queue_name)
	def update_new_slave():
		conn = sqlite3.connect('try.db')
		pass_url="http://orchestrator:5000/api/v1/db/sync"
		r=requests.get(url=pass_url)
		resp=r.text
		resp=json.loads(resp)
		for i in resp:
			print("in loop..",i)
			query=i[0]
			print("Query stored...\t",query)
			r = conn.cursor()
			r.execute(query)
			conn.commit()

		print("done")
		command="SELECT * FROM rides"
		res = conn.cursor()
		res.execute(command)
		conn.commit()
		print("CONTENTS OF THE TABLE...\n",res.fetchall())
		return 0

	def UpdateDb(body):
		print(" [x] Received %r" % body)
		table=json.loads(body)["table"]
		cond=json.loads(body)["cond"]
		vals=json.loads(body)["vals"]
		check=json.loads(body)["check"]

		
		if(check=="delete"):
			command="DELETE FROM "+table+" WHERE "+cond
		if(check =="insert"):
			command="INSERT INTO "+table+" VALUES "+vals
		if(check=="update"):
			command=" UPDATE "+table+" SET "+vals+" WHERE "+cond
		print("Command:", command)
		conn = sqlite3.connect('try.db')
		r = conn.cursor()
		r.execute(command)
		conn.commit()

		print(" [x] Done")
		print(" [x] Update Db")

	update_new_slave()

	def callback_read(ch, method, props, body):
		print(" [x] Received %r" % body)
		
		table=json.loads(body)["table"]
		columns=json.loads(body)["columns"]
		where=json.loads(body)["where"]
		if(where==""):
			command="SELECT "+columns+" FROM "+table
		else:
			command="SELECT "+columns+" FROM "+table+" WHERE "+where
		print(command)

		conn = sqlite3.connect('try.db')
		r = conn.cursor()
		r.execute(command)
		conn.commit()
		res=r.fetchall()
		row_headers = [description[0] for description in r.description]
		my_response=[]
		#res is your row data
		#row_headers is the headers for the data
		for i in range(len(res)):
			
			response_dict={}
			for j in range(len(row_headers)):

				
				if(row_headers[j] is 'time_stamp'):
					k=datetime.datetime.strftime(res[i][j],"%d-%m-%Y:%S-%M-%H")
					response_dict[row_headers[j]]=k
				response_dict[row_headers[j]]=res[i][j]
				
			my_response.append(response_dict)
		
		
		print("Type of data sent as response ",json.dumps(my_response),type(json.dumps(my_response)))

		
		channel.basic_publish(exchange='',
						 routing_key=props.reply_to,
						 properties=pika.BasicProperties(correlation_id = props.correlation_id,
							delivery_mode=2,),
						 body=json.dumps(my_response))
		print(" [x] Done")
		channel.basic_ack(delivery_tag=method.delivery_tag)



	channel.basic_qos(prefetch_count=1)
	channel.basic_consume(queue='read_queue', on_message_callback=callback_read)
	print(" [x] Awaiting RPC requests")

	def callback_sync(ch, method, properties, body):
		print(' [*] got data in syncQ')
		UpdateDb(body)

	   

	channel.basic_consume(
		queue=queue_name, on_message_callback=callback_sync, auto_ack=True)

	channel.start_consuming()

elif(os.environ['NODE_ENV']=="MASTER"):

	print("IN MASTER")
	connection = pika.BlockingConnection(
	pika.ConnectionParameters(host='rmq'))
	channel = connection.channel()

	channel.queue_declare(queue='write_queue', durable = True)
	channel.exchange_declare(exchange='syncQ', exchange_type='fanout')
	
	def create_connection(db_file):
		conn = None
		try:
			conn = sqlite3.connect(db_file)
			return conn
		except Error as e:
			print(e)

		return conn


	def create_table(conn, create_table_sql):
		""" create a table from the create_table_sql statement
		:param conn: Connection object
		:param create_table_sql: a CREATE TABLE statement
		:return:
		"""
		try:
			c = conn.cursor()
			c.execute(create_table_sql)
		except Error as e:
			print(e)

	database = r"try.db"

	sql_create_users_table = """ CREATE TABLE IF NOT EXISTS userdata (
										uname text NOT NULL,
										pwd text NOT NULL,
										created_ride text
									); """
	
	sql_create_rides_table = """CREATE TABLE IF NOT EXISTS rides (
								rideId integer NOT NULL,
								created_by text,
								passengers text,
								source text,
								dest text,
								time_stamp timestamp
							);"""
							



	# create a database connection
	conn = create_connection(database)

	# create tables
	if conn is not None:
		# create projects table
		create_table(conn, sql_create_users_table)

		# create tasks table
		create_table(conn, sql_create_rides_table)
	else:
		print("Error! cannot create the database connection.")

	def callback(ch, method, properties, body):
		print(" [x] Received %r" % body)

		table=json.loads(body)["table"]
		cond=json.loads(body)["cond"]
		vals=json.loads(body)["vals"]
		check=json.loads(body)["check"]

		'''if(check=="delete"):
			# print(where)
			if(cond==""):
				command = "DELETE FROM "+table
			else:
				command="DELETE FROM "+table+" WHERE "+cond
			# command="DELETE FROM "+table+" WHERE "+cond
		if(check =="insert"):
			command="INSERT INTO "+table+" VALUES "+vals
		if(check=="update"):
			command=" UPDATE "+table+" SET "+vals+" WHERE "+cond
		print("hi")
		r= db.execute(command)'''
		if(check=="delete"):
			command="DELETE FROM "+table+" WHERE "+cond
		if(check =="insert"):
			command="INSERT INTO "+table+" VALUES "+vals
		if(check=="update"):
			command=" UPDATE "+table+" SET "+vals+" WHERE "+cond
		print("Command:", command)
		conn = sqlite3.connect('try.db')
		r = conn.cursor()
		r.execute(command)
		conn.commit()
		print(" [x] Done")
		channel.basic_publish(exchange='syncQ', routing_key='', body=body)
		print(" [x] Sent data to syncQ")
		ch.basic_ack(delivery_tag=method.delivery_tag)



	channel.basic_consume(queue='write_queue', on_message_callback=callback)

	print(' [*] Waiting for messages. To exit press CTRL+C')
	channel.start_consuming()

		
	
