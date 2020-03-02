FROM python
ADD . /users
WORKDIR /users
RUN pip install -r requirements.txt
EXPOSE 8080 
CMD ["python3", "users.py"]
