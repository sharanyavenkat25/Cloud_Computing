FROM python
ADD . /rides
WORKDIR /rides
RUN pip install -r requirements.txt
EXPOSE 80
CMD ["python3", "rides.py"]
