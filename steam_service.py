from steam.client import SteamClient
from enum import Enum
from dotenv import load_dotenv
import os




steam_client = SteamClient()

def sign_in():
    global steam_client 
    if(steam_client.session_id is None):
        steam_client = SteamClient()
        load_dotenv('./server_secrets.env')
        steam_username=os.getenv('steamUser')
        steam_password = os.getenv('steamPass')
        steam_client.cli_login(username=steam_username,password=steam_password)


class SteamQueryParam(Enum):
    '''
    Contains strings for different Steam query parameters
    '''
    NotEmpty = r'\empty\1'   
    NotFull = r'\full\1'  
    Secure = r'\secure\1'
    GameTypePVE = r'\gametype\pve'
    GameTypePVP = r'\gametype\pvp'
    GameTypeCS4 = r'\gametype\cs4'
    GameTypeHC = r'\gametype\hc'

    
class SteamServerQuery():
    '''
    Generates Steam Server queries from the string list parameters
    
    See https://developer.valvesoftware.com/wiki/Master_Server_Query_Protocol for parameter syntax

    params: a string list of the parameters to be applied to the query

    excludeParams: a string list of the parameters to exclude results from the query, added after a \\nor\\ parameter

    appId: an int of the game's steam AppId to be applied to the query

    serverName: will only return servers that have this string in their hostname

    ***

    example call: SteamServerQuery(params=['\\empty\\1','\\full\\1','\\gametype\\pvp'], excludeParams=['\\secure\\1'])

    resulting Filter:  \\appid\\1604030\\empty\\1\\full\\1\\gametype\\pvp\\nor\\1\\secure\\1
    
    '''
    def __init__(self,params=[],excludeParams=[],appId = 1604030,serverName='' ):
        self.params = params
        self.excludeParams = excludeParams
        self.appId = appId
        self.serverName = serverName

    def get_query(self):
        """
        Creates a string query with the parameters of the object
        """
        query = fr'\appid\{self.appId}'
        if(self.serverName):
            query+=fr'\name_match\*{self.serverName}*'
        #adds a
        for param in self.params:
            query+=param.value
        excludeParamCount = len(self.excludeParams)
        if(excludeParamCount>0):
            #add the number of exclude params next to the \nor\ parameter
            query+=fr'\nor\{excludeParamCount}'
            for param in self.excludeParams:
                query+=param.value
        return query
    
def get_server_list(stringQuery, max_servers=20000,timeout = 50):
    '''
    Returns information about servers that match the description of the query

    stringQuery: A Steam Server Query
    '''
    result =  steam_client.gameservers.get_server_list(stringQuery,max_servers,timeout)
    return result
