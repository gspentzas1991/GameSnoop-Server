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
    name = request.args.get('name', None)
    pvp = request.args.get('pvp',False)
    pve = request.args.get('pve',False)
    clan_size = int(request.args.get('clanSize','0'))
    secure = request.args.get('secure',False)
    #generate the steam server query based on the received parameters
    #TODO:We don't include empty servers by default. Might change later to receive the value from filters
    queryParams = [SteamQueryParam.NotEmpty]
    excludeParams = []
    #TODO: fix the string booleans (due to rest api returning them as lowercase booleans)
    if(pvp=='true'):
        queryParams.append(SteamQueryParam.GameTypePVP)
    if(pve=='true'):
        queryParams.append(SteamQueryParam.GameTypePVE)
    if(secure=='true'):
        queryParams.append(SteamQueryParam.Secure)
    else:
        excludeParams.append(SteamQueryParam.Secure)
    #TODO: fix clan_size parameter to work with any given number (or change it to only be cs2 or cs4)
    if(clan_size>0):
        queryParams.append(SteamQueryParam.GameTypeCS4)
    query = SteamServerQuery(params=queryParams,excludeParams=excludeParams,serverName=name).get_query()
    game_servers=steam_service.get_server_list(query)

    for server in game_servers:
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