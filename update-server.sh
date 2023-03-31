# check we are in /tracet
cd /home/ubuntu/tracet
# update git repo
git pull
# Stop server
uwsgi --stop /tmp/project-master.pid

# Check for new dependent software
pip install -r requirements.txt
pip install .
pip install -r webapp_tracet/requirements.txt

cd webapp_tracet

# Check for new static files
python manage.py collectstatic --noinput

# Make any required changes to the backend database
python manage.py makemigrations
python manage.py migrate

# Start server
uwsgi --ini webapp_tracet_uwsgi.ini

# Reset comet and kafka event handlers
tmux kill-server
tmux new -s kafka -d 'python kafka_client.py'
tmux new -s comet -d 'python twistd_comet_wrapper.py'