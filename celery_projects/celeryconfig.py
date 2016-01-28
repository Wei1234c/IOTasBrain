
#_____________________________Import Kombu classes_____________________________
from kombu import Exchange, Queue

#___________________________CELERY_TIMEZONE & Misc.____________________________
CELERY_TIMEZONE = 'Asia/Taipei'
CELERYD_POOL_RESTARTS = True

#__________________________________BROKER_URL__________________________________
BROKER_URL = 'redis://192.168.0.114:6379/0'

#____________________________CELERY_RESULT_BACKEND_____________________________
CELERY_RESULT_BACKEND = 'redis://192.168.0.114:6379/1'

#________________________________CELERY_IMPORTS________________________________
CELERY_IMPORTS = ('IoT.tasks',)

#________________________________CELERY_QUEUES_________________________________
CELERY_QUEUES = (
    Queue('neuron_x', Exchange('celery', type = 'direct'), routing_key='neuron_x'),
    Queue('neuron_y', Exchange('celery', type = 'direct'), routing_key='neuron_y'),
    Queue('neuron_h1', Exchange('celery', type = 'direct'), routing_key='neuron_h1'),
    Queue('neuron_h2', Exchange('celery', type = 'direct'), routing_key='neuron_h2'),
    Queue('neuron_h3', Exchange('celery', type = 'direct'), routing_key='neuron_h3'),
    Queue('neuron_z', Exchange('celery', type = 'direct'), routing_key='neuron_z'),
)
