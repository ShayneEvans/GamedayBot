import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import requests
import json
from datetime import date, datetime, timedelta
from dateutil import parser
from io import BytesIO
import typing
import psycopg2
import os
from json.decoder import JSONDecodeError
import pytz
from typing import Literal, Optional

#Connecting to database
try:
    conn = psycopg2.connect(
        database= os.environ.get('GamedayBot_database'),
        user= os.environ.get('GamedayBot_user'),
        password= os.environ.get('GamedayBot_password'),
        host = os.environ.get('GamedayBot_host'),
        port = os.environ.get('GamedayBot_port'),
        keepalives=1,
        keepalives_idle=1
        )
    cur = conn.cursor()

except psycopg2.Error as e:
    print("Error connecting to the database:", e)

cur = conn.cursor()

nba_teams = {
    'ATL': 'Atlanta Hawks',
    'BKN': 'Brooklyn Nets',
    'BOS': 'Boston Celtics',
    'CHA': 'Charlotte Hornets',
    'CHI': 'Chicago Bulls',
    'CLE': 'Cleveland Cavaliers',
    'DAL': 'Dallas Mavericks',
    'DEN': 'Denver Nuggets',
    'DET': 'Detroit Pistons',
    'GSW': 'Golden State Warriors',
    'HOU': 'Houston Rockets',
    'IND': 'Indiana Pacers',
    'LAC': 'Los Angeles Clippers',
    'LAL': 'Los Angeles Lakers',
    'MEM': 'Memphis Grizzlies',
    'MIA': 'Miami Heat',
    'MIL': 'Milwaukee Bucks',
    'MIN': 'Minnesota Timberwolves',
    'NOP': 'New Orleans Pelicans',
    'NYK': 'New York Knicks',
    'OKC': 'Oklahoma City Thunder',
    'ORL': 'Orlando Magic',
    'PHI': 'Philadelphia 76ers',
    'PHX': 'Phoenix Suns',
    'POR': 'Portland Trailblazers',
    'SAC': 'Sacramento Kings',
    'SAS': 'San Antonio Spurs',
    'TOR': 'Toronto Raptors',
    'UTA': 'Utah Jazz',
    'WAS': 'Washington Wizards'}

nfl_teams = {
    '22': 'Arizona Cardinals',
    '1': 'Atlanta Falcons',
    '33': 'Baltimore Ravens',
    '2': 'Buffalo Bills',
    '29': 'Carolina Panthers',
    '3': 'Chicago Bears',
    '4': 'Cincinnati Bengals',
    '5': 'Cleveland Browns',
    '6': 'Dallas Cowboys',
    '7': 'Denver Broncos',
    '8': 'Detroit Lions',
    '9': 'Green Bay Packers',
    '34': 'Houston Texans',
    '11': 'Indianapolis Colts',
    '30': 'Jacksonville Jaguars',
    '12': 'Kansas City Chiefs',
    '13': 'Las Vegas Raiders',
    '24': 'Los Angeles Chargers',
    '14': 'Los Angeles Rams',
    '15': 'Miami Dolphins',
    '16': 'Minnesota Vikings',
    '17': 'New England Patriots',
    '18': 'New Orleans Saints',
    '19': 'New York Giants',
    '20': 'New York Jets',
    '21': 'Philadelphia Eagles',
    '23': 'Pittsburgh Steelers',
    '25': 'San Francisco 49ers',
    '26': 'Seattle Seahawks',
    '27': 'Tampa Bay Buccaneers',
    '10': 'Tennessee Titans',
    '28': 'Washington Commanders'}

nhl_teams = {
    'ANA': 'Anaheim Ducks',
    'ARI': 'Arizona Coyotes',
    'BOS': 'Boston Bruins',
    'BUF': 'Buffalo Sabres',
    'CGY': 'Calgary Flames',
    'CAR': 'Carolina Hurricanes',
    'CHI': 'Chicago Blackhawks',
    'COL': 'Colorado Avalanche',
    'CBJ': 'Columbus Blue Jackets',
    'DAL': 'Dallas Stars',
    'DET': 'Detroit Red Wings',
    'EDM': 'Edmonton Oilers',
    'FLA': 'Florida Panthers',
    'LAK': 'Los Angeles Kings',
    'MIN': 'Minnesota Wild',
    'MTL': 'Montreal Canadiens',
    'NSH': 'Nashville Predators',
    'NJD': 'New Jersey Devils',
    'NYI': 'New York Islanders',
    'NYR': 'New York Rangers',
    'OTT': 'Ottawa Senators',
    'PHI': 'Philadelphia Flyers',
    'PIT': 'Pittsburgh Penguins',
    'SJS': 'San Jose Sharks',
    'SEA': 'Seattle Kraken',
    'STL': 'St. Louis Blues',
    'TBL': 'Tampa Bay Lightning',
    'TOR': 'Toronto Maple Leafs',
    'VAN': 'Vancouver Canucks',
    'VGK': 'Vegas Golden Knights',
    'WSH': 'Washington Capitals',
    'WPG': 'Winnipeg Jets'}

#Class used to obtain cs2 teams
class cs2Teams:
    def __init__(self):
        self.teams = self.get_cs2_teams_dict()

    #Creates a dictionary from team_id and team_name columns from cs2_teams in database
    def get_cs2_teams_dict(self):
        select_statement = "SELECT team_id, team_name FROM cs2_teams"
        cur.execute(select_statement)
        result = cur.fetchall()
        cs2_teams = dict(result)

        return cs2_teams

    #Every minute check the database to see if there are new teams and then update the dictionary with those temas
    #so they appear in the autocomplete
    @tasks.loop(minutes=1440)
    async def update_cs2_teams_dict(self):
        self.teams = self.get_cs2_teams_dict()

#cs2Teams object contains self updating dictionary of team ids and team names
cs2_data = cs2Teams()

reminder_times = {
    5: 'Remind me 5 minutes before the game starts',
    10: 'Remind me 10 minutes before the game starts',
    15: 'Remind me 15 minutes before the game starts',
    20: 'Remind me 20 minutes before the game starts',
    30: 'Remind me 30 minutes before the game starts',
    60: 'Remind me 1 hour before the game starts',
    90: 'Remind me 90 minutes before the game starts',
    120: 'Remind me 2 hours before the game starts',
    180: 'Remind me 3 hours before the game starts',
    360: 'Remind me 6 hours before the game starts',
    720: 'Remind me 12 hours before the game starts',
    1440: 'Remind me a day before the game starts'}

est_time_zone = pytz.timezone('US/Eastern')

#Used to convert dates to a uniform standard across all leagues
def convert_date(date):
    string_to_datetime = parser.parse(date)

    datetime_est = string_to_datetime.astimezone(est_time_zone)

    # Determine if AM or PM
    hours = datetime_est.strftime("%H")
    if int(hours) >= 12:
        setting = " PM EST"
    else:
        setting = " AM EST"

    readable_date = datetime_est.strftime("%m-%d-%Y") + datetime_est.strftime(" %I:%M") + setting
    return readable_date

#Used to sort nba game dates
def sort_dates(date_string):
    date_str = date_string[0].replace(' EST', '')  # Remove 'EST' before parsing
    return datetime.strptime(date_str, '%m-%d-%Y %I:%M %p')

#Gets the reminder time in format suitable for database (string Y-m-d H:M:S)
def get_game_reminder_time(game_start_time, remind_time_in_mins):
    game_start_time_dt = game_start_time - timedelta(minutes = remind_time_in_mins)
    game_start_time_string = game_start_time_dt.strftime('%Y-%m-%d %H:%M:%S')
    return game_start_time_dt, game_start_time_string

#Gets the upcoming games and sets reminders in next 24 hours for a user when they choose to start following a team. Also updates reminder times in same league if following multiple teams in league
def set_upcoming_game_reminder_times(league, teams_query_idx, remind_times_query_idx, user_id):
    #User specified, must be getting games for a new user or if they started following a new league
    id_query = "SELECT * FROM users WHERE user_id = %s"
    cur.execute(id_query, (user_id,))
    user = [cur.fetchone()]
    user_followed_teams_tuple = tuple(user[0][teams_query_idx].split(","))

    #Getting all upcoming games for each league
    league_games = league +"_games"
    if league_games != "cs2_games":
	upcoming_games = f"SELECT * FROM {league_games} WHERE start_time <= NOW() + INTERVAL '2 DAY'::INTERVAL AND (visiting_team IN {str(user_followed_teams_tuple)} OR home_team IN {str(user_followed_teams_tuple)})"
    else:
        upcoming_games = f"SELECT * FROM {league_games} WHERE start_time <= NOW() + INTERVAL '2 DAY'::INTERVAL AND (team_one IN {str(user_followed_teams_tuple)} OR team_two IN {str(user_followed_teams_tuple)})"
    cur.execute(upcoming_games)
    upcoming_games_query_result = cur.fetchall()

    #If there are teams the user follows, obtain that list
    if user[0][teams_query_idx] is not None:
        followed_league_teams = list(user[0][teams_query_idx].split(","))
    
    current_date = datetime.strptime(datetime.now().strftime("%Y-%m-%dT%H:%M"), "%Y-%m-%dT%H:%M")

    #Iterating through all games
    for game in upcoming_games_query_result:
        #obtaining game remind time in datetime format and in string format
        game_remind_time_dt, game_remind_time_string = get_game_reminder_time(game[0], user[0][remind_times_query_idx])
        #If past the remind time, do not set it.
        if current_date < game_remind_time_dt:
            insert_statement = "INSERT INTO reminders (user_id, remind_time, visiting_team, home_team, league, minutes_from_start_time) VALUES (%s, %s, %s, %s, %s, %s)"
            values = (user[0][0], game_remind_time_string, game[1], game[2], league.upper(), user[0][remind_times_query_idx],)
            #Checks if a reminder has been set for this upcoming game, an insert will not take place if true
            check_if_exists = "SELECT count(*) FROM reminders WHERE user_id = %s AND visiting_team = %s AND home_team = %s AND remind_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
            cur.execute(check_if_exists, (user[0][0], game[1], game[2],))
            #If this reminder doesn't exist add it to reminders
            if cur.fetchone()[0] == 0:
                cur.execute(insert_statement, values)
                conn.commit()
                print(f"{league} Games added to reminders")
            else:
                print("Insert failed, duplicate entry or update to remind time needed")

#Used when a user updates the reminder time, updates all existing valid reminders they have set to use the new time
def update_reminder_time_on_reminders_table(user_id, new_time, league):
    #Used to output message to user on the success of the updates
    update_success = 0
    update_error = 0
    #Obtains all reminders that are still coming
    reminders_query = "SELECT * FROM reminders WHERE user_id = %s AND league = %s AND remind_time >= date(timezone('EST', NOW()))"
    cur.execute(reminders_query, (user_id,league,))
    reminders_query_result = cur.fetchall()

    for reminder in reminders_query_result:
        #Gets the new reminder time for the game by subtracting the old reminder time from the new reminder time and subtracting that from the date time reminder
        if league != "CS2":
            game_start_time_query = f"SELECT start_time FROM {league.lower()}_games WHERE visiting_team = %s AND home_team = %s AND start_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
        else:
            game_start_time_query = f"SELECT start_time FROM {league.lower()}_games WHERE team_one = %s AND team_two = %s AND start_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
        values = (reminder[2], reminder[3],)
        cur.execute(game_start_time_query, values)
        game_start_time = cur.fetchone()
        new_game_remind_time = game_start_time[0] - timedelta(minutes = new_time)
        
	#if setting reminder that would have already happened, delete record
        current_date = datetime.strptime(datetime.now().strftime("%Y-%m-%dT%H:%M"), "%Y-%m-%dT%H:%M")
        if current_date < new_game_remind_time:
            update_statement = "UPDATE reminders SET remind_time = %s, minutes_from_start_time = %s WHERE user_id = %s AND remind_time = %s AND visiting_team = %s AND home_team = %s"
            values = (new_game_remind_time, new_time, user_id, reminder[1], reminder[2], reminder[3],)
            cur.execute(update_statement, values)
            conn.commit()
            update_success = 1
        #New reminder time already passed, reminder will not work
        else:
            update_error = 1

    #Returning message to user
    if update_success == 1 and update_error == 0:
        return "All previous reminders were successfully updated!"
    elif update_success == 0 and update_error == 1:
        return "No previously set reminders were updated, this is because the new reminder time has already passed. Old reminder time will be used for these games but games moving forward will use the new remind time."
    else:
        return "Some previously set reminders were unable to be updated because the new remind time has already passed. Old reminder time will be used for these games only."

#Function used to insert a new user or update an existing one in the users table
def insert_or_update_user(user_id, team_id, remind_time, league):
    league_teams = f"{league}_teams"
    league_remind_time = f"{league}_remind_time"
    team_name = ""
    remind_string = ""
    teams_query_idx = 0
    remind_times_query_idx = 0
    update_reminder_times_msg = ""

    if league == "nba":
        team_name = nba_teams[team_id]
        remind_string = reminder_times[remind_time]
        teams_query_idx = 1
        remind_times_query_idx = 2
    elif league == "nfl":
        team_name = nfl_teams[team_id]
        remind_string = reminder_times[remind_time]
        teams_query_idx = 3
        remind_times_query_idx = 4
    elif league == "nhl":
        team_name = nhl_teams[team_id]
        remind_string = reminder_times[remind_time]
        teams_query_idx = 5
        remind_times_query_idx = 6
    elif league == "cs2":
        team_name = cs2_data.teams[team_id]
        remind_string = reminder_times[remind_time]
        teams_query_idx = 7
        remind_times_query_idx = 8

    #Query to see if user already in database or not
    id_query = "SELECT * FROM users WHERE user_id = %s"
    cur.execute(id_query, (user_id,))
    id_query_result = cur.fetchone()

    #Formatting the team name for output message
    if league != "cs2":
        msg_team_name = f"the {team_name}"
    else:
        msg_team_name = team_name

    #If not in database add user with entered team and remind time
    if id_query_result is None:
        insert_statement = f"INSERT INTO users (user_id, {league_teams}, {league_remind_time}) VALUES (%s, %s, %s)"
        values = (user_id, team_id + ",", remind_time)
        cur.execute(insert_statement, values)
        conn.commit()
        set_upcoming_game_reminder_times(league, teams_query_idx, remind_times_query_idx, user_id)
        return f"Now receiving reminders for {msg_team_name} {remind_string[10:]}."
    #User already in database but adding reminders for different leagues
    elif id_query_result[teams_query_idx] is None:
        update_statement = f"UPDATE users SET {league_teams} = %s, {league_remind_time} = %s WHERE user_id = %s"
        values = (team_id + ",", remind_time, user_id)
        cur.execute(update_statement, values)
        conn.commit()
        #Will add reminders for the upcoming games of all teams that the user follows including the just newly added team
        set_upcoming_game_reminder_times(league, teams_query_idx, remind_times_query_idx, user_id)
        return f"Now receiving reminders for {msg_team_name} {remind_string[10:]}. {update_reminder_times_msg}"
    #User already follows teams and has reminders set,they want to follow another team and possibly want different reminder time
    else:
        new_team = False
        #Getting the VARCHAR of teams that the user follows, has this format string: TEAM1,TEAM2,TEAM3,....
        updated_reminder_teams_string = id_query_result[teams_query_idx]
        #If team user wants to follow is not in the string then add it
        if team_id not in updated_reminder_teams_string.split(","):
            updated_reminder_teams_string = f"{updated_reminder_teams_string}{team_id},"

        #If both entered team and remind time are different from ones on database update them
        if updated_reminder_teams_string != id_query_result[teams_query_idx] and remind_time != id_query_result[remind_times_query_idx]:
            update_statement = f"UPDATE users SET {league_teams} = %s, {league_remind_time} = %s WHERE user_id = %s"
            values = (updated_reminder_teams_string, remind_time, user_id)
            cur.execute(update_statement, values)
            conn.commit()
            set_upcoming_game_reminder_times(league, teams_query_idx, remind_times_query_idx, user_id)
            update_reminder_times_msg = update_reminder_time_on_reminders_table(user_id, remind_time, league.upper())
            return f"Now receiving reminders for {msg_team_name} {remind_string[10:]}. {update_reminder_times_msg}"

        #If only remind time is different change it also is updated in the reminders table
        elif updated_reminder_teams_string == id_query_result[teams_query_idx] and remind_time != id_query_result[remind_times_query_idx]:

            update_statement = f"UPDATE users SET {league_remind_time} = %s WHERE user_id = %s"
            values = (remind_time, user_id)
            cur.execute(update_statement, values)
            conn.commit()
            set_upcoming_game_reminder_times(league, teams_query_idx, remind_times_query_idx, user_id)
            update_reminder_times_msg = update_reminder_time_on_reminders_table(user_id, remind_time, league.upper())
            return f"Remind time successfully changed to {remind_string[10:]} for {msg_team_name}. {update_reminder_times_msg}"

        #User wants to get reminders for a new team
        elif updated_reminder_teams_string != id_query_result[teams_query_idx] and remind_time == id_query_result[remind_times_query_idx]:
            update_statement = f"UPDATE users SET {league_teams} = %s WHERE user_id = %s"
            values = (updated_reminder_teams_string, user_id)
            cur.execute(update_statement, values)
            conn.commit()
            #Will add reminders for the upcoming games of all teams that the user follows including the just newly added team
            set_upcoming_game_reminder_times(league, teams_query_idx, remind_times_query_idx, user_id)
            return f"Now receiving reminders for {msg_team_name} {remind_string[10:]}."

        else:
            set_upcoming_game_reminder_times(league, teams_query_idx, remind_times_query_idx, user_id)
            return f"UPDATE not made, you already receive game reminders for {msg_team_name} {remind_string[10:]}."

#Function used to remove reminders for a user for a specific team
def remove_reminders(user_id, team_id, league):
    league_teams = f"{league}_teams"
    team_name = ""
    teams_query_idx = 0

    if league == "nba":
        team_name = nba_teams[team_id]
        teams_query_idx = 1
    elif league == "nfl":
        team_name = nfl_teams[team_id]
        teams_query_idx = 3
    elif league == "nhl":
        team_name = nhl_teams[team_id]
        teams_query_idx = 5
    elif league == "cs2":
        team_name = cs2_data.teams[team_id]
        teams_query_idx = 7

    #Query to see if user already in database or not
    id_query = "SELECT * FROM users WHERE user_id = %s"
    cur.execute(id_query, (user_id,))
    id_query_result = cur.fetchone()

    #Formatting the team name and league name for output message
    if league != "cs2":
        msg_team_name = f"the {team_name}"
        msg_league_name = f"the {league.upper()}"
    else:
        msg_team_name = team_name
        msg_league_name = league.upper()

    #If reminders have been set for this team remove them
    if team_id in id_query_result[teams_query_idx]:
        updated_reminder_teams_bit_string = id_query_result[teams_query_idx]
        updated_reminder_teams_bit_string = updated_reminder_teams_bit_string.replace(team_id + ",", "")
        update_statement = f"UPDATE users SET {league_teams} = %s WHERE user_id = %s"
        values = (updated_reminder_teams_bit_string, user_id)
        cur.execute(update_statement, values)
        conn.commit()
        delete_statement = "DELETE FROM reminders WHERE user_id = %s AND home_team = %s OR visiting_team = %s"
        values = (user_id, team_id, team_id,)
        cur.execute(delete_statement, values)
        conn.commit()
        return f"Reminders removed for {msg_team_name}"
    #User has no reminders for the selected team
    elif team_id not in id_query_result[teams_query_idx]:
        return f"You do not have any reminders set for {msg_team_name}"
    #User has no reminders for the specified league.
    elif id_query_result[teams_query_idx] is None:
        return f"You do not have any reminders set for {msg_league_name}"
    # User does not exist in database
    elif id_query_result is None:
        return "You do not have any reminders set for any leagues."

#Function used for the /remove_all_reminders slash command. Removes all reminders for a user
def remove_all_reminders_fn(user_id, league):
    #Query to see if user already in database or not
    id_query = "SELECT * FROM users WHERE user_id = %s"
    cur.execute(id_query, (user_id,))
    id_query_result = cur.fetchone()
    #Valid reminders have been set for this league and should be removed
    if league == "NBA" and id_query_result[1] is not None:
        update_statement = "UPDATE users SET nba_teams = %s, nba_remind_time = %s WHERE user_id = %s"
        values = (None, None, user_id)
        cur.execute(update_statement, values)
        conn.commit()
        delete_statement = "DELETE FROM reminders WHERE user_id = %s and league = %s"
        values = (user_id, league,)
        cur.execute(delete_statement, values)
        conn.commit()
        return f"All NBA reminders have been successfully removed"
    #No reminders have been set for this league, return error message
    elif league == "NBA" and id_query_result[1] is None:
        return "You have no reminders set for any NBA teams."
    #Valid reminders have been set for this league and should be removed
    elif league == "NFL" and id_query_result[3] is not None:
        update_statement = "UPDATE users SET nfl_teams = %s, nfl_remind_time = %s WHERE user_id = %s"
        values = (None, None, user_id)
        cur.execute(update_statement, values)
        conn.commit()
        delete_statement = "DELETE FROM reminders WHERE user_id = %s and league = %s"
        values = (user_id, league,)
        cur.execute(delete_statement, values)
        conn.commit()
        return "All NFL reminders have been successfully removed"
    #No reminders have been set for this league, return error message
    elif league == "NFL" and id_query_result[3] is None:
        return "You have no reminders set for any NFL teams."
    #Valid reminders have been set for this league and should be removed
    elif league == "NHL" and id_query_result[5] is not None:
        update_statement = "UPDATE users SET nhl_teams = %s, nhl_remind_time = %s WHERE user_id = %s"
        values = (None, None, user_id)
        cur.execute(update_statement, values)
        conn.commit()
        delete_statement = "DELETE FROM reminders WHERE user_id = %s and league = %s"
        values = (user_id, league,)
        cur.execute(delete_statement, values)
        conn.commit()
        return "All NHL reminders have been successfully removed"
    #No reminders have been set for this league, return error message
    elif league == 'NHL' and id_query_result[5] is None:
        return "You have no reminders set for any NHL teams."
    #Valid reminders have been set for this league and should be removed
    elif league == "CS2" and id_query_result[5] is not None:
        update_statement = "UPDATE users SET cs2_teams = %s, CS2_remind_time = %s WHERE user_id = %s"
        values = (None, None, user_id)
        cur.execute(update_statement, values)
        conn.commit()
        delete_statement = "DELETE FROM reminders WHERE user_id = %s and league = %s"
        values = (user_id, league,)
        cur.execute(delete_statement, values)
        conn.commit()
        return f"All CS2 reminders have been successfully removed"
    #No reminders have been set for this league, return error message
    elif league == "CS2" and id_query_result[5] is None:
        return "You have no reminders set for any CS2 teams."

    #Deleting all reminders
    elif league == 'ALL' and not all(followed_teams_list is None for followed_teams_list in (id_query_result[1], id_query_result[3], id_query_result[5], id_query_result[7])):
        update_statement = "DELETE FROM users where user_id = %s"
        values = (user_id,)
        cur.execute(update_statement, values)
        conn.commit()
        delete_statement = "DELETE FROM reminders WHERE user_id = %s"
        values = (user_id,)
        cur.execute(delete_statement, values)
        conn.commit()
        return f"User removed from database. All reminders have been successfully removed"
    else:
        return "You have no reminders for any leagues."

#Gets a list of all matches for a team
def get_team_NBA_matches(team_id):
    currentNBAYear = date.today().year
    #Endpoint obtained from https://github.com/rlabausa/nba-schedule-data
    #Try except block used to get correct year. When NBA season goes to next year will still be using the previous year, this is how the URL works
    try:
        NBA_json_data = requests.get(f"https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/{currentNBAYear}/league/00_full_schedule.json")
        NBA_json = json.loads(NBA_json_data.text)
    except JSONDecodeError as e:
        NBA_json_data = requests.get(f"https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/{currentNBAYear-1}/league/00_full_schedule.json")
        NBA_json = json.loads(NBA_json_data.text)
    nba_games_list = []

    #Getting all team games that have yet to be played with date
    for i in range(len(NBA_json['lscd'])):
        for j in range(len(NBA_json['lscd'][i]['mscd']['g'])):
            #Date when the game takes place
            game_date = NBA_json['lscd'][i]['mscd']['g'][j]['gdte']
            #Start time for the game if it has not occurred, Final otherwise, default EST
            game_status = NBA_json['lscd'][i]['mscd']['g'][j]['stt']
            #Visting team 3 letter abbreviation
            visiting_team = NBA_json['lscd'][i]['mscd']['g'][j]['v']['ta']
            #Home team 3 letter abbreviation
            home_team = NBA_json['lscd'][i]['mscd']['g'][j]['h']['ta']

            #If game hasn't been played, append it to list
            if game_status[-2:] == 'ET' or game_status == "TBD":
                if home_team == team_id or visiting_team == team_id:
                    game_start_time = game_date + " " + game_status
                    if game_status != "TBD":
                        game_start_time = convert_date(game_start_time)
                    
                    #Checking to make sure both are real NBA teams, avoid issue of EU pre season games.
                    if visiting_team in nba_teams and home_team in nba_teams:
                        nba_games_list.append((game_start_time, visiting_team, home_team))
    
    #Sorting nba games by date with function sort_dates
    sorted_nba_games_list = sorted(nba_games_list, key=sort_dates)
    return sorted_nba_games_list

#Used when sending user reminders, since it could be a reminder for any of the 3 leagues this is handeled dynamically with league name as a parameter
def user_upcoming_game(away_team_id, home_team_id, league, reminder_message):
    reminder_message_split_up = reminder_message.split("starts")
    reminder_message_split_up[1] = "".join("starts" + reminder_message_split_up[1])
    #Making sure logo can be found of team
    try:
        away = Image.open(f'{league}/{away_team_id}.png')
    except FileNotFoundError as e:
        away = Image.open(f'{league}/NO_LOGO.png')
    
    #Making sure logo can be found of team
    try:
        home = Image.open(f'{league}/{home_team_id}.png')
    except FileNotFoundError as e:
        home = Image.open(f'{league}/NO_LOGO.png')
    
    away = away.convert("RGBA")
    home = home.convert("RGBA")
    game_graphic = Image.open(league +"/GameTemplate.png")
    game_graphic = game_graphic.convert("RGBA")
    game_graphic.paste(away, (20, 40), away)
    game_graphic.paste(home, (490, 40), home)
    game_image = ImageDraw.Draw(game_graphic)
    font = ImageFont.truetype("arial.ttf", 25)
    _, _, w, h = game_image.textbbox((0, -360), reminder_message_split_up[0], font=font)
    game_image.text(((800-w)/2, (350-h)/2), reminder_message_split_up[0], font=font)
    _, _, w, h = game_image.textbbox((0, -415), reminder_message_split_up[1], font=font)
    game_image.text(((800-w)/2, (350-h)/2), reminder_message_split_up[1], font=font)
    return game_graphic

#Used to get the days, hours, minutes, and seconds until the start of the next game. This will be displayed at the top of all nextgame PIL images
def time_until_game(game_start_time):
    current_time = datetime.now().replace(microsecond=0)
    game_start_time_dt = datetime.strptime(game_start_time[:-4], "%m-%d-%Y %I:%M %p")
    #Difference between current time and the time the game starts
    delta = game_start_time_dt - current_time

    days = delta.days
    seconds = delta.seconds
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    #Exclude days if the game is happening today
    if days > 0:
        time_until_game_starts_msg = f"{days}d {hours}h {minutes}m {seconds}s"
    else:
        time_until_game_starts_msg = f"{hours}h {minutes}m {seconds}s"

    return time_until_game_starts_msg

def create_cs2_game_graphic(cs2_team_next_game, league):
    #Try/except just in case the team has no logo, return generic question mark logo if they do not
    try:
        team_one = Image.open(f"{league}/{cs2_team_next_game[1]}.png")
    except FileNotFoundError:
        team_one = Image.open(f"{league}/NO_LOGO.png")
    try:
        team_two = Image.open(f"{league}/{cs2_team_next_game[2]}.png")
    except FileNotFoundError:
        team_two = Image.open(f"{league}/NO_LOGO.png")

    team_one = team_one.convert("RGBA")
    team_two = team_two.convert("RGBA")
    game_graphic = Image.open(f"{league}/GameTemplate.png")
    game_graphic = game_graphic.convert("RGBA")
    game_graphic.paste(team_one, (20, 40), team_one)
    game_graphic.paste(team_two, (490, 40), team_two)
    game_image = ImageDraw.Draw(game_graphic)
    font = ImageFont.truetype("arial.ttf", 50)
    font_time_until_game = ImageFont.truetype("arial.ttf", 30)
    # Text box for the start time in EST
    _, _, w, h = game_image.textbbox((0, -350), cs2_team_next_game[0], font=font)
    game_image.text(((800 - w) / 2, (400 - h) / 2), cs2_team_next_game[0], font=font)

    # Getting the time until game start time msg in format: {days}d {hours}h {minutes}m {seconds}m
    time_until_game_msg = time_until_game(cs2_team_next_game[0])

    # Creating 2 seperate text boxes for "Game Starts in:" and the time until game message so they can be properly placed at top of PIL image and centered
    _, _, w2, h2 = game_image.textbbox((0, 380), "Game Starts in:", font=font_time_until_game)
    _, _, w3, h3 = game_image.textbbox((0, 290 + h2), time_until_game_msg, font=font_time_until_game)
    x2 = (800 - w2) / 2
    y2 = (400 - h2) / 2
    x3 = (800 - w3) / 2
    y3 = y2 + 25

    # Adding 'Game Starts in' text
    game_image.text((x2, y2), "Game Starts in:", font=font_time_until_game)

    # Adding the time until the game starts text
    game_image.text((x3, y3), time_until_game_msg, font=font_time_until_game)

    return game_graphic

#Used to display the next game of the team
def user_nextgame(league_games_list, league):
    upcoming_game_idx = 0
    for i in range(0, len(league_games_list)):
        if league == 'NBA':
            if league_games_list[i][0][-3:] == "TBD":
                break
        else:
            start_time = datetime.strptime(league_games_list[i][0][:-4], "%m-%d-%Y %I:%M %p")
            if datetime.now() >= start_time:
                if upcoming_game_idx +1 != len(league_games_list):
                    upcoming_game_idx += 1
                break

    away = Image.open(f"{league}/{league_games_list[upcoming_game_idx][1]}.png")
    away = away.convert("RGBA")
    home = Image.open(f"{league}/{league_games_list[upcoming_game_idx][2]}.png")
    home = home.convert("RGBA")
    game_graphic = Image.open(f"{league}/GameTemplate.png")
    game_graphic = game_graphic.convert("RGBA")
    game_graphic.paste(away, (20, 40), away)
    game_graphic.paste(home, (490, 40), home)
    game_image = ImageDraw.Draw(game_graphic)
    font = ImageFont.truetype("arial.ttf", 50)
    font_time_until_game = ImageFont.truetype("arial.ttf", 30)
    #Text box for the start time in EST
    _, _, w, h = game_image.textbbox((0, -350), league_games_list[upcoming_game_idx][0], font=font)
    game_image.text(((800-w)/2, (400-h)/2), league_games_list[upcoming_game_idx][0], font=font)

    #Getting the time until game start time msg in format: {days}d {hours}h {minutes}m {seconds}m
    time_until_game_msg =  time_until_game(league_games_list[upcoming_game_idx][0])

    #Creating 2 seperate text boxes for "Game Starts in:" and the time until game message so they can be properly placed at top of PIL image and centered
    _, _, w2, h2 = game_image.textbbox((0, 380), "Game Starts in:", font = font_time_until_game)
    _,_, w3, h3 = game_image.textbbox((0, 290 + h2), time_until_game_msg, font = font_time_until_game)
    x2 = (800 - w2) / 2
    y2 = (400 - h2) / 2
    x3 = (800 - w3) / 2
    y3 = y2 + 25

    #Adding 'Game Starts in' text
    game_image.text((x2, y2), "Game Starts in:", font = font_time_until_game)

    #Adding the time until the game starts text
    game_image.text((x3, y3), time_until_game_msg, font = font_time_until_game)

    return game_graphic

#https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c#apissitev2sportsfootballnflteamsteam_id
def get_team_NFL_matches(team_id):
    nfl_games_list = []
    current_date = datetime.strptime(datetime.now().strftime("%Y-%m-%dT%H:%M"), "%Y-%m-%dT%H:%M")

    NFL_json_data = requests.get(f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{str(team_id)}/schedule")
    NFL_json = json.loads(NFL_json_data.text)

    #Going over each game
    for i in range(0, len(NFL_json["events"])):
        game_start_time = NFL_json["events"][i]["date"]

        #Converting game start time to datetime to be compared with the current datetime, first must convert string to datetime then back to string then datetime again to get
        #correct format (ANNOYING).
        game_start_time_dt = datetime.strptime(game_start_time, "%Y-%m-%dT%H:%M%f%z")
        game_start_time_dt = datetime.strptime(game_start_time_dt.strftime("%Y-%m-%dT%H:%M"), "%Y-%m-%dT%H:%M")

        if game_start_time_dt >= current_date:
            game_start_time = convert_date(NFL_json["events"][i]["date"])
            game = NFL_json["events"][i]["name"]
            game = game.split(" at ")
            #Visting team ID obtained by using the team name
            visiting_team = list(nfl_teams.keys())[list(nfl_teams.values()).index(game[0])]
            #Home team ID obtained by using the team name
            home_team = list(nfl_teams.keys())[list(nfl_teams.values()).index(game[1])]
            if visiting_team in nfl_teams and home_team in nfl_teams:
                nfl_games_list.append((game_start_time, visiting_team, home_team))

    return nfl_games_list

def get_team_NHL_matches(team_id):
    # Variable for upcoming NHL matches
    upcoming_match_list = []

    # Requesting schedule of team and converting request object to json text
    NHL_json_data = requests.get(f"https://api-web.nhle.com/v1/club-schedule/{team_id}/week/now")
    NHL_json = json.loads(NHL_json_data.text)

    number_of_teams = len(NHL_json["games"])
    for i in range(0, number_of_teams):
	#Game happens in the future, can set reminders for it
        if (NHL_json["games"][i]["gameState"] == "FUT"):
            game_start_time = convert_date(NHL_json["games"][i]["startTimeUTC"])
            away_team = NHL_json["games"][i]["awayTeam"]["abbrev"]
            home_team = NHL_json["games"][i]["homeTeam"]["abbrev"]
            upcoming_match_list.append((game_start_time, away_team, home_team))

    return upcoming_match_list

#Get the next game for a cs2 team
def get_team_CS2_matches(team_id):
    select_statement = "SELECT * FROM cs2_games WHERE (team_one = %s or team_two = %s) AND start_time > NOW() ORDER BY start_time"
    values = (team_id, team_id,)
    cur.execute(select_statement, values)
    next_game = cur.fetchone()

    if next_game is not None:
        return list(next_game)
    else:
        return None

#Gets all reminders from database that need to be sent to users
def get_reminders():
    cur.execute("SELECT * FROM reminders")
    reminders = cur.fetchall()
    reminders_with_messages = []

    for reminder in reminders:
        if reminder[4] == "NBA":
            away_team = nba_teams[reminder[2]]
            home_team = nba_teams[reminder[3]]
        elif reminder[4] == "NFL":
            away_team = nfl_teams[reminder[2]]
            home_team = nfl_teams[reminder[3]]
        elif reminder[4] == "NHL":
            away_team = nhl_teams[reminder[2]]
            home_team = nhl_teams[reminder[3]]
        elif reminder[4] == "CS2":
            #Defaults to "TBA" if team does not exist in dictionary
            away_team = cs2_data.teams.get(reminder[2], "TBA")
            home_team = cs2_data.teams.get(reminder[3], "TBA")

        time_before_game = reminder_times[reminder[5]]
        time_before_game = " ".join(time_before_game.split()[2:4])
        reminder_message = f"{away_team} vs. {home_team} starts in {time_before_game}!"
        reminders_with_messages.append((reminder[0], reminder[1], reminder[2], reminder[3], reminder[4], reminder_message))

    return reminders_with_messages

def run_discord_bot():
    TOKEN = os.environ.get("GamedayBot_TOKEN")
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix = "!", intents=intents)

    @bot.command()
    @commands.dm_only()
    @commands.is_owner()
    async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object],
                   spec: Optional[Literal["~", "*", "^"]] = None) -> None:
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")
	
    @tasks.loop(seconds=15)
    async def send_reminders():
        reminders_to_send = get_reminders()
        delete_reminders = []
        delete_users = []
        for reminder in reminders_to_send:
            #If current time is past the reminder time or equal to it then send message to user!
            if datetime.now() >= reminder[1]:
                user = await bot.fetch_user(reminder[0])
                bytes_io_obj = BytesIO()
                user_upcoming_game(reminder[2], reminder[3], reminder[4], reminder[5]).save(bytes_io_obj, "PNG")
                bytes_io_obj.seek(0)
                #Added this incase users no longer have access to bot in server or DMs
                try:
                    await user.send(file=discord.File(fp=bytes_io_obj, filename="image.png"))
                except discord.Forbidden as e:
                    print(f"Forbidden error: {e} {user.id}, deleting user")
                    delete_users.append(reminder[0])


                delete_reminders.append((reminder[0], reminder[1], reminder[2], reminder[3]))

        #Deletes reminders that were successfully sent to users
        for reminder in delete_reminders:
            delete_statement = "DELETE FROM reminders WHERE user_id = %s AND remind_time = %s AND visiting_team = %s AND home_team = %s"
            values = (reminder[0], reminder[1], reminder[2], reminder[3],)
            cur.execute(delete_statement, values)
            conn.commit()

        #Deleting all users from database where it is impossible to send messages to them
        for user_id in delete_users:
            delete_statement = "DELETE FROM users WHERE user_id = %s"
            values = (str(user_id),)
            cur.execute(delete_statement, values)
            conn.commit()

    @bot.event
    async def on_ready():
        print(f"{bot.user} is now running!")
        try:
            send_reminders.start()
            cs2_data.update_cs2_teams_dict.start()
        except Exception as e:
            print(e)


    ##########################   GENERAL COMMANDS   ###############################

    @bot.tree.command(name="remove_all_reminders", description="Removes all reminders for any or all of the leagues")
    @app_commands.describe(league="league to remove reminders from")
    @app_commands.choices(league = [
        discord.app_commands.Choice(name = "NBA", value = "NBA"),
        discord.app_commands.Choice(name = "NFL", value = "NFL"),
        discord.app_commands.Choice(name = "NHL", value = "NHL"),
        discord.app_commands.Choice(name = "CS2", value = "CS2"),
        discord.app_commands.Choice(name = "All Leagues", value = "ALL")
    ])
    async def remove_all_reminders(interaction: discord.Interaction, league: discord.app_commands.Choice[str]):
        response = remove_all_reminders_fn(str(interaction.user.id), str(league.value))
        await interaction.response.send_message(response)

    ##########################   GENERAL COMMANDS   ###############################

    ##########################   NBA RELATED COMMANDS   ###############################

    @bot.tree.command(name="nba_nextgame", description="Returns a graphic of selected NBA team upcoming game")
    @app_commands.describe(nba_team = "NBA Team")
    async def nba_nextgame(interaction: discord.Interaction, nba_team: str):
        if nba_team in nba_teams:
            team_name = nba_teams.get(nba_team)
            nba_games_list = get_team_NBA_matches(nba_team)
            bytes_io_obj = BytesIO()
            if len(nba_games_list) > 0:
                user_nextgame(nba_games_list, "NBA").save(bytes_io_obj, "PNG")
                bytes_io_obj.seek(0)
                await interaction.response.send_message(file = discord.File(fp=bytes_io_obj, filename="image.png"))
            else:
                await interaction.response.send_message("No Upcoming Games for the " + team_name)

    @bot.tree.command(name="nba_remindme", description="Set game time reminders for NBA teams")
    @app_commands.describe(nba_team = "NBA Team that user will get game time reminders for")
    @app_commands.describe(remind_time = "Time at which user will be reminded before selected NBA team game starts")
    async def nba_remindme(interaction: discord.Interaction, nba_team: str, remind_time: int):
        if nba_team in nba_teams:
            response = insert_or_update_user(str(interaction.user.id), nba_team, remind_time, "nba")
            await interaction.response.send_message(response)

    #Slash command for removing reminders for NBA teams
    @bot.tree.command(name="nba_remove_reminders", description="Remove game time reminders for NBA teams")
    @app_commands.describe(nba_team = "NBA Team that user will get game time reminders for")
    async def nba_remove_reminders(interaction: discord.Interaction, nba_team: str):
        if nba_team in nba_teams:
            response = remove_reminders(str(interaction.user.id), nba_team, "nba")
            await interaction.response.send_message(response)

    @nba_nextgame.autocomplete("nba_team")
    @nba_remindme.autocomplete("nba_team")
    @nba_remove_reminders.autocomplete("nba_team")
    # Only gets first 25 teams (LIMIT)
    async def nba_nextgame_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=nba_team, value=team_id)
            for team_id, nba_team in nba_teams.items() if current.lower() in nba_team.lower()
        ][:25]
    
    @nba_remindme.autocomplete("remind_time")
    # Only gets first 25 teams (LIMIT)
    async def nba_remind_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=remind_time, value=remind_time_in_mins)
            for remind_time_in_mins, remind_time in reminder_times.items() if current.lower() in remind_time.lower()
        ]

    ##########################   NBA RELATED COMMANDS   ###############################

    ##########################   NFL RELATED COMMANDS   ###############################

    @bot.tree.command(name="nfl_nextgame", description = "Returns a graphic of selected NFL team upcoming game")
    #@app_commands.describe(nba_team = "NBA Team")
    async def nfl_nextgame(interaction: discord.Interaction, nfl_team: str):
        if nfl_team in nfl_teams:
            team_name = nfl_teams.get(nfl_team)
            nfl_games_list = get_team_NFL_matches(nfl_team)
            bytes_io_obj = BytesIO()
            if len(nfl_games_list) > 0:
                user_nextgame(nfl_games_list, "NFL").save(bytes_io_obj, "PNG")
                bytes_io_obj.seek(0)
                await interaction.response.send_message(file = discord.File(fp=bytes_io_obj, filename="image.png"))
            else:
                await interaction.response.send_message(f"No Upcoming Games for the {team_name}")

    @bot.tree.command(name="nfl_remindme", description="Set game time reminders for NFL teams")
    @app_commands.describe(nfl_team = "NFL Team that user will get game time reminders for")
    @app_commands.describe(remind_time = "Time at which user will be reminded before selected NFL team game starts")
    async def nfl_remindme(interaction: discord.Interaction, nfl_team: str, remind_time: int):
        if nfl_team in nfl_teams:
            response = insert_or_update_user(str(interaction.user.id), nfl_team, remind_time, "nfl")
            await interaction.response.send_message(response)
            
    #Slash command for removing reminders for nfl teams
    @bot.tree.command(name="nfl_remove_reminders", description="Remove game time reminders for NFL teams")
    @app_commands.describe(nfl_team = "NFL team that user will get game time reminders for")
    async def nfl_remove_reminders(interaction: discord.Interaction, nfl_team: str):
        if nfl_team in nfl_teams:
            response = remove_reminders(str(interaction.user.id), nfl_team, "nfl")
            await interaction.response.send_message(response)

    @nfl_nextgame.autocomplete("nfl_team")
    @nfl_remindme.autocomplete("nfl_team")
    @nfl_remove_reminders.autocomplete('nfl_team')
    #Only gets first 25 teams (LIMIT)
    async def nfl_nextgame_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        return [
                   app_commands.Choice(name=nfl_team, value=team_id)
                   for team_id, nfl_team in nfl_teams.items() if current.lower() in nfl_team.lower()
               ][:25]

    @nfl_remindme.autocomplete("remind_time")
    # Only gets first 25 teams (LIMIT)
    async def nfl_remind_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=remind_time, value=remind_time_in_mins)
            for remind_time_in_mins, remind_time in reminder_times.items() if current.lower() in remind_time.lower()
        ]
    ##########################   NFL RELATED COMMANDS   ###############################

    ##########################   NHL RELATED COMMANDS   ###############################

    @bot.tree.command(name="nhl_nextgame", description = "Returns a graphic of selected NHL team upcoming game")
    async def nhl_nextgame(interaction: discord.Interaction, nhl_team: str):
        if nhl_team in nhl_teams:
            team_name = nhl_teams.get(nhl_team)
            nhl_games_list = get_team_NHL_matches(nhl_team)
            bytes_io_obj = BytesIO()

            if len(nhl_games_list) > 0:
                user_nextgame(nhl_games_list, "NHL").save(bytes_io_obj, "PNG")
                bytes_io_obj.seek(0)
                await interaction.response.send_message(file=discord.File(fp=bytes_io_obj, filename="image.png"))
            else:
                await interaction.response.send_message("No Upcoming Games for the {team_name}")

    @bot.tree.command(name="nhl_remindme", description="Set game time reminders for NHL teams")
    @app_commands.describe(nhl_team = "NHL Team that user will get game time reminders for")
    @app_commands.describe(remind_time = "Time at which user will be reminded before selected NHL team game starts")
    async def nhl_remindme(interaction: discord.Interaction, nhl_team: str, remind_time: int):
        if nhl_team in nhl_teams:
            response = insert_or_update_user(str(interaction.user.id), nhl_team, remind_time, "nhl")
            await interaction.response.send_message(response)
            
    #Slash command for removing reminders for nhl teams
    @bot.tree.command(name="nhl_remove_reminders", description="Remove game time reminders for NHL teams")
    @app_commands.describe(nhl_team = "NHL team that user will get game time reminders for")
    async def nhl_remove_reminders(interaction: discord.Interaction, nhl_team: str):
        if nhl_team in nhl_teams:
            response = remove_reminders(str(interaction.user.id), nhl_team, "nhl")
            await interaction.response.send_message(response)

    @nhl_nextgame.autocomplete("nhl_team")
    @nhl_remindme.autocomplete("nhl_team")
    @nhl_remove_reminders.autocomplete('nhl_team')
    # Only gets first 25 teams (LIMIT)
    async def nhl_nextgame_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        return [
                   app_commands.Choice(name=nhl_team, value=team_id)
                   for team_id, nhl_team in nhl_teams.items() if current.lower() in nhl_team.lower()
               ][:25]

    @nhl_remindme.autocomplete("remind_time")
    # Only gets first 25 teams (LIMIT)
    async def nhl_remind_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=remind_time, value=remind_time_in_mins)
            for remind_time_in_mins, remind_time in reminder_times.items() if current.lower() in remind_time.lower()
        ]
    ##########################   NHL RELATED COMMANDS   ###############################

    ##########################   CS2 RELATED COMMANDS START  ###############################

    @bot.tree.command(name="cs2_nextgame", description="Returns an embed of selected CS2 team upcoming game")
    @app_commands.describe(cs2_team="CS2 Team")
    async def cs2_nextgame(interaction: discord.Interaction, cs2_team: str):
        if cs2_team in cs2_data.teams:
            team_name = cs2_data.teams.get(cs2_team)
            cs2_next_game = get_team_CS2_matches(cs2_team)
            bytes_io_obj = BytesIO()
            if cs2_next_game is not None:
                fixed_date = convert_date(str(cs2_next_game[0]))
                cs2_next_game[0] = fixed_date
                create_cs2_game_graphic(cs2_next_game, "CS2").save(bytes_io_obj, "PNG")
                bytes_io_obj.seek(0)
                game_embed = discord.Embed(title=f"{cs2_data.teams[cs2_next_game[1]]} vs. {cs2_data.teams[cs2_next_game[2]]}", url = cs2_next_game[5])
                game_embed.set_image(url = "attachment://image.png")
                game_embed.add_field(name = "Series Type: ", value = cs2_next_game[3])
                game_embed.add_field(name = "Match Environment: ", value = cs2_next_game[4])

                await interaction.response.send_message(file = discord.File(fp=bytes_io_obj, filename="image.png"), embed = game_embed)
            else:
                await interaction.response.send_message(f"No Upcoming Games for {team_name}")

    @bot.tree.command(name="cs2_remindme", description="Set reminders for CS2 teams")
    @app_commands.describe(cs2_team="CS2 team that user will get game time reminders for")
    @app_commands.describe(remind_time="Time at which user will be reminded before selected CS2 team game starts")
    async def cs2_remindme(interaction: discord.Interaction, cs2_team: str, remind_time: int):
        if cs2_team in cs2_data.teams:
            response = insert_or_update_user(str(interaction.user.id), cs2_team, remind_time, "cs2")
            await interaction.response.send_message(response)

    # Slash command for removing reminders for CS2 teams
    @bot.tree.command(name="cs2_remove_reminders", description="Remove game time reminders for CS2 teams")
    @app_commands.describe(cs2_team="CS2 team that user will remove game time reminders for")
    async def cs2_remove_reminders(interaction: discord.Interaction, cs2_team: str):
        if cs2_team in cs2_data.teams:
            response = remove_reminders(str(interaction.user.id), cs2_team, "cs2")
            await interaction.response.send_message(response)

    @cs2_nextgame.autocomplete("cs2_team")
    @cs2_remindme.autocomplete("cs2_team")
    @cs2_remove_reminders.autocomplete("cs2_team")
    #Only gets first 25 teams (LIMIT)
    async def cs2_nextgame_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[
        app_commands.Choice[str]]:
        return [
                   app_commands.Choice(name=cs2_team, value=team_id)
                   for team_id, cs2_team in cs2_data.teams.items() if current.lower() in cs2_team.lower()
               ][:25]

    @cs2_remindme.autocomplete("remind_time")
    # Only gets first 25 teams (LIMIT)
    async def cs2_remind_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[
        app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=remind_time, value=remind_time_in_mins)
            for remind_time_in_mins, remind_time in reminder_times.items() if current.lower() in remind_time.lower()
        ]

    ###########################   CS2 RELATED COMMANDS END  ################################
    bot.run(TOKEN)
