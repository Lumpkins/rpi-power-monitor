
from requests.auth import HTTPBasicAuth
import requests

def get_key():
    with open("../conn.txt") as f:
        return f.readlines()[0]
    

class ApiClient():
    
    def __init__(self) -> None:
        self.ApiKey=get_key()
    
    def PutPMData(self,data):
        url = r'https://192.168.1.201/PM/Put'
        headers = {'Accept': 'application/json'}
        auth = HTTPBasicAuth('ApiKey', get_key())


        res = requests.get(url, headers=headers, auth=auth, json=data)

        #test if good or not

