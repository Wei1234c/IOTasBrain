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
    config['output'] = {'value': RESTING_POTENTIAL, 'polarized_time': datetime.datetime(1970,1,1), 'lasting': datetime.timedelta(0, REFRACTORY_PERIOD)}
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
    logs = getLog()
    logs.append((datetime.datetime.now(), getHostname(), message))
    setLog(logs)
    
    
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
    return True if output['polarized_time'] + output['lasting'] >= datetime.datetime.now() else False
    
    
# @app.task    
def sumInputsAndWeights():  
    config = getConfig()
    weights = config.get('weights', {})
    inputs = config.get('inputs', {})
    sum_of_weighted_inputs = 0
    currentTime = datetime.datetime.now()
    
    # sum weighted inputs
    for neuron in inputs:
        input = inputs[neuron]        
        # 如果input還沒有超過有效期
        input['value'] = input.get('value', ACTION_POTENTIAL) if input['kick_time'] + input['lasting'] >= currentTime else RESTING_POTENTIAL        
        sum_of_weighted_inputs += input['value'] * weights.get(neuron, INITIAL_WEIGHT)
        
    setConfig(config)
    
    return sum_of_weighted_inputs


@app.task
def setOutput(potential):
    # 設定 output 為 potential
    config = getConfig()
    config['output']['value'] = potential
    config['output']['polarized_time'] = datetime.datetime.now()
    # config['output']['lasting'] = datetime.timedelta(0, REFRACTORY_PERIOD)}
    setConfig(config)
    

@app.task
def setOutputActive():
    log('Setting output of {0} to ACTION_POTENTIAL.'.format(getHostname()))
    setOutput(ACTION_POTENTIAL)


# @app.task
# def setOutputResting():
    # log('Setting output of {0} to RESTING_POTENTIAL.'.format(getHostname()))
    # setOutput(RESTING_POTENTIAL)
    
    
@app.task
def getOutput():
    if in_refractory_period():
        output = getConfig()['output'].get('value', RESTING_POTENTIAL)
    else:
        output = RESTING_POTENTIAL        
    return output
    
    
@app.task
def receiveInput(neuron_id): 
    # 紀錄 input 的狀態     
    config = getConfig() 
    inputs = config.get('inputs', {})  
    input = inputs.get(neuron_id)
    
    # 收到 input 的時間
    currentTime = datetime.datetime.now()
    
    # 尚無紀錄，則 initialize
    if input is None:
        input = {}
        input['value'] = RESTING_POTENTIAL
        input['kick_time'] = currentTime
        input['lasting'] = datetime.timedelta(0, POLARIZATION_SECONDS)
        inputs[neuron_id] = input
    
    remainingValue = input['value'] if input['kick_time'] + input['lasting'] >= currentTime else RESTING_POTENTIAL  # 上一次 input 的殘餘值
    input['value'] = remainingValue + ACTION_POTENTIAL  # 同一個來源 累積的效果
    input['kick_time'] = currentTime
    input['lasting'] = datetime.timedelta(0, POLARIZATION_SECONDS)
    setConfig(config) 
    
    
@app.task
def kick(neuron_id): 
    myName = getHostname()
    log('{0} is kicking {1}.'.format(neuron_id, myName))     
    
    # 紀錄 input 的狀態
    receiveInput(neuron_id)    
    
    sum_of_weighted_inputs = sumInputsAndWeights()
    threshold = getThreshold()    
    currentOutput = getOutput()
    
    if not in_refractory_period():
        # refractory period 已經過了，需重新估算        
        if sum_of_weighted_inputs >= threshold:
            fire() 
    else: 
        # 還在 refractory period 期間 
        log('{0} is still in refractory-period.'.format(myName))
        if currentOutput == ACTION_POTENTIAL:
            # 目前在 ACTION_POTENTIAL
            if sum_of_weighted_inputs >= threshold:
                log('{0} is still in refractory_period at action potential, then a neuron {1} kicks in, now sum_of_weighted_inputs >= threshold.'.format(myName, neuron_id))
            else:                
                log('{0} is still in refractory_period at action potential, then a neuron {1} kicks in, now sum_of_weighted_inputs < threshold.'.format(myName, neuron_id))
                # setOutputResting()
        else: 
            # 目前在 RESTING_POTENTIAL
            if sum_of_weighted_inputs >= threshold:
                log('{0} is still in refractory_period at resting potential, then a neuron {1} kicks in, now sum_of_weighted_inputs >= threshold.'.format(myName, neuron_id))
            else:                
                log('{0} is still in refractory_period at resting potential, then a neuron {1} kicks in, now sum_of_weighted_inputs < threshold.'.format(myName, neuron_id))
                # setOutputResting()
                
                
@app.task    
def fire():    
    myName = getHostname()
    log('{0} fires.'.format(myName))
    setOutputActive()  
    
    # kick 下游 neurons
    connections = getConnections()        
    group([kick.subtask((myName,), routing_key = connection) for connection in connections]).apply_async()