from flask import Flask, request
from flask_cors import CORS
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
pd.set_option('display.precision', 2)

# Load data
all_players = pd.read_csv('all_players.csv')


##################################################################################
###  Notebook methods below
##################################################################################

class PlayerNotFoundError(Exception):
    pass

def getPlayerID(player, df):
    playerID = df[df['Player'].str.lower() == player.strip().lower()]
    if playerID.empty:
        raise PlayerNotFoundError('Player not found')
    return playerID.iloc[0][1]

def lookupPlayer(playerName, n=1000):
    
    player = getPlayerID(playerName, all_players)
        
    url = f'https://gol.gg/players/player-matchlist/{player}/season-S13/split-Spring/tournament-ALL/'
    header = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
    }
    page = requests.get(url, headers=header).text
    doc = BeautifulSoup(page, "html.parser")
 
    df = pd.DataFrame()

    matches = doc.find_all('tr')[3:n + 2]
    for i in matches:
        td_list = i.find_all('td') 
        teams = td_list[6].text.split(' vs ')
        next_game = {
                        'Champion': td_list[0].text.strip(), 
                        'Result': td_list[1].text, 
                        'KDA': td_list[2].text,
                        'Kills': int(td_list[2].text.split('/')[0]),
                        'Duration': td_list[4].text,
                        'Date': td_list[5].text,
                        'Team1': teams[0],
                        'Team2': teams[1],
                    }
        df = pd.concat([df, pd.DataFrame.from_records([next_game])])
    
    team = pd.concat([df['Team1'], df['Team2']], axis=0).value_counts().index[0]
    df['Opponent'] = df.apply(lambda row: row['Team2'] if row['Team1'] == team else row['Team1'], axis=1)
    df.drop(columns=['Team1', 'Team2'], inplace=True)
    
    return df

# @param n: look at n most recent games only (optional argument)
def proj_kills(player, wins, losses, n=1000):
    df = lookupPlayer(player)[:n]
    df = df[df['Duration'] != '0']
    
    v_lst = (sorted(list(df[df['Result'] == 'Victory']['Kills'])))
    v_avg = sum(v_lst)/len(v_lst)
    d_lst = (sorted(list(df[df['Result'] == 'Defeat']['Kills'])))
    d_avg = sum(d_lst)/len(d_lst)
    
    return round(v_avg * wins + d_avg * losses, 2)


##################################################################################
###  Flask functionality below
##################################################################################

# Initialize Flask application
app = Flask(__name__)
CORS(app)

@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "API is up and running"}

@app.route('/lookup_player', methods=['POST'])
def lookup_player_route():
    try:
        data = request.json
        player = data.get('player')
        n = data.get('n', 1000)
        df = lookupPlayer(player, n)
        return {"player_data": df.to_dict(orient='records')}
    except PlayerNotFoundError:
        return {"error": "Player not found"}, 404
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/proj_kills', methods=['POST'])
def proj_kills_route():
    try:
        data = request.json
        player = data.get('player')
        wins = int(data.get('wins'))
        losses = int(data.get('losses'))
        n = data.get('n', 1000)
        return {"proj_kills": proj_kills(player, wins, losses, n)}
    except PlayerNotFoundError:
        return {"error": "Player not found"}, 404
    except Exception as e:
        return {"error": str(e)}, 500
    
@app.route('/player_info', methods=['POST'])
def player_info_route():
    try:
        data = request.json
        player = data.get('player')
        wins = int(data.get('wins'))
        losses = int(data.get('losses'))
        n = data.get('n', 1000)
        proj_kills_value = proj_kills(player, wins, losses, n)
        df = lookupPlayer(player, n)
        return {
            "proj_kills": proj_kills_value,
            "player_data": df.to_dict(orient='records')
        }
    except PlayerNotFoundError:
        return {"error": "Player not found"}, 404
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
