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
    #gets the name parameter of the request
    name = request.args.get('name', None)
    game_servers = []
    #each steam server request can return up to 20k servers, so we need to create multiple different queries and collect the results to get all servers
    #by default we ignore empty servers, this might turn into an option later (probably everything will be handled with frontent filters)
    queryList = []
    #password protected servers (any kind)
    queryList.append(SteamServerQuery(params=[SteamQueryParam.Secure,SteamQueryParam.NotEmpty],serverName=name))
    #full servers (any kind)
    queryList.append(SteamServerQuery(excludeParams=[SteamQueryParam.NotFull],serverName=name))
    #PVP servers with no password, who are not full
    queryList.append(SteamServerQuery(params=[SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.GameTypePVP],
    excludeParams=[SteamQueryParam.Secure],serverName=name))
    #pve servers of clan size 4 who are not full, with no password and not hardcore
    queryList.append(SteamServerQuery(params=[SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.GameTypePVE,SteamQueryParam.GameTypeCS4],
    excludeParams=[SteamQueryParam.Secure,SteamQueryParam.GameTypeHC],serverName=name))
    #PVE servers with no password, not hardcore and with a clan size different than 4
    queryList.append(SteamServerQuery(params=[SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.GameTypePVE],
    excludeParams=[SteamQueryParam.Secure,SteamQueryParam.GameTypeHC,SteamQueryParam.GameTypeCS4],serverName=name))
    #PVE servers that are HardCore with no passwords
    queryList.append(SteamServerQuery(params=[SteamQueryParam.NotFull,SteamQueryParam.NotEmpty,SteamQueryParam.GameTypePVE,SteamQueryParam.GameTypeHC],
    excludeParams=[SteamQueryParam.Secure],serverName=name))
    for query in queryList:
        game_servers.extend(steam_service.get_server_list(query.get_query()))
    for server in game_servers:
        server_list['servers'].append({'name':str(server['name']),'players':server['players'], 'max_players':server['max_players']})
    return server_list

if __name__ == "__main__":
    steam_service.sign_in()
    app.run(debug=True)