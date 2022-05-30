from steam.client import SteamClient
from enum import Enum
from dotenv import load_dotenv
import os




steam_client = SteamClient()

def sign_in():
    '''
    Signs in the global SteamClient object, with the credentials provided in the server_secrets.env file
    '''
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

    GameTypeCS requires a clan size to also be provided, see get_clan_size(size)
    '''
    NotEmpty = r'\empty\1'   
    NotFull = r'\full\1'  
    Secure = r'\secure\1'
    Dedicated = r'\dedicated\1'
    GameTypePVE = r'\gametype\pve'
    GameTypePVP = r'\gametype\pvp'
    GameTypeHC = r'\gametype\hc'
    #requires a clan size to be provided
    __GameTypeCS = r'\gametype\cs'
    __ServerName = r'\name_match'

    def __str__(self):
        return self.value
    def generate_LogicalOR_query(params):
        '''
        Returns a steam query string that returns servers if they satisfy any of the supplied params

        params: A list of SteamQueryParam that we want to apply the OR operation on

        example:
        call: generate_LogicalOR_query([SteamQueryParam.PVE,SteamQueryParam.PVP])
        return: r'\or\\2\gametype\pve\gametype\pvp'
        '''
        query = ''
        paramCount = len(params)
        if(paramCount==0):
            return query
        else:
            query+=fr'\or\{paramCount}'
        for param in params:
            query+=str(param)
        return query
    def get_clan_size(size):
        '''
        Returns a parameter for the specified clan size
        '''
        return f'{SteamQueryParam.__GameTypeCS}{size}'
    def get_server_name(name):
        '''
        Returns a parameter for the specified server name, surrounded by wildcards
        '''
        return rf'{SteamQueryParam.__ServerName}\*{name}*'

    
class SteamServerQuery():
    '''
    Generates Steam Server queries from the string list parameters
    
    See https://developer.valvesoftware.com/wiki/Master_Server_Query_Protocol for parameter syntax

    params: a string list of the parameters to be applied to the query

    excludeParams: a string list of the parameters to exclude results from the query, added after a \\nor\\ parameter

    appId: an int of the game's steam AppId to be applied to the query

    ***

    example call: SteamServerQuery(params=['\\empty\\1','\\full\\1','\\gametype\\pvp'], excludeParams=['\\secure\\1'])

    resulting Filter:  \\appid\\1604030\\empty\\1\\full\\1\\gametype\\pvp\\nor\\1\\secure\\1
    
    '''
    def __init__(self,params=[],excludeParams=[],appId = 1604030 ):
        self.params = params
        self.excludeParams = excludeParams
        self.appId = appId

    def get_query(self):
        """
        Returns a string query with the parameters of the object
        """
        query = fr'\appid\{self.appId}'
        #TODO: comment this better
        for param in self.params:
            query+=str(param)
        excludeParamCount = len(self.excludeParams)
        if(excludeParamCount>0):
            #add the number of exclude params next to the \nor\ parameter
            query+=fr'\nor\{excludeParamCount}'
            for param in self.excludeParams:
                query+=str(param)
        return query
    
def get_server_list(stringQuery, max_servers=5000,timeout = 50):
    '''
    Returns information about servers that match the description of the query

    stringQuery: A Steam Server Query
    '''
    print(f'query : {stringQuery}')
    result =  steam_client.gameservers.get_server_list(stringQuery,max_servers,timeout)
    print(f'result : {result}')
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
    queryList.append(SteamServerQuery(params=[SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.GameTypePVE,SteamQueryParam.get_clan_size(4)],
    excludeParams=[SteamQueryParam.Secure,SteamQueryParam.GameTypeHC]))
    #PVE servers with no password, not hardcore and with a clan size different than 4
    queryList.append(SteamServerQuery(params=[SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.GameTypePVE],
    excludeParams=[SteamQueryParam.Secure,SteamQueryParam.GameTypeHC,SteamQueryParam.get_clan_size(4)]))
    #PVE servers that are HardCore with no passwords
    queryList.append(SteamServerQuery(params=[SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.GameTypePVE,SteamQueryParam.GameTypeHC],
    excludeParams=[SteamQueryParam.Secure]))
    for query in queryList:
        game_servers.extend(get_server_list(query.get_query()))
    return game_servers

 
sign_in()