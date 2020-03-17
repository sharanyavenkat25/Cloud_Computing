FROM python
ADD . /users
WORKDIR /users
RUN pip install -r requirements.txt
EXPOSE 80
CMD ["python3", "users.py"]
