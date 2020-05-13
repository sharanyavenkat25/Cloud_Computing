from flask import Flask, render_template,jsonify,request,abort,Response
from sqlalchemy import create_engine
import re
import datetime
from datetime import datetime
import json
from sqlalchemy.sql import text
from collections import OrderedDict
import requests
import random
import datetime
import sqlite3
from sqlite3 import Error

dbaasip='34.236.79.177'

def create_connection(db_file):
	""" create a database connection to the SQLite database
		specified by db_file
	:param db_file: database file
	:return: Connection object or None
	"""
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



# create a database connection
conn = create_connection(database)

# create tables
if conn is not None:
	# create users table
	create_table(conn, sql_create_users_table)

	# create rides table
	#create_table(conn, sql_create_rides_table)
else:
	print("Error! cannot create the database connection.")

app=Flask(__name__)

def myCounterfunc():
	global mycounter
	mycounter = mycounter+ 1

@app.before_request
def incrementcounter():
	if request.path not in ('/', '/api/v1/_count', '/api/v1/db/write/', '/api/v1/db/read/', '/api/v1/db/clear'):
		myCounterfunc()


@app.route('/api/v1/_count', methods=["GET"])
def count_the_requests():
	r = list()
	total = mycounter
	r.append(total)
	return jsonify(r), 200

@app.route('/api/v1/_count', methods=["DELETE"])
def reset_the_requests():
	global mycounter
	mycounter =0 
	return jsonify({})


#1) Add user

@app.route('/api/v1/users',methods=["PUT"])
def add_user():

	if not request.json:
		abort(400,description="Mention userdetails in request")
	 
	
	u_name=request.get_json()["username"]
	u_pwd=request.get_json()["password"]
	headers={"origin":'3.230.137.46'}
	pass_data={"table":"userdata","columns":"uname,pwd,created_ride","where":"uname="+"'"+str(u_name)+"'"}
	pass_api="http://"+dbaasip+":80/api/v1/db/read"
	r=requests.post(url=pass_api,json=pass_data, headers=headers)
	resp=r.text
	resp=json.loads(resp)
	

	pattern = re.compile(r'\b[0-9a-fA-F]{40}\b')
	match = re.match(pattern,u_pwd)

	# tests for pwd to be in sha1
	if(type(match)== type(None)):
		abort(400,description="Password not in SHA1 form")
	#tests for unique
	if(len(resp) > 0 ):
		return Response("User Already Exists",status=400, mimetype='application/json') 
	else:
		pass_data={"table":"userdata (uname,pwd,created_ride)","cond":"",
					"vals":"("+"'"+str(u_name)+"'"+","+"'"+str(u_pwd)+"'"+","+"'N'"+")",
					"check":"insert"}
		pass_api="http://"+dbaasip+":80/api/v1/db/write"
		r=requests.post(url=pass_api,json=pass_data, headers=headers)
		return Response("{}",status=201,mimetype='application/json')




#2)Remove User

@app.route('/api/v1/users/<username>',methods=["DELETE"])
def remove_user(username):
	
	headers={"origin":'3.230.137.46'}
	pass_data={"table":"userdata","columns":"*","where":"uname="+"'"+str(username)+"'"}
	pass_api="http://"+dbaasip+":80/api/v1/db/read"
	r=requests.post(url=pass_api,json=pass_data, headers=headers)
	resp=r.text
	resp=json.loads(resp)
	if(len(resp)==0):
		abort(400,description="User does not exist")
	else:
		pass_data={"table":"rides",
					"columns":"created_by",
					"where":"created_by="+"'"+str(username)+"'"}
		
		pass_api="http://"+dbaasip+":80/api/v1/db/read"
		r=requests.post(url=pass_api,json=pass_data, headers=headers)
		resp1=r.text
		resp1=json.loads(resp1)
		if(len(resp1)>0):
			abort(400,description="Cannot Delete User")
		else:
			pass_data={"table":"userdata",
						"cond":"uname="+"'"+str(username)+"'",
						"vals":"",
						"check":"delete"}

			pass_api="http://"+dbaasip+":80/api/v1/db/write"
			r=requests.post(url=pass_api,json=pass_data, headers=headers)

			pass_data1={"table":"rides",
						"cond":"passengers="+"'"+str(username)+"'",
						"vals":"",
						"check":"delete"}
			
			pass_api1="http://"+dbaasip+":80/api/v1/db/write"
			r1=requests.post(url=pass_api1,json=pass_data1, headers=headers)


			return Response("{}",status=200 , mimetype='application/json')

#3) List all users
@app.route('/api/v1/users', methods=["GET"])
def get_users():
	pass_data={"table":"userdata","columns":"uname","where":""}
	pass_api="http://"+dbaasip+":80/api/v1/db/read"
	headers={"origin":'3.230.137.46'}
	
	res=requests.post(url=pass_api,json=pass_data, headers=headers)
	resp=res.text
	resp=json.loads(resp)
	if(len(resp)==0):
		return Response("No content to show",status=204,mimetype='application/json')
	r = list()
	for row in resp:
		r.append(row['uname'])
	return jsonify(r)

@app.route("/api/v1/db/clear",methods=["POST"])
def clear_db():
	headers={"origin":'3.230.137.46'}
	pass_api="http://"+dbaasip+":80/api/v1/db/clear"
	r=requests.post(url=pass_api, headers=headers)
	return Response("{}", status=200, mimetype='application/json')

if __name__ == '__main__': 
	global mycounter
	mycounter = 0 
	app.debug=True
	app.run(host='0.0.0.0',port=80)
