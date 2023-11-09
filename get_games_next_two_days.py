import bot
import psycopg2
from datetime import date, datetime, timedelta
import os

#Gets ALL upcoming games
def get_all_upcoming_matches(nba_game_list, nfl_game_list, nhl_game_list, startDate, endDate):
    for team, team_str in bot.nba_teams.items():
        nba_game_list.extend(bot.get_team_NBA_matches(team))

    for team, team_str in bot.nfl_teams.items():
        nfl_game_list.extend(bot.get_team_NFL_matches(team))

    for team, team_str in bot.nhl_teams.items():
        nhl_game_list.extend(bot.get_team_NHL_matches(team))

    nba_games = sorted(set(nba_game_list), key = lambda x: x[0])
    nfl_games = sorted(set(nfl_game_list), key=lambda x: x[0])
    nhl_games = sorted(set(nhl_game_list), key=lambda x: x[0])

    nba_games_today_and_tomorrow = []
    nfl_games_today_and_tomorrow = []
    nhl_games_today_and_tomorrow = []

    date_today = date.today().strftime("%m-%d-%Y")
    date_tomorrow = (date.today() + timedelta(1)).strftime("%m-%d-%Y")
    today_and_tomorrow = [date_today, date_tomorrow]

    #Getting all the games upcoming in the next 2 days

    for game in nba_games:
        if game[0].split(" ")[0] in today_and_tomorrow:
            nba_games_today_and_tomorrow.append(game)
            
    for game in nfl_games:
        if game[0].split(" ")[0] in today_and_tomorrow:
            nfl_games_today_and_tomorrow.append(game)
            
    for game in nhl_games:
        if game[0].split(" ")[0] in today_and_tomorrow:
            nhl_games_today_and_tomorrow.append(game)
    
    return nba_games_today_and_tomorrow, nfl_games_today_and_tomorrow, nhl_games_today_and_tomorrow

#Used to insert next two days of games
def insert_upcoming_games_to_db(nba_upcoming_games, nfl_upcoming_games, nhl_upcoming_games):
    conn_get_games = psycopg2.connect(
        database= os.environ.get('GamedayBot_database'),
        user= os.environ.get('GamedayBot_user'),
        password= os.environ.get('GamedayBot_password'),
        host= os.environ.get('GamedayBot_host'),
        port= os.environ.get('GamedayBot_port')
    )

    cur_get_games = conn_get_games.cursor()
    current_time = datetime.now()

    if len(nba_upcoming_games) != 0:
        nba_args_str = ','.join(cur_get_games.mogrify("(%s,%s,%s)", i).decode('utf-8')
                        for i in nba_upcoming_games)
        cur_get_games.execute("INSERT INTO nba_games VALUES " + (nba_args_str) + " ON CONFLICT(start_time, visiting_team, home_team) DO NOTHING")
        conn_get_games.commit()
        print(f"[{current_time}]: Insert of {len(nba_upcoming_games)} NBA attempted.")

    if len(nfl_upcoming_games) != 0:
        nfl_args_str = ','.join(cur_get_games.mogrify("(%s,%s,%s)", i).decode('utf-8')
                        for i in nfl_upcoming_games)
        cur_get_games.execute("INSERT INTO nfl_games VALUES " + (nfl_args_str) + " ON CONFLICT(start_time, visiting_team, home_team) DO NOTHING")
        conn_get_games.commit()
        print(f"[{current_time}]: Insert of {len(nfl_upcoming_games)} NFL games attempted.")

    if len(nhl_upcoming_games) != 0:
        nhl_args_str = ','.join(cur_get_games.mogrify("(%s,%s,%s)", i).decode('utf-8')
                        for i in nhl_upcoming_games)
        cur_get_games.execute("INSERT INTO nhl_games VALUES " + (nhl_args_str) + " ON CONFLICT(start_time, visiting_team, home_team) DO NOTHING")
        conn_get_games.commit()
        print(f"[{current_time}]: Insert of {len(nhl_upcoming_games)} NHL games attempted.")

    cur_get_games.close()
    conn_get_games.close()

#Running functions
nba_game_list = []
nfl_game_list = []
nhl_game_list = []

startDate = date.today()
endDate = date(date.today().year + 1, 12, 31)
nba_upcoming_games, nfl_upcoming_games, nhl_upcoming_games = get_all_upcoming_matches(nba_game_list, nfl_game_list, nhl_game_list, startDate, endDate)
insert_upcoming_games_to_db(nba_upcoming_games, nfl_upcoming_games, nhl_upcoming_games)
