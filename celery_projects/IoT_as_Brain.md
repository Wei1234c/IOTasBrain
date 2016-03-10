
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
neuron x, y, z, h1, h2 都被佈署到 Swarm node "node01' 上面，


```python
HypriotOS: pi@rpi201 in ~
$ docker ps
CONTAINER ID        IMAGE                   COMMAND                  CREATED              STATUS              PORTS               NAMES
6c0d6a8bb590        wei1234c/celery_armv7   "/bin/sh -c 'cd /cele"   About a minute ago   Up About a minute   5555/tcp            neuron_z
a6679a9bb651        wei1234c/celery_armv7   "/bin/sh -c 'cd /cele"   About a minute ago   Up About a minute   5555/tcp            neuron_h2
1b5180f0284c        wei1234c/celery_armv7   "/bin/sh -c 'cd /cele"   About a minute ago   Up About a minute   5555/tcp            neuron_h1
8608740a5a86        wei1234c/celery_armv7   "/bin/sh -c 'cd /cele"   About a minute ago   Up About a minute   5555/tcp            neuron_y
684e3d7b84bf        wei1234c/celery_armv7   "/bin/sh -c 'cd /cele"   2 minutes ago        Up 2 minutes        5555/tcp            neuron_x
ef0c519ae7da        hypriot/rpi-swarm       "/swarm join --advert"   4 minutes ago        Up 4 minutes        2375/tcp            swarm-agent
HypriotOS: pi@rpi201 in ~
$ 
```

只有 h3 被安排在 Swarm manager 這台 "master01" machine 上。


```python
HypriotOS: pi@rpi202 in /data/celery_projects
$ docker ps
CONTAINER ID        IMAGE                      COMMAND                  CREATED              STATUS              PORTS                                                                    NAMES
3a59323ae8f6        wei1234c/celery_armv7      "/bin/sh -c 'cd /cele"   35 seconds ago       Up 32 seconds       5555/tcp                                                                 neuron_h3
e136f3f443a4        wei1234c/celery_armv7      "/bin/sh -c 'cd /cele"   About a minute ago   Up About a minute   0.0.0.0:5555->5555/tcp                                                   flower
cb706da89689        hypriot/rpi-redis          "/entrypoint.sh redis"   About a minute ago   Up About a minute   0.0.0.0:6379->6379/tcp                                                   redis
966928d0a37c        hypriot/rpi-swarm          "/swarm join --advert"   3 minutes ago        Up 3 minutes        2375/tcp                                                                 swarm-agent
b01b05cbe323        hypriot/rpi-swarm          "/swarm manage --tlsv"   4 minutes ago        Up 4 minutes        2375/tcp, 0.0.0.0:3376->3376/tcp                                         swarm-agent-master
ab78ab3e5476        nimblestratus/rpi-consul   "/bin/start -server -"   4 minutes ago        Up 4 minutes        53/udp, 8300-8302/tcp, 8400/tcp, 0.0.0.0:8500->8500/tcp, 8301-8302/udp   consul
HypriotOS: pi@rpi202 in /data/celery_projects
$ 
```

#### 從 Swarm Manager 的視角 綜觀全局


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

---

### <font color="red">開始下指令config網路</font>


```python
from IoT.neuron import * 
from time import sleep
import pandas as pd
from pandas import DataFrame

pd.options.display.max_colwidth = 400
REFRACTORY_PERIOD = 0.1   # 0.1 seconds
```

#### Note:
定義一個 neuron 行為的 Python code 放在 celery_projects/IoT/neuron.py，Celery 的 worker 被啟動時 會將之載入。  
neuron.py 中以一個 pickle 檔案紀錄一個 neuron 的組成與任一時刻的狀態，包括有 connections、weights、inputs、output...


```python
# 總共有 6 個 neurons，各代表一個 Docker container，被隨機佈署在 Docker Swarm 中的任一台 machine 上。
neurons = ['neuron_x', 'neuron_y', 'neuron_h1', 'neuron_h2', 'neuron_h3', 'neuron_z'] 

# print 出 一個 neuron 中的 Log
def printConfig(neuron):
    print('{0:_^78}\n {1}\n'.format(neuron + " config:", getConfig.apply_async(routing_key = neuron).get()))

# 清除所有 neurons 中的 logs    
def emptyLogs():
    for neuron in neurons:
        emptyLog.apply_async(routing_key = neuron)

# 彙整logs。將所有 neurons 中的 logs merge 在一起，成為一個 Pandas.DataFrame
def mergeLogs():
    logs = []
    
    for neuron in neurons:
        currentLog = getLog.apply_async(routing_key = neuron).get()
        logs += currentLog 
            
    df = DataFrame(list(logs), columns = ['time', 'neuron', 'message']) 
    df.set_index('time', inplace = True)
    df.sort_index(inplace = True)
    
    return df
```

### 清空 log files


```python
# 清除所有 neurons 中的 logs  
emptyLogs()
```

### 設定 connections
#### 設定 neurons 之間的連結，其實就是在設定 publisher / subscriber 的對應關係


```python
# input layer fan out
# neuron x
addConnection.apply_async(['neuron_h1'], routing_key = 'neuron_x')  # 增設 neuron_x -> neuron_h1 的 connection
addConnection.apply_async(['neuron_h2'], routing_key = 'neuron_x')
# neuron y
addConnection.apply_async(['neuron_h2'], routing_key = 'neuron_y')  # 增設 neuron_y -> neuron_h2 的 connection
addConnection.apply_async(['neuron_h3'], routing_key = 'neuron_y')

# hidden layer fan out
addConnection.apply_async(['neuron_z'], routing_key = 'neuron_h1')  # 增設 neuron_h1 -> neuron_z 的 connection
addConnection.apply_async(['neuron_z'], routing_key = 'neuron_h2')
addConnection.apply_async(['neuron_z'], routing_key = 'neuron_h3')
```




    <AsyncResult: 2c476123-b85e-4a50-8b31-56ab64cb0758>



### 設定 weights


```python
# hidden layer
setWeight.apply_async(['neuron_x', 1], routing_key = 'neuron_h1')  # 設定 neuron_x -> neuron_h1 的 weight = 1
setWeight.apply_async(['neuron_x', 1], routing_key = 'neuron_h2')
setWeight.apply_async(['neuron_y', 1], routing_key = 'neuron_h2')  # 設定 neuron_y -> neuron_h2 的 weight = 1
setWeight.apply_async(['neuron_y', 1], routing_key = 'neuron_h3')

# output layer
setWeight.apply_async(['neuron_h1', 1], routing_key = 'neuron_z')
setWeight.apply_async(['neuron_h2', -2], routing_key = 'neuron_z')  # 設定 neuron_h2 -> neuron_z 的 weight = -2 (inhibitory)
setWeight.apply_async(['neuron_h3', 1], routing_key = 'neuron_z') 
```




    <AsyncResult: ca9824e0-05af-4b55-bf5e-3d0b097388ed>



### 設定 thresholds


```python
# input layer 
setThreshold.apply_async([0.9], routing_key = 'neuron_x')  # 設定 neuron_x 的 threshold = 0.9
setThreshold.apply_async([0.9], routing_key = 'neuron_y') 

# hidden layer
setThreshold.apply_async([0.9], routing_key = 'neuron_h1') 
setThreshold.apply_async([1.9], routing_key = 'neuron_h2')  # 設定 neuron_h2 的 threshold = 1.9
setThreshold.apply_async([0.9], routing_key = 'neuron_h3')

# output layer
setThreshold.apply_async([0.9], routing_key = 'neuron_z')  # 設定 neuron_z 的 threshold = 0.9
```




    <AsyncResult: 9f2e95ef-72a9-4d10-81a6-9ff41aed1b2d>



### 模擬 sensor input，然後查看各 neurons 的 output 狀態
一個 neuron fire 之後，如果沒有持續的輸入可維持 fire 的狀態，則過 5 秒鐘之 neuron 的 output 一定為 0


```python
### 模擬 sensor input，強迫 neuron x 或 y ouput 1
emptyLogs()  # 清除 logs
sleep(REFRACTORY_PERIOD)  # 等電位歸零 
mergeLogs()  # 彙整 logs
```




<div>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>neuron</th>
      <th>message</th>
    </tr>
    <tr>
      <th>time</th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
  </tbody>
</table>
</div>




```python
### 模擬 sensor input，強迫 neuron x 或 y ouput 1
emptyLogs()  # 清除 logs
sleep(REFRACTORY_PERIOD)  # 等電位歸零
fire.apply_async(routing_key = 'neuron_x') # force neuron x output 1 and fire.
mergeLogs()  # 彙整 logs
```




<div>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>neuron</th>
      <th>message</th>
    </tr>
    <tr>
      <th>time</th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>2016-03-10 20:51:18.489509</th>
      <td>neuron_x</td>
      <td>neuron_x fires.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:18.493309</th>
      <td>neuron_x</td>
      <td>Setting output of neuron_x to ACTION_POTENTIAL.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:18.559939</th>
      <td>neuron_h1</td>
      <td>neuron_x is kicking neuron_h1.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:18.581558</th>
      <td>neuron_h2</td>
      <td>neuron_x is kicking neuron_h2.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:18.587120</th>
      <td>neuron_h1</td>
      <td>neuron_h1 fires.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:18.595436</th>
      <td>neuron_h1</td>
      <td>Setting output of neuron_h1 to ACTION_POTENTIAL.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:18.654499</th>
      <td>neuron_z</td>
      <td>neuron_h1 is kicking neuron_z.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:18.689138</th>
      <td>neuron_z</td>
      <td>neuron_z fires.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:18.692448</th>
      <td>neuron_z</td>
      <td>Setting output of neuron_z to ACTION_POTENTIAL.</td>
    </tr>
  </tbody>
</table>
</div>




```python
### 模擬 sensor input，強迫 neuron x 或 y ouput 1
emptyLogs()  # 清除 logs
sleep(REFRACTORY_PERIOD)  # 等電位歸零
fire.apply_async(routing_key = 'neuron_y') # force neuron y output 1 and fire.
mergeLogs()  # 彙整 logs
```




<div>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>neuron</th>
      <th>message</th>
    </tr>
    <tr>
      <th>time</th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>2016-03-10 20:51:21.721563</th>
      <td>neuron_y</td>
      <td>neuron_y fires.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:21.726665</th>
      <td>neuron_y</td>
      <td>Setting output of neuron_y to ACTION_POTENTIAL.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:21.796071</th>
      <td>neuron_h3</td>
      <td>neuron_y is kicking neuron_h3.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:21.818246</th>
      <td>neuron_h3</td>
      <td>neuron_h3 fires.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:21.822734</th>
      <td>neuron_h3</td>
      <td>Setting output of neuron_h3 to ACTION_POTENTIAL.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:21.858226</th>
      <td>neuron_h2</td>
      <td>neuron_y is kicking neuron_h2.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:21.899541</th>
      <td>neuron_z</td>
      <td>neuron_h3 is kicking neuron_z.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:21.922727</th>
      <td>neuron_z</td>
      <td>neuron_z fires.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:21.927111</th>
      <td>neuron_z</td>
      <td>Setting output of neuron_z to ACTION_POTENTIAL.</td>
    </tr>
  </tbody>
</table>
</div>




```python
### 模擬 sensor input，強迫 neuron x 或 y ouput 1
emptyLogs()  # 清除 logs
sleep(REFRACTORY_PERIOD)  # 等電位歸零
fire.apply_async(routing_key = 'neuron_x') # force neuron x output 1 and fire.
fire.apply_async(routing_key = 'neuron_y') # force neuron y output 1 and fire.
mergeLogs()  # 彙整 logs
```




<div>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>neuron</th>
      <th>message</th>
    </tr>
    <tr>
      <th>time</th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>2016-03-10 20:51:25.524156</th>
      <td>neuron_x</td>
      <td>neuron_x fires.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.543150</th>
      <td>neuron_x</td>
      <td>Setting output of neuron_x to ACTION_POTENTIAL.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.557295</th>
      <td>neuron_y</td>
      <td>neuron_y fires.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.561307</th>
      <td>neuron_y</td>
      <td>Setting output of neuron_y to ACTION_POTENTIAL.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.620065</th>
      <td>neuron_h3</td>
      <td>neuron_y is kicking neuron_h3.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.632281</th>
      <td>neuron_h1</td>
      <td>neuron_x is kicking neuron_h1.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.649561</th>
      <td>neuron_h1</td>
      <td>neuron_h1 fires.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.649841</th>
      <td>neuron_h3</td>
      <td>neuron_h3 fires.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.653656</th>
      <td>neuron_h1</td>
      <td>Setting output of neuron_h1 to ACTION_POTENTIAL.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.657057</th>
      <td>neuron_h3</td>
      <td>Setting output of neuron_h3 to ACTION_POTENTIAL.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.689440</th>
      <td>neuron_h2</td>
      <td>neuron_x is kicking neuron_h2.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.759928</th>
      <td>neuron_z</td>
      <td>neuron_h1 is kicking neuron_z.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.787273</th>
      <td>neuron_z</td>
      <td>neuron_z fires.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.791270</th>
      <td>neuron_z</td>
      <td>Setting output of neuron_z to ACTION_POTENTIAL.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.813897</th>
      <td>neuron_h2</td>
      <td>neuron_y is kicking neuron_h2.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.835654</th>
      <td>neuron_h2</td>
      <td>neuron_h2 fires.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.842069</th>
      <td>neuron_h2</td>
      <td>Setting output of neuron_h2 to ACTION_POTENTIAL.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.869606</th>
      <td>neuron_z</td>
      <td>neuron_h3 is kicking neuron_z.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.892445</th>
      <td>neuron_z</td>
      <td>neuron_z is still in refractory-period.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.895733</th>
      <td>neuron_z</td>
      <td>neuron_z is still in refractory_period at action potential, then a neuron neuron_h3 kicks in, now sum_of_weighted_inputs &gt;= threshold.</td>
    </tr>
    <tr>
      <th>2016-03-10 20:51:25.943689</th>
      <td>neuron_z</td>
      <td>neuron_h2 is kicking neuron_z.</td>
    </tr>
  </tbody>
</table>
</div>



### [Flower](http://192.168.0.114:5555) 中顯示各 worker 處理的 messages 數量:

![各 neuron 的活動次數](https://github.com/Wei1234c/IOTasBrain/raw/master/celery_projects/jpgs/flower2.jpg "各 neuron 的活動次數")

### 各 neurons 的 config 狀態:


```python
for neuron in reversed(neurons): printConfig(neuron)
```

    _______________________________neuron_z config:_______________________________
     {'inputs': {'neuron_h1': {'lasting': datetime.timedelta(0, 0, 500000), 'kick_time': datetime.datetime(2016, 3, 10, 20, 51, 25, 763889), 'value': 1}, 'neuron_h2': {'lasting': datetime.timedelta(0, 0, 500000), 'kick_time': datetime.datetime(2016, 3, 10, 20, 51, 25, 946926), 'value': 1}, 'neuron_h3': {'lasting': datetime.timedelta(0, 0, 500000), 'kick_time': datetime.datetime(2016, 3, 10, 20, 51, 25, 873372), 'value': 1}}, 'output': {'lasting': datetime.timedelta(0, 0, 100000), 'polarized_time': datetime.datetime(2016, 3, 10, 20, 51, 25, 803324), 'value': 1}, 'threshold': 0.9, 'weights': {'neuron_h1': 1, 'neuron_h3': 1, 'neuron_h2': -2}}
    
    ______________________________neuron_h3 config:_______________________________
     {'inputs': {'neuron_y': {'lasting': datetime.timedelta(0, 0, 500000), 'kick_time': datetime.datetime(2016, 3, 10, 20, 51, 25, 628021), 'value': 1}}, 'threshold': 0.9, 'output': {'lasting': datetime.timedelta(0, 0, 100000), 'polarized_time': datetime.datetime(2016, 3, 10, 20, 51, 25, 660253), 'value': 1}, 'connections': {'neuron_z'}, 'weights': {'neuron_y': 1}}
    
    ______________________________neuron_h2 config:_______________________________
     {'inputs': {'neuron_x': {'lasting': datetime.timedelta(0, 0, 500000), 'kick_time': datetime.datetime(2016, 3, 10, 20, 51, 25, 693412), 'value': 1}, 'neuron_y': {'lasting': datetime.timedelta(0, 0, 500000), 'kick_time': datetime.datetime(2016, 3, 10, 20, 51, 25, 817076), 'value': 1}}, 'threshold': 1.9, 'output': {'lasting': datetime.timedelta(0, 0, 100000), 'polarized_time': datetime.datetime(2016, 3, 10, 20, 51, 25, 845780), 'value': 1}, 'connections': {'neuron_z'}, 'weights': {'neuron_x': 1, 'neuron_y': 1}}
    
    ______________________________neuron_h1 config:_______________________________
     {'inputs': {'neuron_x': {'lasting': datetime.timedelta(0, 0, 500000), 'kick_time': datetime.datetime(2016, 3, 10, 20, 51, 25, 635170), 'value': 1}}, 'output': {'lasting': datetime.timedelta(0, 0, 100000), 'polarized_time': datetime.datetime(2016, 3, 10, 20, 51, 25, 657518), 'value': 1}, 'weights': {'neuron_x': 1}, 'threshold': 0.9, 'connections': {'neuron_z'}}
    
    _______________________________neuron_y config:_______________________________
     {'inputs': {}, 'output': {'lasting': datetime.timedelta(0, 0, 100000), 'polarized_time': datetime.datetime(2016, 3, 10, 20, 51, 25, 565365), 'value': 1}, 'connections': {'neuron_h2', 'neuron_h3'}, 'threshold': 0.9}
    
    _______________________________neuron_x config:_______________________________
     {'inputs': {}, 'output': {'lasting': datetime.timedelta(0, 0, 100000), 'polarized_time': datetime.datetime(2016, 3, 10, 20, 51, 25, 547371), 'value': 1}, 'connections': {'neuron_h1', 'neuron_h2'}, 'threshold': 0.9}
    
    

## Summary

  這次實驗，主要是想驗證 可以使用 Celery + Docker Swarm 快速地建構私有的 類似 Bluemix 的 IoT 平台，讓其上的 devices 共同組成一個分散式的協同運算系統，視整個 IoT(Internet of Things) 為一體。  
  
  本次實作的平台中，使用 2 台 Raspberry Pi 組成一個 Docker Swarm，run 6 個 containers，每個 container 扮演一個 device，也可視為一個 neuron。設定 neurons 之間的連結，好比是在設定 publisher / subscriber 的對應關係，其對應關係 可以是多對多。  
  
  可以使用這 6 個 neurons (devices / containers)，在設定好 connections / weights / thresholds 之後，組成一個 XOR網路，針對外接的 sensors 所感測到的環境狀態，依據 網路的pattern 決定最終的 output。

## 後記 (2016/01/31)

  後來發現 XOR網路 可能不會存在於現實世界的大腦中，因為要實現XOR網路 就必須要求 各訊號都同時到達，這在真實的世界中不大可能發生，而且就算發生了，因為這種機制會要求 "等待"，對系統整體的運算效能會造成很大的損失，我不認為是一個好的運算機制，大自然應該不會這樣設計大腦。

### 參考資料
[Action potential](https://en.wikipedia.org/wiki/Action_potential)  
[Neural coding](https://en.wikipedia.org/wiki/Neural_coding)  
[Artificial neuron](https://en.wikipedia.org/wiki/Artificial_neuron)  
["All-or-none" principle](https://en.wikipedia.org/wiki/Action_potential#.22All-or-none.22_principle)  
[Refractory period](https://en.wikipedia.org/wiki/Action_potential#Refractory_period)  
- The absolute refractory period is largely responsible for the unidirectional propagation of action potentials along axons.[34] At any given moment, the patch of axon behind the actively spiking part is refractory, but the patch in front, not having been activated recently, is capable of being stimulated by the depolarization from the action potential.  



