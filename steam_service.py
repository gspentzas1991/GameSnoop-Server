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
    GameTypeCS2 = r'\gametype\cs2'
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
        Returns a string query with the parameters of the object
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

def get_complete_server_list():
    '''
    Runs multiple Steam Server Queries to get every single game server listed (not including empty ones)

    Because each query can only return up to 20k servers, we split up server types to try to get fewer servers with each query

    Returns the serverlist
    
    '''

    game_servers = []
    #each steam server request can return up to 20k servers, so we need to create multiple different queries and collect the results to get all servers
    #by default we ignore empty servers, this might turn into an option later (probably everything will be handled with frontent filters)
    queryList = []
    #password protected servers (any kind)
    queryList.append(SteamServerQuery(params=[SteamQueryParam.Secure,SteamQueryParam.NotEmpty]))
    #full servers (any kind)
    queryList.append(SteamServerQuery(excludeParams=[SteamQueryParam.NotFull]))
    #PVP servers with no password, who are not full
    queryList.append(SteamServerQuery(params=[SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.GameTypePVP],
    excludeParams=[SteamQueryParam.Secure]))
    #pve servers of clan size 4 who are not full, with no password and not hardcore
    queryList.append(SteamServerQuery(params=[SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.GameTypePVE,SteamQueryParam.GameTypeCS4],
    excludeParams=[SteamQueryParam.Secure,SteamQueryParam.GameTypeHC]))
    #PVE servers with no password, not hardcore and with a clan size different than 4
    queryList.append(SteamServerQuery(params=[SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.GameTypePVE],
    excludeParams=[SteamQueryParam.Secure,SteamQueryParam.GameTypeHC,SteamQueryParam.GameTypeCS4]))
    #PVE servers that are HardCore with no passwords
    queryList.append(SteamServerQuery(params=[SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.GameTypePVE,SteamQueryParam.GameTypeHC],
    excludeParams=[SteamQueryParam.Secure]))
    for query in queryList:
        game_servers.extend(get_server_list(query.get_query()))
    return game_servers