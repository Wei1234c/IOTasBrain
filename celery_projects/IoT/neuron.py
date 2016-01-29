# https://en.wikipedia.org/wiki/Neuron
# https://en.wikipedia.org/wiki/Action_potential
# https://en.wikipedia.org/wiki/Artificial_neuron
# https://en.wikipedia.org/wiki/Neural_coding

from celery import group
from IoT.celery import app 
import pickle
import os
import datetime

DEBUG = True
CONFIG_FILE = os.path.join(os.environ['HOME'], 'neuron.cfg')
LOG_FILE = os.path.join(os.environ['HOME'], 'neuron.log')
INITIAL_WEIGHT = 0
ACTION_POTENTIAL = 1
RESTING_POTENTIAL = 0
# LASTING_SECONDS = 0.5
POLARIZATION_SECONDS = 0.5
REFRACTORY_PERIOD = 0.1
# ABSOLUTE_REFRACTORY_PERIOD = 0.5


@app.task
def getHostname():
    return os.environ['HOSTNAME'] if 'HOSTNAME' in os.environ else os.environ['COMPUTERNAME']

    
# @app.task
def pickleDump(content, fileName):        
    with open(fileName, 'wb') as f:
        pickle.dump(content, f)

        
# @app.task  
def pickleLoad(fileName):     
    with open(fileName, 'rb') as f:
        return pickle.load(f) 
        

# @app.task    
def touchFiles():    
    if not os.path.exists(CONFIG_FILE): emptyConfig()
    if not os.path.exists(LOG_FILE): emptyLog()

    
@app.task
def emptyConfig():
    config = {}
    config['inputs'] = {}
    config['output'] = {'value': RESTING_POTENTIAL, 'depolarized_time': datetime.datetime(1970,1,1), 'lasting': datetime.timedelta(0, REFRACTORY_PERIOD)}
    setConfig(config)
    
    
@app.task
def emptyLog():
    content = []
    setLog(content)
    
    
@app.task
def setConfig(content):        
    pickleDump(content, CONFIG_FILE)
    
    
# @app.task
def setLog(content):        
    pickleDump(content, LOG_FILE)
    
        
@app.task  
def getConfig():
    touchFiles()        
    return pickleLoad(CONFIG_FILE)
    
        
@app.task  
def getLog():
    touchFiles()        
    return pickleLoad(LOG_FILE)
    
    
# @app.task  
def log(message):
    content = getLog()
    content.append((datetime.datetime.now(), getHostname(), message))
    setLog(content)
    
    
@app.task
def setConnections(connections):
    config = getConfig()
    config['connections'] = connections
    setConfig(config)


@app.task    
def getConnections():
    return getConfig().get('connections', set())

    
@app.task
def addConnection(neuron_id):
    connections = getConnections()
    connections.add(neuron_id) 
    setConnections(connections)


@app.task    
def deleteConnection(neuron_id):
    connections = getConnections()
    connections.remove(neuron_id) 
    setConnections(connections)


@app.task    
def setWeights(weights):
    config = getConfig()
    config['weights'] = weights
    setConfig(config)


@app.task    
def getWeights():
    return getConfig().get('weights', {})


@app.task    
def setWeight(neuron_id, weight):
    weights = getWeights()
    weights[neuron_id] = weight
    setWeights(weights)


@app.task    
def getWeight(neuron_id):
    return getWeights().get(neuron_id, INITIAL_WEIGHT)


@app.task    
def deleteWeight(neuron_id):
    weights = getWeights()
    del weights[neuron_id]
    setWeights(weights)


@app.task    
def setThreshold(threshold):
    config = getConfig()
    config['threshold'] = threshold 
    setConfig(config)


@app.task    
def getThreshold():
    return getConfig().get('threshold', float("inf"))
    
    
# @app.task
def in_refractory_period():
    output = getConfig()['output'] 
    
    # 如果 output 還沒有超過有效期
    return True if output['depolarized_time'] + output['lasting'] >= datetime.datetime.now() else False
    
    
# @app.task    
def sumInputsAndWeights():  
    config = getConfig()
    weights = config.get('weights', {})
    inputs = config.get('inputs', {})
    sum_of_weighted_inputs = 0
    
    # sum weighted inputs
    for neuron in inputs:
        input = inputs[neuron]        
        # 如果input還沒有超過有效期
        input['value'] = ACTION_POTENTIAL if input['kick_time'] + input['lasting'] >= datetime.datetime.now() else RESTING_POTENTIAL        
        sum_of_weighted_inputs += input['value'] * weights.get(neuron, INITIAL_WEIGHT)
        
    setConfig(config)
    
    return sum_of_weighted_inputs


@app.task
def getOutput():
    return ACTION_POTENTIAL if in_refractory_period() else RESTING_POTENTIAL
    

@app.task
def kick(neuron_id): 
    # 紀錄 input 的狀態
    myName = getHostname()
    log('{0} is kicking {1}.'.format(neuron_id, myName))
    config = getConfig()
    config['inputs'][neuron_id] = {'value': ACTION_POTENTIAL, 'kick_time': datetime.datetime.now(), 'lasting': datetime.timedelta(0, POLARIZATION_SECONDS)}
    setConfig(config)    
    
    if not in_refractory_period():
        # output 已經歸零        
        if sumInputsAndWeights() >= getThreshold():
            fire() 
    else:
        # output 尚未歸零
        log('{0} is still in refractory_period.'.format(myName))
        pass
 
 
@app.task    
def fire():    
    # 設定 output 為 ACTION_POTENTIAL
    config = getConfig()
    config['output']['value'] = ACTION_POTENTIAL
    config['output']['depolarized_time'] = datetime.datetime.now()
    # config['output']['lasting'] = datetime.timedelta(0, REFRACTORY_PERIOD)}
    setConfig(config) 
    
    myName = getHostname()
    log('{0} fired.'.format(myName))
    # kick 下游 neurons
    connections = getConnections()        
    group([kick.subtask((myName,), routing_key = connection) for connection in connections]).apply_async()