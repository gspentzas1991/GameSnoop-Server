from gevent import monkey
monkey.patch_all()

from flask import Flask
from flask import request
from steam_service import SteamServerQuery
from steam_service import SteamQueryParam
import steam_service



app = Flask(__name__)

#Flask Routing
@app.route("/servers",methods = ['GET'])
def servers():
    server_list = {'servers':[]}
    #gets the request parameters
    #TODO: add parameter validation
    serverName = request.args.get('serverName', None)
    clanSizeList = request.args.get('clanSize',[]).split(',')
    serverTypeList = request.args.get('serverType',[]).split(',')
    #generate the steam server query based on the received parameters
    #TODO:We don't include empty servers by default. Might change later to receive the value from filters
    queryParams = [SteamQueryParam.NotEmpty]
    excludeParams = []
    #TODO: fix the string booleans (due to rest api returning them as lowercase booleans)
    remainingClanSizes = [SteamQueryParam.GameTypeCS4,SteamQueryParam.GameTypeCS2]
    for clanSize in clanSizeList:
        if clanSize == 'Two':
            #queryParams.append(SteamQueryParam.GameTypeCS2)
            remainingClanSizes.remove(SteamQueryParam.GameTypeCS2)
        elif clanSize == 'Four':
            #queryParams.append(SteamQueryParam.GameTypeCS4)
            remainingClanSizes.remove(SteamQueryParam.GameTypeCS4)
    #any clan sizes that we didn't get, we'll remove from results
    for clanSize in remainingClanSizes:
        excludeParams.append(clanSize)

    remainingServerTypes = [SteamQueryParam.GameTypePVE,SteamQueryParam.GameTypePVP,SteamQueryParam.Secure,SteamQueryParam.GameTypeHC]
    for serverType in serverTypeList:
        if serverType == 'PvP':
            #queryParams.append(SteamQueryParam.GameTypePVP)
            remainingServerTypes.remove(SteamQueryParam.GameTypePVP)
        elif serverType == 'PvE':
            #queryParams.append(SteamQueryParam.GameTypePVE)
            remainingServerTypes.remove(SteamQueryParam.GameTypePVE)
        elif clanSize == 'Dedicated':
            #queryParams.append(SteamQueryParam.Secure)
            remainingServerTypes.remove(SteamQueryParam.Secure)
        elif clanSize == 'Hardcore':
            #queryParams.append(SteamQueryParam.GameTypeHC)
            remainingServerTypes.remove(SteamQueryParam.GameTypeHC)
    #any clan sizes that we didn't get, we'll remove from results
    for serverTypes in remainingServerTypes:
        excludeParams.append(serverTypes)

    query = SteamServerQuery(params=queryParams,excludeParams=excludeParams,serverName=serverName).get_query()
    print(query)
    game_servers=steam_service.get_server_list(query)

    for server in game_servers:
        print(server)
        server_list['servers'].append({'name':str(server['name']),'players':server['players'], 'max_players':server['max_players']})

    return server_list

@app.route("/allServers",methods = ['GET'])
def allServers():
    server_list = {'servers':[]}
    game_servers=steam_service.get_complete_server_list()
    for server in game_servers:
        server_list['servers'].append({'name':str(server['name']),'players':server['players'], 'max_players':server['max_players']})
    return server_list

if __name__ == "__main__":
    steam_service.sign_in()
    app.run(debug=True)