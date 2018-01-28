#!/bin/bash

nohup locust -f locust_test.py --host=http://localhost:5000 &
python app.py