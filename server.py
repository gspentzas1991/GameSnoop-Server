from gevent import monkey
monkey.patch_all()

from flask import Flask
from flask import request
import simple_steam_queries
from simple_steam_queries import SteamQueryParam
from simple_steam_queries import Logical
from simple_steam_queries import SteamServerQuery
from enum import Enum
from flask_cors import CORS
from dotenv import load_dotenv
import os

class GameType(Enum):
    PVE = 'pve'
    PVP = 'pvp'
    Hardcore = 'hc'
    ClanSize = 'CS'

app = Flask(__name__)
CORS(app,origins=['http://www.gamesnoop.gg','https://www.gamesnoop.gg','http://localhost:3000'])

@app.before_first_request
def startup():
    sign_in_steam_client()

#Flask Routing endpoints
@app.route("/",methods = ['GET'])
def home():
    return 'hello world'

@app.route("/servers",methods = ['GET'])
def servers():
    #gets the request parameters
    #TODO: add parameter validation
    serverName = request.args.get('serverName', '')
    clanSizeList = request.args.get('clanSize','').split(',')
    multiplayerModeList = request.args.get('serverType','').split(',')
    dedicated = request.args.get('dedicated', '')
    secure = request.args.get('secure', '')
    difficulty = request.args.get('difficulty', '')

    server_list = get_servers(serverName,clanSizeList,multiplayerModeList,dedicated,secure,difficulty)
    return server_list

@app.route("/allServers",methods = ['GET'])
def allServers():
    server_list = get_all_servers()
    return server_list

def get_servers(serverName='',clanSizeList=[],multiplayerModeList=[],dedicated='',secure='',difficulty=''):
    '''
    Generates lists of SteamQueryParam objects, to create a Steam Query based on the provided parameters

    Executes the query and returns a list of dictionary viewModels (see generate_server_model)
    '''
    server_list = {'servers':[]}
    #TODO:We don't include empty servers by default. Might change later to receive the value from filters
    #parameters that we want to apply on the steam query
    queryParams = [SteamQueryParam.NotEmpty,SteamQueryParam.get_appId_param(1604030)]
    #parameters of servers we want to be excluded from the steam query
    excludeParams = []
    if serverName :
        queryParams.append(SteamQueryParam.get_servername_param(serverName))
    #for each value of clanSizeList we're going to create a SteamQueryParam and apply a logical OR on them
    #that way we get servers that have any of the supplied clan sizes
    acceptedClanSizes = []
    for clanSize in range(int(clanSizeList[0]),int(clanSizeList[1])+1):
        clanSizeGametype = f'{GameType.ClanSize.value}{clanSize}'
        acceptedClanSizes.append(SteamQueryParam.get_gametype_param(clanSizeGametype))
    clanSizeQuery = SteamQueryParam.generate_logical_query(Logical.OR,acceptedClanSizes)
    queryParams.append(clanSizeQuery)
    #for each value of multiplayerTypeList we're going to create a SteamQueryParam and apply a logical OR on them
    #that way we get servers that have any of the multiplayer modes
    acceptedMultiplayerTypes = []
    for serverType in multiplayerModeList:
        if serverType == 'PvP':
            acceptedMultiplayerTypes.append(SteamQueryParam.get_gametype_param(GameType.PVP.value))
        elif serverType == 'PvE':
            acceptedMultiplayerTypes.append(SteamQueryParam.get_gametype_param(GameType.PVE.value))
    multiplayerTypeQuery = SteamQueryParam.generate_logical_query(Logical.OR,acceptedMultiplayerTypes)
    queryParams.append(multiplayerTypeQuery)
    #adds query parameters for any other server options provided
    if dedicated=='Dedicated':
        queryParams.append(SteamQueryParam.Dedicated)
    elif dedicated=='Public':
        excludeParams.append(SteamQueryParam.Dedicated)
    if secure=='Locked':
        queryParams.append(SteamQueryParam.Secure)
    elif secure=='Open':
        excludeParams.append(SteamQueryParam.Secure)
    if difficulty=='Hardcore':
        queryParams.append(SteamQueryParam.get_gametype_param(GameType.Hardcore.value))
    elif difficulty=='Casual':
        excludeParams.append(SteamQueryParam.get_gametype_param(GameType.Hardcore.value))
    queryParams.append(SteamQueryParam.generate_logical_query(Logical.NOR,excludeParams))
    query = SteamServerQuery(params=queryParams).get_query()
    game_servers=simple_steam_queries.get_server_list(query,max_servers=5000)

    for server in game_servers: 
        server_list['servers'].append(generate_server_model(server))
    return server_list

def get_all_servers():
    '''
    Calls the necessary requests to get every single server of the game (excluding empty servers by default)

    Returns a list of dictionary viewModels (see generate_server_model)
    '''
    server_list = {'servers':[]}
    game_servers=get_complete_server_list()
    for server in game_servers:
        server_list['servers'].append(generate_server_model(server))
    return server_list

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
    params = [SteamQueryParam.Secure,SteamQueryParam.NotEmpty]
    queryList.append(SteamServerQuery(params))
    #full servers (any kind)
    params = SteamQueryParam.generate_logical_query(Logical.NOR,[SteamQueryParam.NotFull])
    queryList.append(SteamServerQuery(params))
    #PVP servers with no password, who are not full
    params = [SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.get_gametype_param(GameType.PVP)]
    params.append(SteamQueryParam.generate_logical_query(Logical.NOR,[SteamQueryParam.Secure]))
    queryList.append(SteamServerQuery(params))
    #pve servers of clan size 4 who are not full, with no password and not hardcore
    params = [SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.get_gametype_param(GameType.PVE),SteamQueryParam.get_gametype_param(f'{GameType.ClanSize.value}4')]   
    params.append(SteamQueryParam.generate_logical_query(Logical.NOR,[SteamQueryParam.Secure,SteamQueryParam.get_gametype_param(GameType.Hardcore)]))
    queryList.append(SteamServerQuery(params))
    #PVE servers with no password, not hardcore and with a clan size different than 4
    params = [SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.get_gametype_param(GameType.PVP)]  
    params.append(SteamQueryParam.generate_logical_query(Logical.NOR,[SteamQueryParam.Secure,SteamQueryParam.get_gametype_param(GameType.Hardcore),
        SteamQueryParam.get_gametype_param(f'{GameType.ClanSize.value}4')]))
    queryList.append(SteamServerQuery(params))
    #PVE servers that are HardCore with no passwords
    params = [SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.get_gametype_param(GameType.PVE),SteamQueryParam.get_gametype_param(GameType.Hardcore)]
    params.append(SteamQueryParam.generate_logical_query(Logical.NOR,[SteamQueryParam.Secure]))
    queryList.append(SteamServerQuery(params))
    for query in queryList:
        queryString = query.get_query()
        newServers = simple_steam_queries.get_server_list(queryString)
        if(newServers):
            game_servers.extend(newServers)
    return game_servers

def generate_server_model(steam_server):
    '''
    Generates a dictionary viewModel based on the server data received from steam

    Dictionary Keys: name, players,max_players,isSecure,isDedicated,isPVP,isPVE,isHardcore,
    '''
    serverObject = {
        'name':str(steam_server.get('name')),
        'players':int(steam_server.get('players')), 
        'max_players':int(steam_server.get('max_players')),
        'isSecure':bool(steam_server.get('secure')), 
        'isDedicated':bool(steam_server.get('dedicated')),
        'isPVP' : False,
        'isPVE' : False,
        'isHardcore':False
        }
    server_gametype = steam_server.get('gametype')
    if(server_gametype):
        for gametype in str(server_gametype).split(','):
            if gametype == 'hc':
                serverObject['isHardcore'] = True
            if gametype == 'pve':
                serverObject['isPVE'] = True
            if gametype == 'pvp':
                serverObject['isPVP'] = True
            if 'cs' in gametype:
                serverObject['clanSize'] = gametype.split('cs')[1]
    return serverObject

def sign_in_steam_client():
    load_dotenv('./server_secrets.env')
    steam_username=os.getenv('steamUser')
    steam_password = os.getenv('steamPass')
    simple_steam_queries.sign_in(steam_username,steam_password)

if __name__ == "__main__":
    app.run()