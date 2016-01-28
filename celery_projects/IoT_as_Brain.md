
# 使用 Celery 於 Docker Swarm 之上 建構類似 Bluemix 的 IoT 平台
## Part II: IoT as Brain

Wei Lin  
20160128  

## 緣起 
  [上次](https://github.com/Wei1234c/CeleryOnDockerSwarm/blob/master/celery_projects/CeleryOnDockerSwarm.md) 在 2 台 Raspberry Pi 上面架了一個 Docker Swarm，然後在 Docker Swarm 裡面使用 Celery (distributed task queue) 的機制，利用 8 個 containers 跑 40 個 processes 執行 "Word Count" 程式，驗證 Celery + Docker Swarm 是可行的。  

  做上述實驗的原因，是為了想利用 Celery + Docker Swarm 快速的建構私有的 類似 [Bluemix](https://console.ng.bluemix.net/) 的 IoT 平台，讓其上的 devices 共同組成一個分散式的協同運算系統，視整個 IoT(Internet of Things) 為一體。     

  Celery 所採用的機制，簡單來說就是: producer 發出要求運算的訊息到 queue 中排隊，眾多的 workers 紛紛到 queue 去撿出訊息來進行處理。類比於 Bluemix 和 [MQTT](http://cheng-min-i-taiwan.blogspot.tw/2015/03/raspberry-pimqtt-android.html): producer 就如同 publisher，queue 如同 topic 或 channel，consumer 如同 subscriber，我覺得兩者是十分類似的。 

  在 Bluemix 的架構中，IBM 把 clients 區分為 device 和 application 兩種角色，devices 扮演 publisher，負責發送資料到平台上，然後扮演 subscriber 的 applications 會收到資料進行運算處理，資料的產生與運算分離，這樣的設計顯得理所當然，Bluemix 所提供的功能也很完整且強大。
  
  然而還有另外一種可能，或許 **資料的儲存 與 運算，其實可以是同一件事情**，就如同我們的大腦，資料的儲存與運算都是由 神經**網路** 來完成的。
  
  我們可以把一個 device 視為一個 neuron，讓 IoT 中眾多的 devices (neurons) 互相連結，經過訓練的 **IoT網路** 就可以自行對環境做出反應，並不需要 集中式的 "邏輯 applications"。但是，這樣的 IoT 平台要如何設計呢? 
  
  在**類神經網路**的發展歷史中，**[XOR網路](https://en.wikipedia.org/wiki/Feedforward_neural_network#Multi-layer_perceptron)** 是一個著名的案例，本次的實驗就來試試看用 IoT 做一個 XOR網路，如果這個可以做，應該也可以組成更複雜的東西。
  ![XOR 網路](https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/XOR_perceptron_net.png/250px-XOR_perceptron_net.png "XOR 網路 (來源: WiKi)")

## 實驗設計與原理:
  - 上圖中各 neuron 的代號:
   - input layer: x, y
   - hidden layer: h1, h2, h3
   - output layer: z
  - 使用 2 台 Raspberry Pi 組成一個 Docker Swarm。
  - Docker Swarm 中 run 6 個 containers，**每個 container 扮演一個 device (neuron)**。
  - 這 6 個 devices (neurons)，可以分佈於不同的實體 host 上面，代表其可佈署在 Internet 上任何位置。
  - Neurons 之間的連結與權重如上圖所示。**設定 neurons 之間的連結，其實就是在設定 publisher / subscriber 的對應關係**。
  - **使用 message queue 來代表 MQTT 中的 "topic"，每個 neuron 都有自己專屬的 message queue**，例如:
   - neruon h2 有自己專屬的 message queue "neuron_h2"，input layer 的 **neuron x 如果想送訊息給 neuron h2，就必須發送到 message queue "neuron_h2"**，neruon h2 就會收到訊息。
   - 上例中，**neuron x 扮演 publisher，neuron h2 扮演 subscriber。neuron h1 也是 neuron x 的 subscriber**。
   - publisher / subscriber 的對應關係 可以是多對多。
  - 假設上圖的 x、y neurons 分別接到各自的 sensor，接收 0/1 的資料，每個 device (neuron) 都可以各自外接多個 sensors 感測外部的環境。
  - Neuron z 的 output 必須隨時等於 XOR(x, y)

## 實作步驟:

### 建立 Docker Swarm
之前已經參考了這篇 [文章](https://www.facebook.com/groups/docker.taipei/permalink/1704032656498757) 使用兩台 RPi2 建立了一個 Docker Swarm。

#### Swarm 中有兩台 Docker machines:
- host rpi202(192.168.0.114) 擔任 Swarm Manager，其 Docker machine name 為 master01
- host rpi201(192.168.0.109) 擔任 Swarm Node，其 Docker machine name 為 node01


```python
HypriotOS: pi@rpi202 in ~
$ docker-machine ls
NAME       ACTIVE   DRIVER    STATE     URL                        SWARM
master01            hypriot   Running   tcp://192.168.0.114:2376   master01 (master)
node01              hypriot   Running   tcp://192.168.0.109:2376   master01
HypriotOS: pi@rpi202 in ~
$


# Swarm 中的 nodes:

HypriotOS: pi@rpi202 in /data/celery_projects
$ docker $(docker-machine config --swarm master01) info
Containers: 4
Images: 51
Role: primary
Strategy: spread
Filters: health, port, dependency, affinity, constraint
Nodes: 2
 master01: 192.168.0.114:2376
  └ Status: Healthy
  └ Containers: 3
  └ Reserved CPUs: 0 / 4
  └ Reserved Memory: 0 B / 972 MiB
  └ Labels: executiondriver=native-0.2, kernelversion=4.1.8-hypriotos-v7+, operatingsystem=Raspbian GNU/Linux 8 (jessie), provider=hypriot, storagedriver=overlay
 node01: 192.168.0.109:2376
  └ Status: Healthy
  └ Containers: 1
  └ Reserved CPUs: 0 / 4
  └ Reserved Memory: 0 B / 972 MiB
  └ Labels: executiondriver=native-0.2, kernelversion=4.1.8-hypriotos-v7+, operatingsystem=Raspbian GNU/Linux 8 (jessie), provider=hypriot, storagedriver=overlay
CPUs: 8
Total Memory: 1.899 GiB
Name: fe30da0875d6
HypriotOS: pi@rpi202 in /data/celery_projects
$
```

### 將檔案 celeryconfig.py、start_workers.sh、資料夾 IoT 複製到 兩台 hosts 的 /data/celery_projects 資料夾之下

可以使用 SCP 來達成，參考: http://www.hypexr.org/linux_scp_help.php  

例如:  
$ scp -r /data/celery_projects root@rpi201:/data/   


```python
# Swarm manager

HypriotOS: pi@rpi202 in /data/celery_projects
$ ll
total 20
drwxr-xr-x 3 999 root 4096 Jan 28 10:08 ./
drwxr-xr-x 3 999 root 4096 Jan 28 11:02 ../
-rw-r--r-- 1 999 root 1469 Jan 28 10:48 celeryconfig.py
drwxr-xr-x 3 999 root 4096 Jan 28 10:08 IoT/
-rwxr-xr-x 1 999 root  963 Jan 28 10:28 start_workers.sh*   <-- 用來啟動 containers 的 script，只在 Swarm Manager 上有需要
HypriotOS: pi@rpi202 in /data/celery_projects
$


# Swarm node
HypriotOS: pi@rpi201 in /data/celery_projects
$ ll
total 16
drwxr-xr-x 3 root root 4096 Jan 28 12:54 ./
drwxr-xr-x 3  999 root 4096 Jan 25 22:55 ../
-rw-r--r-- 1 root root 1250 Jan 28 11:27 celeryconfig.py
drwxr-xr-x 3 root root 4096 Jan 28 12:54 IoT/
HypriotOS: pi@rpi201 in /data/celery_projects
$
```

#### start_workers.sh 的 內容


```python
#### ./start_workers.sh

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
```

### 執行 start_workers.sh，這會做以下幾件事情:
- 建立 Celery 所需的 Broker，使用 Redis
- 建立監控用的 Flower container
- 透過 Swarm Manager 建立並佈署代表 neurons 的 Celery worker containers


```python
HypriotOS: pi@rpi202 in /data/celery_projects
$ ./start_workers.sh
Starting Redis, Flower _________________________________________________
cb706da89689211601b931e88921df1564c939a2cdb3de7bda0f4fa878424553
e136f3f443a46b1a1082b26d367c6c146327d54a3eb9f16aa907dd48bce38a47
Starting Celery cluster containers _________________________________________________
684e3d7b84bfa4713a972d434507473d33adcbaad092e32518a291f7e095c86f
8608740a5a86977f82dc2943feb315575a2ca9e38ebb1a2c73842567c87a865d
1b5180f0284c8c2aa723c63b4297e57fd35cc5a2c0b1ef5dded3bc3026202f61
a6679a9bb651dc735725ecd7b4793f27d598efdd4179c008afaae1e4322b0a42
3a59323ae8f61e76e80595a67e98293c0d42f96b1ac47205aff48d863b321aba
6c0d6a8bb590961e9947bf1d15587f1c0017b114a466fc7061d2fe888740026e
HypriotOS: pi@rpi202 in /data/celery_projects
$
```

#### 共有 6 個 neurons
neuron x, y, z, h1, h2 都被佈署到 Swarm node "node01' 上面，只有 h3 被安排在 Swarm manager 這台 "master01" machine 上。


```python
HypriotOS: pi@rpi202 in /data/celery_projects
$ docker $(docker-machine config --swarm master01) ps
CONTAINER ID        IMAGE                      COMMAND                  CREATED             STATUS              PORTS                                                                          NAMES
6c0d6a8bb590        wei1234c/celery_armv7      "/bin/sh -c 'cd /cele"   2 minutes ago       Up 2 minutes        5555/tcp                                                                       node01/neuron_z
3a59323ae8f6        wei1234c/celery_armv7      "/bin/sh -c 'cd /cele"   2 minutes ago       Up 2 minutes        5555/tcp                                                                       master01/neuron_h3
a6679a9bb651        wei1234c/celery_armv7      "/bin/sh -c 'cd /cele"   2 minutes ago       Up 2 minutes        5555/tcp                                                                       node01/neuron_h2
1b5180f0284c        wei1234c/celery_armv7      "/bin/sh -c 'cd /cele"   2 minutes ago       Up 2 minutes        5555/tcp                                                                       node01/neuron_h1
8608740a5a86        wei1234c/celery_armv7      "/bin/sh -c 'cd /cele"   3 minutes ago       Up 3 minutes        5555/tcp                                                                       node01/neuron_y
684e3d7b84bf        wei1234c/celery_armv7      "/bin/sh -c 'cd /cele"   3 minutes ago       Up 3 minutes        5555/tcp                                                                       node01/neuron_x
e136f3f443a4        wei1234c/celery_armv7      "/bin/sh -c 'cd /cele"   3 minutes ago       Up 3 minutes        192.168.0.114:5555->5555/tcp                                                   master01/flower
cb706da89689        hypriot/rpi-redis          "/entrypoint.sh redis"   3 minutes ago       Up 3 minutes        192.168.0.114:6379->6379/tcp                                                   master01/redis
ef0c519ae7da        hypriot/rpi-swarm          "/swarm join --advert"   5 minutes ago       Up 5 minutes        2375/tcp                                                                       node01/swarm-agent
966928d0a37c        hypriot/rpi-swarm          "/swarm join --advert"   5 minutes ago       Up 5 minutes        2375/tcp                                                                       master01/swarm-agent
b01b05cbe323        hypriot/rpi-swarm          "/swarm manage --tlsv"   5 minutes ago       Up 5 minutes        2375/tcp, 192.168.0.114:3376->3376/tcp                                         master01/swarm-agent-master
ab78ab3e5476        nimblestratus/rpi-consul   "/bin/start -server -"   6 minutes ago       Up 6 minutes        53/udp, 8300-8302/tcp, 8301-8302/udp, 8400/tcp, 192.168.0.114:8500->8500/tcp   master01/consul
HypriotOS: pi@rpi202 in /data/celery_projects
$
```


```python
from IoT.tasks import * 
from time import sleep
```


```python
def printConfig(neuron_id):
    print('{0} config:\n {1}'.format(neuron_id, getConfig.apply_async(routing_key = neuron_id).get()))
          
def printOutput(neuron_id):
    print('{0} output: {1}'.format(neuron_id, getOutput.apply_async(routing_key = neuron_id).get()))
    
def printOutputs():
    # 印出各 neuron 的 output
    printOutput('neuron_x')
    printOutput('neuron_y')
    printOutput('neuron_h1')
    printOutput('neuron_h2')
    printOutput('neuron_h3')
    printOutput('neuron_z')
```

### 設定 connections
#### 設定 neurons 之間的連結，其實就是在設定 publisher / subscriber 的對應關係


```python
# input layer fan out
# neuron x
addConnection.apply_async(['neuron_h1'], routing_key = 'neuron_x')
addConnection.apply_async(['neuron_h2'], routing_key = 'neuron_x')
# neuron y
addConnection.apply_async(['neuron_h2'], routing_key = 'neuron_y')
addConnection.apply_async(['neuron_h3'], routing_key = 'neuron_y')

# hidden layer fan out
addConnection.apply_async(['neuron_z'], routing_key = 'neuron_h1')
addConnection.apply_async(['neuron_z'], routing_key = 'neuron_h2')
addConnection.apply_async(['neuron_z'], routing_key = 'neuron_h3')
```




    <AsyncResult: 962d5d9a-8d1c-4175-9b41-0b3d88a68fbc>



### 設定 weights


```python
# input layer 
# neuron x
setWeight.apply_async(['sensor_x_1', 1], routing_key = 'neuron_x')
setWeight.apply_async(['sensor_x_2', 1], routing_key = 'neuron_x')
# neuron y
setWeight.apply_async(['sensor_y_1', 1], routing_key = 'neuron_y')
setWeight.apply_async(['sensor_y_2', 1], routing_key = 'neuron_y')

# hidden layer
setWeight.apply_async(['neuron_x', 1], routing_key = 'neuron_h1')
setWeight.apply_async(['neuron_x', 1], routing_key = 'neuron_h2')
setWeight.apply_async(['neuron_y', 1], routing_key = 'neuron_h2')
setWeight.apply_async(['neuron_y', 1], routing_key = 'neuron_h3')

# output layer
setWeight.apply_async(['neuron_h1', 1], routing_key = 'neuron_z')
setWeight.apply_async(['neuron_h2', -2], routing_key = 'neuron_z')
setWeight.apply_async(['neuron_h3', 1], routing_key = 'neuron_z') 
```




    <AsyncResult: 676b47f3-da9b-4e82-930c-52327d7e40e3>



### 設定 thresholds


```python
# input layer 
setThreshold.apply_async([0.9], routing_key = 'neuron_x') 
setThreshold.apply_async([0.9], routing_key = 'neuron_y') 

# hidden layer
setThreshold.apply_async([0.9], routing_key = 'neuron_h1')
setThreshold.apply_async([1.9], routing_key = 'neuron_h2')
setThreshold.apply_async([0.9], routing_key = 'neuron_h3')

# output layer
setThreshold.apply_async([0.9], routing_key = 'neuron_z') 
```




    <AsyncResult: 83135759-21de-4804-bb93-838fe82db236>



### 設定之後，各 neurons 的 config 狀態:


```python
printConfig('neuron_x')
```

    neuron_x config:
     {'output': {'lasting': datetime.timedelta(0, 5), 'evaluate_time': datetime.datetime(2016, 1, 28, 21, 6, 21, 334197), 'value': 0}, 'connections': {'neuron_h2', 'neuron_h1'}, 'threshold': 0.9, 'weights': {'sensor_x_2': 1, 'sensor_x_1': 1}}
    


```python
printConfig('neuron_y')
```

    neuron_y config:
     {'output': {'lasting': datetime.timedelta(0, 5), 'evaluate_time': datetime.datetime(2016, 1, 28, 21, 6, 21, 394303), 'value': 0}, 'connections': {'neuron_h2', 'neuron_h3'}, 'threshold': 0.9, 'weights': {'sensor_y_1': 1, 'sensor_y_2': 1}}
    


```python
printConfig('neuron_h1')
```

    neuron_h1 config:
     {'output': {'lasting': datetime.timedelta(0, 5), 'evaluate_time': datetime.datetime(2016, 1, 28, 21, 6, 21, 488497), 'value': 0}, 'connections': {'neuron_z'}, 'threshold': 0.9, 'weights': {'neuron_x': 1}}
    


```python
printConfig('neuron_h2')
```

    neuron_h2 config:
     {'output': {'lasting': datetime.timedelta(0, 5), 'evaluate_time': datetime.datetime(2016, 1, 28, 21, 6, 21, 508248), 'value': 0}, 'connections': {'neuron_z'}, 'threshold': 1.9, 'weights': {'neuron_x': 1, 'neuron_y': 1}}
    


```python
printConfig('neuron_h3')
```

    neuron_h3 config:
     {'output': {'lasting': datetime.timedelta(0, 5), 'evaluate_time': datetime.datetime(2016, 1, 28, 21, 6, 21, 532751), 'value': 0}, 'connections': {'neuron_z'}, 'threshold': 0.9, 'weights': {'neuron_y': 1}}
    


```python
printConfig('neuron_z')
```

    neuron_z config:
     {'output': {'lasting': datetime.timedelta(0, 5), 'evaluate_time': datetime.datetime(2016, 1, 28, 21, 6, 22, 68767), 'value': 0}, 'threshold': 0.9, 'weights': {'neuron_h2': -2, 'neuron_h1': 1, 'neuron_h3': 1}}
    

### 模擬 sensor input，然後查看各 neurons 的 output 狀態
一個 neuron fire 之後，如果沒有持續的輸入可維持 fire 的狀態，則過 5 秒鐘之 neuron 的 output 一定為 0


```python
### 模擬 sensor input，強迫 neuron x 或 y ouput 1
sleep(5)  # 停 5秒，等電位歸零
# setOutput.apply_async(routing_key = 'neuron_x') # force neuron x output 0.
# setOutput.apply_async(routing_key = 'neuron_y') # force neuron y output 0.

printOutputs()
```

    neuron_x output: 0
    neuron_y output: 0
    neuron_h1 output: 0
    neuron_h2 output: 0
    neuron_h3 output: 0
    neuron_z output: 0
    


```python
### 模擬 sensor input，強迫 neuron x 或 y ouput 1
sleep(5)  # 停 5秒，等電位歸零
setOutput.apply_async(routing_key = 'neuron_x') # force neuron x output 1 and fire.
# setOutput.apply_async(routing_key = 'neuron_y') # force neuron y output 0.

printOutputs()
```

    neuron_x output: 1
    neuron_y output: 0
    neuron_h1 output: 1
    neuron_h2 output: 0
    neuron_h3 output: 0
    neuron_z output: 1
    


```python
### 模擬 sensor input，強迫 neuron x 或 y ouput 1
sleep(5)  # 停 5秒，等電位歸零
# setOutput.apply_async(routing_key = 'neuron_x') # force neuron x output 0.
setOutput.apply_async(routing_key = 'neuron_y') # force neuron y output 1 and fire.

printOutputs()
```

    neuron_x output: 0
    neuron_y output: 1
    neuron_h1 output: 0
    neuron_h2 output: 0
    neuron_h3 output: 1
    neuron_z output: 1
    


```python
### 模擬 sensor input，強迫 neuron x 或 y ouput 1
sleep(5)  # 停 5秒，等電位歸零
setOutput.apply_async(routing_key = 'neuron_x') # force neuron x output 1 and fire.
setOutput.apply_async(routing_key = 'neuron_y') # force neuron y output 1 and fire.

printOutputs()
```

    neuron_x output: 1
    neuron_y output: 1
    neuron_h1 output: 1
    neuron_h2 output: 1
    neuron_h3 output: 1
    neuron_z output: 0
    

### Flower 中顯示各 worker 處理的 messages 數量:

![各 neuron 的活動次數](.\jpgs\flower2.jpg "各 neuron 的活動次數")

## Summary

 這次實驗，主要是想驗證可以使用 Celery + Docker Swarm 快速的建構私有的 類似 Bluemix 的 IoT 平台，讓其上的 devices 共同組成一個分散式的協同運算系統，視整個 IoT(Internet of Things) 為一體。

 本次實作的平台中，使用 2 台 Raspberry Pi 組成一個 Docker Swarm，run 6 個 containers，每個 container 扮演一個 device (neuron)。每個 neuron 都有自己專屬的 message queue，類似於 MQTT 中 "topic" 的作用。設定 neurons 之間的連結，其實就是在設定 publisher / subscriber 的對應關係，publisher / subscriber 的對應關係 可以是多對多。

 設定好 connections / weights / thresholds 之後，可以使用這 6 個 neurons (devices / containers)，組成一個 XOR網路，針對外接的 sensors 所感測到的環境狀態，依據 網路的pattern 決定最終的 output。
