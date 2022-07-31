
from requests.auth import HTTPBasicAuth
import requests
from datetime import datetime
import json

def get_key():
    with open("../conn.txt") as f:
        return f.readlines()[0].strip()
    

class ApiClient():


    def __init__(self) -> None:
        self.ApiKey=get_key()
        self.batch_size=10
        self.current_batch=0
        self.batched_data=[]
        self.auth = ('ApiKey', self.ApiKey)#HTTPBasicAuth


    def PutPMData(self):
        print('Logging data to SQL')

        url = r'http://192.168.1.201/PM/Put'
        headers = {'Accept': '*/*',
        'User-Agent':'rpi-power-monitor',
        'Connection':'keep-alive',
        'Content-Type':'application/json',
        'Accept-Encoding':'gzip, deflate, br',
        'ApiKey':self.ApiKey,
        'Host':'www.homeapi.net'}
        
        json_str=json.dumps(self.batched_data,indent=4)
        #print(json_str)

        res = requests.put(url, headers=headers, auth=self.auth, json=self.batched_data)
        print(res.content)


        #test if good or not

    def AddBatch(self, data):
        
        self.batched_data.append(self.extract_data(data,'ct1'))
        self.batched_data.append(self.extract_data(data,'ct2'))
        
        if(self.current_batch>=self.batch_size):
            self.PutPMData()
            self.current_batch=0
            self.batched_data=[]
        else:
            self.current_batch+=1



    def extract_data(self,data,circuit):
        now = datetime.now()
        return {"dateTime":now.strftime('%Y-%m-%dT%H:%M:%S'),
        'circuit':circuit,
        'current':data[circuit]['current'],
        'power':data[circuit]['power'],
        'pf':data[circuit]['pf']
        }