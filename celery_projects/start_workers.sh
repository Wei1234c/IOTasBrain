# ./start_workers.sh

PROJECT='IoT'  # project 名稱
CONCURRENCY=1  # 每個 worker 可以有幾個 subprocesses



echo "Starting Redis, Flower _________________________________________________"
eval $(docker-machine env master01)

docker run -dit -p 6379:6379 --name=redis -v /data:/data hypriot/rpi-redis
docker run -d -p 5555:5555 --name=flower --volume=/data/celery_projects:/celery_projects wei1234c/celery_armv7 /bin/sh -c "cd /celery_projects && celery -A ${PROJECT} flower"



echo "Starting Celery cluster containers _________________________________________________"
eval $(docker-machine env --swarm master01)

for id in 'x' 'y' 'h1' 'h2' 'h3' 'z'
do
  docker run -d --name=neuron_${id} --hostname=neuron_${id} --volume=/data/celery_projects:/celery_projects wei1234c/celery_armv7 /bin/sh -c "cd /celery_projects && celery -A ${PROJECT} worker -n %h -Q neuron_${id} --concurrency=${CONCURRENCY} --loglevel=INFO"
done

