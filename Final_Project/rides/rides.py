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
	# create users table
	#create_table(conn, sql_create_users_table)

	# create rides table
	create_table(conn, sql_create_rides_table)
else:
	print("Error! cannot create the database connection.")

app=Flask(__name__)

def myCounterfunc():
	global mycounter
	mycounter = mycounter+ 1

@app.before_request
def incrementcounter():
	if request.path not in ('/', '/api/v1/_count', '/api/v1/db/write', '/api/v1/db/read', '/api/v1/db/clear'):
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




#1)Create Ride
@app.route('/api/v1/rides',methods=["POST"])

def create_ride():
	if not request.json:
		abort(400,description="Mention userdetails in request")
	source=request.get_json()["source"]
	dest=request.get_json()["destination"]
	time_stamp=request.get_json()["timestamp"]
	f='%d-%m-%Y:%S-%M-%H'
	time_obj=datetime.datetime.strptime(time_stamp,f)
	u_name=request.get_json()["created_by"]
	vd=0
	vs=0
	with open("AreaNameEnum.csv") as obj:
		for row in obj:
			row=row.split(",")
			if row[0]== source:
				vs=1
			if row[0]==dest:
				vd=1
	if(vd==1 and vs==1 and source!=dest):
		headers={'origin':'52.87.95.202'} 
		pass_data={"table":"userdata","columns":"*","where":"uname="+"'"+str(u_name)+"'"}
		pass_api="http://ridesharelb-397737146.us-east-1.elb.amazonaws.com/api/v1/users" 
		
		r=requests.get(url=pass_api,json=pass_data, headers=headers)
		resp=r.text
		#resp=json.loads(resp)
		ridelist = list()
		for i in range(10000):
			ridelist.append(i)
		rideId=random.sample(ridelist,1)
		print("response to check if user exists...",resp)
		#if user doesnt exist
		if(u_name not in resp):
			abort(400,description="user doesnt exist")
		else:
			pass_data={"table":"rides(rideId,created_by,passengers,source,dest,time_stamp)",
						"cond":"",
						"vals":"("+"'"+str(rideId[0])+"'"+","+"'"+str(u_name)+"'"+","+"'"+str(u_name)+"'"+","+"'"+str(source)+"'"+","+"'"+str(dest)+"'"+","+"'"+str(time_obj)+"'"+")",
						"check":"insert"}
			
			headers={'origin':'52.87.95.202'} 
			pass_api="http://"+dbaasip+":80/api/v1/db/write"
			r=requests.post(url=pass_api,json=pass_data,headers=headers)
			return Response("{}",status=201,mimetype='application/json')
	else:
		abort(400,description="Source and Destination are the same, or are invalid")


#4) prints data about upcoming rides
@app.route('/api/v1/rides',methods=["GET"])
def details_upcoming():
	source = request.args.get('source')
	dest = request.args.get('destination')
	vd=0
	vs=0
	with open("AreaNameEnum.csv") as obj:
		for row in obj:
			row=row.split(",")
			if row[0]== source:
				vs=1
			if row[0]==dest:
				vd=1
	
	pass_api="http://"+dbaasip+":80/api/v1/db/read"
	headers={'origin':'52.87.95.202'}
		#pass_api="http://localhost:5000/api/v1/db/read/"
	pass_data={"columns":"rideid,created_by,time_stamp","table":"rides","where":"source=" + "'"+str(source)+"'" + "" + " and " + "dest=""'" + str(dest) + "'" + " and " + "time_stamp >" + "CURRENT_TIMESTAMP"}
	res=requests.post(url=pass_api,json=pass_data, headers=headers)
	resp=res.text
	resp=json.loads(resp)
	if(len(resp)==0):
		if(vd!=1 or vs!=1 or source==dest):
			abort(400,description="Source and Destination are the same, or are invalid")
		else:
			return Response("No content to show",status=204,mimetype='application/json')
	r=[]
		
		#print("PRINTING FROM API UPCOMING..\n",resp)
	for row in resp:
			
		d=OrderedDict() 
		d['rideid']=row['rideId']
		d['username']=row['created_by']
		d['time_stamp']=row['time_stamp']
		r.append(d)


		# return Response(jsonify(r),status=200,mimetype='application/json')
	return jsonify(r)
	#else:
		#abort(400,description="Source and Destination are the same, or are invalid")

#5) Details of a given ride
@app.route('/api/v1/rides/<rideId>', methods=["GET"])
def  ride_details(rideId):
	pass_data={"table":"rides","columns":"rideid, created_by, source, dest, time_stamp, passengers","where":"rideid="+rideId}
	#pass_api="http://localhost:5000/api/v1/db/read/"
	pass_api="http://"+dbaasip+":80/api/v1/db/read"
	headers={'origin':'52.87.95.202'} 
	res=requests.post(url=pass_api,json=pass_data, headers=headers)
	resp=res.text
	resp=json.loads(resp)
	
	if(len(resp)==0):
		abort(400,description="rideID does not exist")
	
	r=list()
	passengers_list = []
	for row in resp:
		passengers_list.append(row['passengers'])
	for row in resp:
		print("Row in resp:", row)
		d=OrderedDict()
		d['rideID']=row['rideId']
		d['Created_by']=row['created_by']
		d['Timestamp']=row['time_stamp']
		d['Source']=row['source']
		d['Destination']=row['dest']
		d['Timestamp']=str(d['Timestamp'])
		d['Users'] = passengers_list
		# print(d)
		r.append(d)
		break
	return jsonify(r)
	# return Response(jsonify(r),status=200,mimetype='application/json')

#6) join an existing ride
@app.route('/api/v1/rides/<rideId>', methods=["POST"])
def join_existing_ride(rideId):
	u_name=request.get_json()["username"]
	"""
	To check if rideid and uname is valid
	query="select rideid from rides where rideid=rideid"
	query="select uname from userdata where uname=uname"
	"""
	headers={'origin':'52.87.95.202'} 
	pass_data={"table":"userdata","columns":"uname","where":"uname="+"'"+str(u_name)+"'"}
	#pass_api="http://users:80/api/v1/db/read/"
	pass_api="http://ridesharelb-397737146.us-east-1.elb.amazonaws.com/api/v1/users"
	
	r1=requests.get(url=pass_api,json=pass_data, headers=headers)
	resp1=r1.text
	#resp1=json.loads(resp1)
	# print("hello")
	
	pass_data={"table":"rides","columns":"rideid","where":"rideid="+"'"+rideId+"'"}
	#pass_api="http://localhost:5000/api/v1/db/read/"
	
	pass_api="http://"+dbaasip+":80/api/v1/db/read"
	r2=requests.post(url=pass_api,json=pass_data, headers=headers)
	resp2=r2.text
	resp2=json.loads(resp2)
	if(u_name not in resp1):
		print("hello")
		abort(400,description="user does not exist")
	if(len(resp2)==0):
		print("hello")
		abort(400,description="rideID does not exist")
	'''pass_data={"table":"rides","columns":"passengers","where":"rideid="+"'"+str(rideId)+"'"}
							pass_api="http://localhost:5000/api/v1/db/read/"
							r=requests.post(url=pass_api,json=pass_data)
							dup=r.text
							dup=json.loads(dup)
							# print(dup)
							existing_pas = dup[0]['passengers']'''
	'''if u_name not in existing_pas:
						 
				#query="update rides set passengers = array_cat(topics, '{uname}' where rideid=rideid);"
					pass_data={"table":"rides",
								"cond":"rideid="+rideId,
								"vals":"passengers=array_cat(passengers,"+"'{"+u_name+"}'"+")",
								"check":"update"}
					pass_api="http://localhost:5000/api/v1/db/write/"
					r=requests.post(url=pass_api,json=pass_data)
					return Response("{}",status=200,mimetype='application/json')
				else:
					print("you're already part of the ride")'''
	#step 1 : retrieve ride details of given ride id
	pass_data={"table":"rides","columns":"rideid, created_by, source, dest, time_stamp, passengers","where":"rideid="+rideId}
	#pass_api="http://localhost:5000/api/v1/db/read/"
	pass_api="http://"+dbaasip+":80/api/v1/db/read"
	res=requests.post(url=pass_api,json=pass_data, headers=headers)
	resp=res.text
	resp=json.loads(resp)
	passengers_list = []
	for row in resp:
		passengers_list.append(row['passengers'])
	if u_name not in passengers_list:
		pass_data={"table":"rides","columns":"*","where":"rideid="+"'"+str(rideId)+"'"}
		pass_api="http://"+dbaasip+":80/api/v1/db/read"
		#pass_api="http://localhost:5000/api/v1/db/read/"
		r=requests.post(url=pass_api,json=pass_data, headers=headers)
		dup=r.text
		dup=json.loads(dup)
		for i in dup:
			#print("THIS IS I : ", i)
			created_by= i["created_by"]
			src = i["source"]
			dest = i["dest"]
			time_obj=i["time_stamp"]
		pass_data={ "table":"rides",
					"cond":"",
					"vals":"("+"'"+str(rideId)+"'"+","+"'"+str(created_by)+"'"+","+"'"+str(u_name)+"'"+","+"'"+str(src)+"'"+","+"'"+str(dest)+"'"+","+"'"+str(time_obj)+"'"+")",
					"check":"insert"}
		#pass_api="http://localhost:5000/api/v1/db/write/"
		pass_api="http://"+dbaasip+":80/api/v1/db/write"
		r=requests.post(url=pass_api,json=pass_data, headers=headers)
	else:
		print("you're already part of the ride")

	
	#return Response("{}",status=200,mimetype='application/json')



	return Response("{}",status=200,mimetype='application/json')
	




#new - count number of rides
@app.route('/api/v1/rides/count', methods=["GET"])
def count_rides():
	res=[]
	pass_data={"table":"rides","columns":"rideId","where":"1=1"}
	n=0
	#headers={'origin':'52.87.95.202'}
	pass_api="http://"+dbaasip+":80/api/v1/db/read"
	headers= {'origin':'52.87.95.202'}
	r=requests.post(url=pass_api,json=pass_data, headers=headers)
	resp=r.text
	
	resp=json.loads(resp)
	unique=[]
	for row in resp:
		unique.append(row["rideId"])
	unique_set = set(unique)
	res.append(len(unique_set))
	return jsonify(res)
	#,status=200,mimetype='application/json')

#7. Delete a ride 

@app.route('/api/v1/rides/<rideId>', methods=["DELETE"])
def del_ride(rideId):

	

	headers={'origin':'52.87.95.202'} 
	pass_data={"table":"rides","columns":"*","where":"rideid="+rideId}
	#pass_api="http://localhost:5000/api/v1/db/read/"
	pass_api="http://"+dbaasip+":80/api/v1/db/read"
	r=requests.post(url=pass_api,json=pass_data, headers=headers)
	resp=r.text
	resp=json.loads(resp)

	if(len(resp)>0):

		
		pass_data={"table":"rides",
				   "cond":"rideid="+"'"+rideId+"'",
				   "vals":"",
				   "check":"delete"}
		#pass_api="http://localhost:5000/api/v1/db/write/"
		pass_api="http://"+dbaasip+":80/api/v1/db/write"
		r=requests.post(url=pass_api,json=pass_data, headers=headers)
		return Response("{}",status=200,mimetype='application/json')
	else:

		return Response("{}",status=400,mimetype='application/json')


@app.route("/api/v1/db/clear",methods=["POST"])
def clear_db():
	headers={'origin':'52.87.95.202'}
	pass_api="http://"+dbaasip+":80/api/v1/db/clear"
	r = requests.post(url=pass_api, headers=headers)
	return Response("{}", status=200, mimetype='application/json')

if __name__ == '__main__':
	global mycounter
	mycounter = 0  
	app.debug=True
	app.run(host='0.0.0.0',port=80)
