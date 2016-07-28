
#_____________________________Import Kombu classes_____________________________
from kombu import Exchange, Queue

#___________________________CELERY_TIMEZONE & Misc.____________________________
CELERY_TIMEZONE = 'Asia/Taipei'
CELERYD_POOL_RESTARTS = True

#__________________________________BROKER_URL__________________________________
BROKER_URL = 'redis://weilin.noip.me:6379/0'

#____________________________CELERY_RESULT_BACKEND_____________________________
CELERY_RESULT_BACKEND = 'redis://weilin.noip.me:6379/1'

#________________________________CELERY_IMPORTS________________________________
CELERY_IMPORTS = ('IoT.neuron',)

#________________________________CELERY_QUEUES_________________________________
CELERY_QUEUES = (
    Queue('neuron_x', Exchange('celery', type = 'direct'), routing_key='neuron_x'),
    Queue('neuron_y', Exchange('celery', type = 'direct'), routing_key='neuron_y'),
    Queue('neuron_h1', Exchange('celery', type = 'direct'), routing_key='neuron_h1'),
    Queue('neuron_h2', Exchange('celery', type = 'direct'), routing_key='neuron_h2'),
    Queue('neuron_h3', Exchange('celery', type = 'direct'), routing_key='neuron_h3'),
    Queue('neuron_z', Exchange('celery', type = 'direct'), routing_key='neuron_z'),
)


#_______________________________Workers Scripts________________________________
#[Node - localhost] : celery -A IoT worker -n worker1.%h -Q neuron_x --concurrency=1 --loglevel=INFO
#[Node - localhost] : celery -A IoT worker -n worker1.%h -Q neuron_y --concurrency=1 --loglevel=INFO
#[Node - localhost] : celery -A IoT worker -n worker1.%h -Q neuron_h1 --concurrency=1 --loglevel=INFO
#[Node - localhost] : celery -A IoT worker -n worker1.%h -Q neuron_h2 --concurrency=1 --loglevel=INFO
#[Node - localhost] : celery -A IoT worker -n worker1.%h -Q neuron_h3 --concurrency=1 --loglevel=INFO
#[Node - localhost] : celery -A IoT worker -n worker1.%h -Q neuron_z --concurrency=1 --loglevel=INFO

#____________________________________FLOWER____________________________________
#[Flower] : celery -A IoT flower
