#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt
python manage.py makemigrations store
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py seed_data
