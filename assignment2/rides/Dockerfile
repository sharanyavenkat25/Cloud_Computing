FROM python
ADD . /rides
WORKDIR /rides
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["python3", "rides.py"]
