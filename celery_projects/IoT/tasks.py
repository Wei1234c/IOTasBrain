from celery import group
from IoT.celery import app 
import pickle
import os
import datetime

DEBUG = True
CONFIG_FILE = os.path.join(os.environ['HOME'], 'IoT_config.pickle')


@app.task
def getHostname():
    return os.environ['HOSTNAME'] if 'HOSTNAME' in os.environ else os.environ['COMPUTERNAME']


@app.task    
def touchFile(file):    
    if not os.path.exists(CONFIG_FILE): emptyConfig()

    
@app.task
def emptyConfig():
    config = {}
    config['output'] = {'value': 0, 'evaluate_time': datetime.datetime.now(), 'lasting': datetime.timedelta(0, 5)}
    setConfig(config)

    
@app.task
def setConfig(config):        
    with open(CONFIG_FILE, 'wb') as f:
        pickle.dump(config, f)

        
@app.task  
def getConfig():
    touchFile(CONFIG_FILE)    
    with open(CONFIG_FILE, 'rb') as f:
        config = pickle.load(f)    
        
    return config

    
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
    return getWeights().get(neuron_id, 0)


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
    
    
@app.task
def outputStillLast():
    output = getConfig()['output'] 
    if DEBUG: print(output['evaluate_time'] , output['lasting'])
    return True if output['evaluate_time'] + output['lasting'] >= datetime.datetime.now() else False

    
@app.task    
def sumInputsAndWeights():
    myName = getHostname()
    sum = 0    
    weights = getWeights()
    
    for inputNeuron in weights:
        if DEBUG: print('input = getOutput.apply_async(routing_key = {0}).get() )'.format(inputNeuron))
        input = getOutput.apply_async(routing_key = inputNeuron).get() 
        # input = 1
        weight = weights[inputNeuron]
        weighted_input = input * weight
        sum += input * weighted_input
        if DEBUG: print('{0} -> {1}: input value = {2}, weight = {3}, weighted_input = {4}'.format(inputNeuron, myName, input, weight, weighted_input))
        
    return sum


@app.task
def getOutput(): 
    config = getConfig()    
    
    if outputStillLast():
        output = 1 
    else:
        output = 0
        config['output']['value'] = output
        # config['output']['evaluate_time'] = datetime.datetime.now()
        setConfig(config)
    
    print ('{0} output: {1}'.format(getHostname(), output))
    
    return output


@app.task
def setOutput(): 
    config = getConfig()
    config['output']['value'] = 1
    config['output']['evaluate_time'] = datetime.datetime.now()
    setConfig(config) 
    fire()


@app.task    
def kick():    
    myName = getHostname()
    weightedInput = sumInputsAndWeights() 
    threshold = getThreshold()
    config = getConfig() 
    
    if weightedInput >= threshold:
        setOutput()
        print('{0} fired!'.format(myName))
        fire()        
 
 
@app.task    
def fire():    
    myName = getHostname()    
    connections = getConnections()  
    
    for connection in connections:
        if DEBUG: print('{0} kicking {1}'.format(myName, connection))
        kick.apply_async(routing_key = connection)