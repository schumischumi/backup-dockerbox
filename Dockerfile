FROM python:3.10

WORKDIR /code

COPY ./requirements/requirements.txt /code/requirements.txt

RUN /usr/local/bin/python -m pip install --upgrade pip 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
RUN rm -rf /code/requirements.txt

COPY ./app /code

CMD [ "python", "./app.py" ]
