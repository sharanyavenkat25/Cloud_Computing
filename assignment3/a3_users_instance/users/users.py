

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
PUBLIC_URL='3.218.239.57'
# Scheme: "postgres+psycopg2://<USERNAME>:<PASSWORD>@<IP_ADDRESS>:<PORT>/<DATABASE_NAME>"
DATABASE_URI = 'postgresql+psycopg2://postgres:postgres@db:5432/postgres'
db = create_engine(DATABASE_URI)
db.execute("CREATE TABLE IF NOT EXISTS userdata (uname text, pwd text, created_ride text)")
#db.execute("CREATE TABLE IF NOT EXISTS rides (rideId INT,created_by text,passengers text[],source text, dest text, time_stamp timestamp)")
r=db.execute("SELECT * from userdata")
print(r.fetchall())
#print("before app")
app=Flask(__name__)
#print("after app")


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


#1)Add user
@app.route('/api/v1/users',methods=["PUT"])
def add_user():
	print("Reached PUT /users")
	if not request.json:
		abort(400,description="Mention userdetails in request")
		
	u_name=request.get_json()["username"]
	u_pwd=request.get_json()["password"]
	headers={"origin":'3.218.239.57'}
	pass_data={"table":"userdata","columns":"uname,pwd,created_ride","where":"uname="+"'"+str(u_name)+"'"}
	pass_api="http://users:80/api/v1/db/read/"
	r=requests.post(url=pass_api,json=pass_data)
	resp=r.text
	resp=json.loads(resp)
	

	pattern = re.compile(r'\b[0-9a-fA-F]{40}\b')
	match = re.match(pattern,u_pwd)

	# tests for pwd to be in sha1
	if(type(match)== type(None)):
		abort(400,description="Password not in SHA1 form")
	#tests for unique
	if(len(resp) > 0 ):
		return Response("User Already Exists",status=400, mimetype='application/json') #LOOK AGAIN!!!
	else:
		# db.execute("INSERT INTO userdata (uname,pwd,created_ride) VALUES (%s,%s,%s)",u_name,u_pwd,"N")
		pass_data={"table":"userdata (uname,pwd,created_ride)","cond":"",
					"vals":"("+"'"+str(u_name)+"'"+","+"'"+str(u_pwd)+"'"+","+"'N'"+")",
					"check":"insert"}
		pass_api="http://users:80/api/v1/db/write/"
		r=requests.post(url=pass_api,json=pass_data)
		return Response("{}",status=201,mimetype='application/json')

#2)Remove User
@app.route('/api/v1/users/<username>',methods=["DELETE"])
def remove_user(username):
	print("i am here")
	pass_data={"table":"userdata","columns":"*","where":"uname="+"'"+str(username)+"'"}
	pass_api=" http://users:80/api/v1/db/read/"
	r=requests.post(url=pass_api,json=pass_data)
	resp=r.text
	resp=json.loads(resp)
	if(len(resp)==0):
		abort(400,description="User does not exist")
	else:
		pass_data={"table":"rides",
					"columns":"created_by",
					"where":"created_by="+"'"+str(username)+"'"}
		pass_api="http://rideshareApp-948913955.us-east-1.elb.amazonaws.com/api/v1/db/read/"
		headers={"origin":'3.218.239.57'}
		r=requests.post(url=pass_api,json=pass_data,headers=headers)
		resp1=r.text
		resp1=json.loads(resp1)
		if(len(resp1)>0):
			abort(400,description="Cannot Delete User")
		else:
			pass_data={"table":"userdata",
						"cond":"uname="+"'"+str(username)+"'",
						"vals":"",
						"check":"delete"}
			pass_api="http://users:80/api/v1/db/write/"
			r=requests.post(url=pass_api,json=pass_data)


			pass_data_update={"table":"rides",
				"cond":"1=1",
				"vals":"passengers=array_remove(passengers,"+"'"+username+"'"+")",
				"check":"update"}
			pass_api_update="http://rideshareApp-948913955.us-east-1.elb.amazonaws.com/api/v1/db/write/"
			r=requests.post(url=pass_api_update,json=pass_data_update)
			return Response("{}",status=200 , mimetype='application/json')

#List all users
@app.route('/api/v1/users', methods=["GET"])
def get_users():
	pass_data={"table":"userdata","columns":"uname","where":""}
	pass_api="http://users:80/api/v1/db/read/"
	
	res=requests.post(url=pass_api,json=pass_data)
	resp=res.text
	resp=json.loads(resp)
	if(len(resp)==0):
		return Response("No content to show",status=204,mimetype='application/json')
	r = list()
	for row in resp:
		r.append(row['uname'])
	return jsonify(r)

#9. Read from db

@app.route('/api/v1/db/read/', methods=["POST"])
def read_db():
	table=request.get_json()["table"]
	columns=request.get_json()["columns"]
	where=request.get_json()["where"]
	if(where==""):
		command="SELECT "+columns+" FROM "+table
	else:
		command="SELECT "+columns+" FROM "+table+" WHERE "+where
	
	r= db.execute(command)
	res=r.fetchall()
	row_headers=r.keys()
	json_data=[]
	
	for result in res:
		d = dict(result.items())
		if("time_stamp" in row_headers):
			k=datetime.datetime.strftime(d['time_stamp'],"%d-%m-%Y:%S-%M-%H")
			d['time_stamp']=k
		json_data.append(d)
		
	return jsonify(json_data)

#8) Write to db

@app.route('/api/v1/db/write/', methods=["POST"])
def write_db():
	table=request.get_json()["table"]
	cond=request.get_json()["cond"]
	vals=request.get_json()["vals"]
	check=request.get_json()["check"]

	if(check=="delete"):
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
	
	r= db.execute(command)
	return Response("{}",status=200,mimetype='application/json')

#11. Clearing the database
@app.route('/api/v1/db/clear', methods=["POST"])
def clear_db():
	pass_data1={"table":"userdata",
				   "cond":"",
				   "vals":"",
				   "check":"delete"}
	pass_api1="http://users:80/api/v1/db/write/"
	r1=requests.post(url=pass_api1,json=pass_data1)
	resp1=r1.text
	resp1=json.loads(resp1)
	return Response("{}",status=200,mimetype='application/json')


if __name__ == '__main__':
	global mycounter
	mycounter = 0	
	app.debug=True
	app.run(host='0.0.0.0',port=80)

