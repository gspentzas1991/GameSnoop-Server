from gevent import monkey
monkey.patch_all()

from flask import Flask
from flask import request
from steam_service import SteamServerQuery
from steam_service import SteamQueryParam
import steam_service
from flask_cors import CORS



app = Flask(__name__)
CORS(app, origins=['https://game-snoop.herokuapp.com'])


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
    queryParams = [SteamQueryParam.NotEmpty]
    #parameters of servers we want to be excluded from the steam query
    excludeParams = []
    if serverName :
        queryParams.append(SteamQueryParam.get_server_name(serverName))
    #for each value of clanSizeList we're going to create a SteamQueryParam and apply a logical OR on them
    #that way we get servers that have any of the supplied clan sizes
    acceptedClanSizes = []
    for clanSize in range(int(clanSizeList[0]),int(clanSizeList[1])+1):
        acceptedClanSizes.append(SteamQueryParam.get_clan_size(clanSize))
    clanSizeQuery = SteamQueryParam.generate_LogicalOR_query(acceptedClanSizes)
    queryParams.append(clanSizeQuery)
    #for each value of multiplayerTypeList we're going to create a SteamQueryParam and apply a logical OR on them
    #that way we get servers that have any of the multiplayer modes
    acceptedMultiplayerTypes = []
    for serverType in multiplayerModeList:
        if serverType == 'PvP':
            acceptedMultiplayerTypes.append(SteamQueryParam.GameTypePVP)
        elif serverType == 'PvE':
            acceptedMultiplayerTypes.append(SteamQueryParam.GameTypePVE)
    multiplayerTypeQuery = SteamQueryParam.generate_LogicalOR_query(acceptedMultiplayerTypes)
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
        queryParams.append(SteamQueryParam.GameTypeHC)
    elif difficulty=='Casual':
        excludeParams.append(SteamQueryParam.GameTypeHC)

    query = SteamServerQuery(params=queryParams,excludeParams=excludeParams).get_query()
    game_servers=steam_service.get_server_list(query)

    for server in game_servers: 
        server_list['servers'].append(generate_server_model(server))
    return server_list

def get_all_servers():
    '''
    Calls the necessary requests to get every single server of the game (excluding empty servers by default)

    Returns a list of dictionary viewModels (see generate_server_model)
    '''
    server_list = {'servers':[]}
    game_servers=steam_service.get_complete_server_list()
    for server in game_servers:
        server_list['servers'].append(generate_server_model(server))
    return server_list

def generate_server_model(steam_server):
    '''
    Generates a dictionary viewModel based on the server data received from steam

    Dictionary Keys: name, players,max_players,isSecure,isDedicated,isPVP,isPVE,isHardcore,
    '''
    serverObject = {
        'name':str(steam_server['name']),
        'players':steam_server['players'], 
        'max_players':steam_server['max_players'],
        'isSecure':steam_server['secure'], 
        'isDedicated':steam_server['dedicated'],
        'isPVP' : False,
        'isPVE' : False,
        'isHardcore':False
        }
    for gametype in steam_server['gametype'].split(','):
        if gametype == 'hc':
            serverObject['isHardcore'] = True
        if gametype == 'pve':
            serverObject['isPVE'] = True
        if gametype == 'pvp':
            serverObject['isPVP'] = True
        if 'cs' in gametype:
            serverObject['clanSize'] = gametype.split('cs')[1]
    return serverObject

if __name__ == "__main__":
    app.run(debug=True)