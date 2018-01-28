FROM python:3.6.4-stretch
ADD . /code
WORKDIR /code
RUN pip install flask redis python-igraph locustio
RUN pip install --user git+https://github.com/pygobject/pycairo.git
CMD /bin/sh start.sh
