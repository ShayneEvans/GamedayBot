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
import pytz
import os

est_time_zone = pytz.timezone('US/Eastern')

# Connecting to database
def conn_database():
    conn = psycopg2.connect(
        database= os.environ.get('GamedayBot_database'),
        user= os.environ.get('GamedayBot_user'),
        password= os.environ.get('GamedayBot_password'),
        host = os.environ.get('GamedayBot_host'),
        port = os.environ.get('GamedayBot_port'),
        keepalives=1,
        keepalives_idle=1
        )
    return conn

conn = conn_database()
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
    '1': 'New Jersey Devils',
    '2': 'New York Islanders',
    '3': 'New York Rangers',
    '4': 'Philadelphia Flyers',
    '5': 'Pittsburgh Penguins',
    '6': 'Boston Bruins',
    '7': 'Buffalo Sabres',
    '8': 'Montréal Canadiens',
    '9': 'Ottawa Senators',
    '10': 'Toronto Maple Leafs',
    '12': 'Carolina Hurricanes',
    '13': 'Florida Panthers',
    '14': 'Tampa Bay Lightning',
    '15': 'Washington Capitals',
    '16': 'Chicago Blackhawks',
    '17': 'Detroit Red Wings',
    '18': 'Nashville Predators',
    '19': 'St. Louis Blues',
    '20': 'Calgary Flames',
    '21': 'Colorado Avalanche',
    '22': 'Edmonton Oilers',
    '23': 'Vancouver Canucks',
    '24': 'Anaheim Ducks',
    '25': 'Dallas Stars',
    '26': 'Los Angeles Kings',
    '28': 'San Jose Sharks',
    '29': 'Columbus Blue Jackets',
    '30': 'Minnesota Wild',
    '52': 'Winnipeg Jets',
    '53': 'Arizona Coyotes',
    '54': 'Vegas Golden Knights',
    '55': 'Seattle Kraken'}

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

#Gets the reminder time in format suitable for database (string Y-m-d H:M:S)
def get_game_reminder_time(game_start_time, remind_time_in_mins):
    game_start_time_dt = game_start_time - timedelta(minutes = remind_time_in_mins)
    game_start_time_string = game_start_time_dt.strftime('%Y-%m-%d %H:%M:%S')
    return game_start_time_dt, game_start_time_string

#def daily_get_upcoming_reminder_times():


#Gets the upcoming games and sets reminders in next 24 hours for a user when they choose to start following a team. Also updates reminder times in same league if following multiple teams in league
def set_upcoming_game_reminder_times(league, teams_query_idx, remind_times_query_idx, user_id):
    #User specified, must be getting games for a new user or if they started following a new league
    id_query = "SELECT * FROM users WHERE user_id = %s"
    cur.execute(id_query, (user_id,))
    user = [cur.fetchone()]
    user_followed_teams_tuple = tuple(user[0][teams_query_idx].split(","))

    #Getting all upcoming games for each league
    league_games = league +'_games'
    upcoming_games = "SELECT * FROM " + league_games + " WHERE start_time <= NOW() + INTERVAL '2 DAY'::INTERVAL AND (visiting_team IN " + str(user_followed_teams_tuple) + " OR home_team IN " + str(user_followed_teams_tuple) + ")"
    cur.execute(upcoming_games)
    upcoming_games_query_result = cur.fetchall()

    #These will not be None if user follows any teams will be updated in code below
    followed_league_teams = None

    if user[0][teams_query_idx] is not None:
        followed_league_teams = list(user[0][teams_query_idx].split(','))
    
    current_date = datetime.strptime(datetime.now().strftime("%Y-%m-%dT%H:%M"), "%Y-%m-%dT%H:%M")

    #If user follows nba teams
    if followed_league_teams is not None:
        for game in upcoming_games_query_result:
            #If home team or visiting team in followed league teams insert a reminder for that game, duplicate games are avoided with a check for the count
            if game[1] in followed_league_teams or game[2] in followed_league_teams:
                game_remind_time_dt, game_remind_time_string = get_game_reminder_time(game[0], user[0][remind_times_query_idx])
                #If past the remind time, do not set it.
                if current_date < game_remind_time_dt:
                    insert_statement = "INSERT INTO reminders (user_id, remind_time, visiting_team, home_team, league, minutes_from_start_time) VALUES (%s, %s, %s, %s, %s, %s)"
                    values = (user[0][0], game_remind_time_string, game[1], game[2], league.upper(), user[0][remind_times_query_idx])
                    #Checks if a reminder has been set for this upcoming game, an insert will not take place if true
                    check_if_exists = "SELECT count(*) FROM reminders WHERE user_id = %s AND visiting_team = %s AND home_team = %s AND remind_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
                    check_if_exists_results = cur.execute(check_if_exists, (user[0][0], game[1], game[2],))
                    if cur.fetchone()[0] == 0:
                        check_if_exists_swapped = "SELECT count(*) FROM reminders WHERE user_id = %s AND visiting_team = %s AND home_team = %s AND remind_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
                        check_if_exists_swapped_results = cur.execute(check_if_exists_swapped, (user[0][0], game[2], game[1]))
                        if cur.fetchone()[0] == 0:
                            cur.execute(insert_statement, values)
                            conn.commit()
                            print(f'{league} Games added to reminders')
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
        game_start_time_query = "SELECT start_time FROM " + league.lower() + "_games WHERE visiting_team = %s AND home_team = %s AND start_time <= NOW() + INTERVAL '2 DAY'::INTERVAL"
        values = (reminder[2], reminder[3],)
        cur.execute(game_start_time_query, values)
        game_start_time = cur.fetchone()
        new_game_remind_time = game_start_time[0] - timedelta(minutes = new_time)
        #If setting reminder that would have already happened, delete record

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
        return f'All previous reminders were successfully updated!'
    elif update_success == 0 and update_error == 1:
        return f'No previously set reminders were updated, this is because the new reminder time has already passed. Old reminder time will be used for these games but games moving forward will use the new remind time.'
    else:
        return f'Some previously set reminders were unable to be updated because the new remind time has already passed. Old reminder time will be used for these games only.'

#Function used to insert a new user or update an existing one in the users table
def insert_or_update_user(user_id, team_id, remind_time, league):
    league_teams = league + "_teams"
    league_remind_time = league + "_remind_time"
    team_name = ""
    remind_string = ""
    teams_query_idx = 0
    remind_times_query_idx = 0
    update_reminder_times_msg = ""

    if league == 'nba':
        team_name = nba_teams[team_id]
        remind_string = reminder_times[remind_time]
        teams_query_idx = 1
        remind_times_query_idx = 2
    elif league == 'nfl':
        team_name = nfl_teams[team_id]
        remind_string = reminder_times[remind_time]
        teams_query_idx = 3
        remind_times_query_idx = 4
    elif league == 'nhl':
        team_name = nhl_teams[team_id]
        remind_string = reminder_times[remind_time]
        teams_query_idx = 5
        remind_times_query_idx = 6

    #Query to see if user already in database or not
    id_query = "SELECT * FROM users WHERE user_id = %s"
    try:
        cur.execute(id_query, (user_id,))
        #id_query_result = await db.execute(id_query, (user_id,))
        id_query_result = cur.fetchone()
    except Exception as e:
        print(e.message)
        conn = conn_database()
        cur = conn.cursor()
        cur.execute(id_query, (user_id,))
        id_query_result = cur.fetchone()
    #If not in database add user with entered team and remind time
    if id_query_result is None:
        insert_statement = "INSERT INTO users (user_id, " + league_teams + ", " + league_remind_time + ") VALUES (%s, %s, %s)"
        values = (user_id, team_id + ',', remind_time)
        cur.execute(insert_statement, values)
        conn.commit()
        set_upcoming_game_reminder_times(league, teams_query_idx, remind_times_query_idx, user_id)
        return f"Now receiving reminders for the {team_name} {remind_string[10:]}."
    #User already in database but adding reminders for different leagues
    elif id_query_result[teams_query_idx] is None:
        update_statement = "UPDATE users SET " + league_teams + " = %s, " + league_remind_time + " = %s WHERE user_id = %s"
        values = (team_id + ',', remind_time, user_id)
        cur.execute(update_statement, values)
        conn.commit()
        #Will add reminders for the upcoming games of all teams that the user follows including the just newly added team
        set_upcoming_game_reminder_times(league, teams_query_idx, remind_times_query_idx, user_id)
        return f"Now receiving reminders for the {team_name} {remind_string[10:]}. {update_reminder_times_msg}"
    #User already follows teams and has reminders set,they want to follow another team and possibly want different reminder time
    else:
        #Getting the VARCHAR of teams that the user follows, has this format string: TEAM1,TEAM2,TEAM3,....
        updated_reminder_teams_string = id_query_result[teams_query_idx]
        #If team user wants to follow is not in the string then add it
        if team_id not in updated_reminder_teams_string:
            updated_reminder_teams_string = f'{updated_reminder_teams_string}{team_id},'

        #If both entered team and remind time are different from ones on database update them
        if updated_reminder_teams_string != id_query_result[teams_query_idx] and remind_time != id_query_result[remind_times_query_idx]:
            update_statement = "UPDATE users SET " + league_teams + " = %s, " + league_remind_time + " = %s WHERE user_id = %s"
            values = (updated_reminder_teams_string, remind_time, user_id)
            cur.execute(update_statement, values)
            conn.commit()
            set_upcoming_game_reminder_times(league, teams_query_idx, remind_times_query_idx, user_id)
            update_reminder_times_msg = update_reminder_time_on_reminders_table(user_id, remind_time, league.upper())
            return f"Now receiving reminders for the {team_name} {remind_string[10:]}. {update_reminder_times_msg}"

        #If only remind time is different change it also is updated in the reminders table
        elif updated_reminder_teams_string == id_query_result[teams_query_idx] and remind_time != id_query_result[remind_times_query_idx]:

            update_statement = "UPDATE users SET " + league_remind_time + " = %s WHERE user_id = %s"
            values = (remind_time, user_id)
            cur.execute(update_statement, values)
            conn.commit()
            set_upcoming_game_reminder_times(league, teams_query_idx, remind_times_query_idx, user_id)
            update_reminder_times_msg = update_reminder_time_on_reminders_table(user_id, remind_time, league.upper()) #######################################################
            return f"Remind time successfully changed to {remind_string[10:]} for the {team_name}. {update_reminder_times_msg}"

        #User wants to get reminders for a new team
        elif updated_reminder_teams_string != id_query_result[teams_query_idx] and remind_time == id_query_result[remind_times_query_idx]:
            update_statement = "UPDATE users SET " + league_teams + " = %s WHERE user_id = %s"
            values = (updated_reminder_teams_string, user_id)
            cur.execute(update_statement, values)
            conn.commit()
            #Will add reminders for the upcoming games of all teams that the user follows including the just newly added team
            set_upcoming_game_reminder_times(league, teams_query_idx, remind_times_query_idx, user_id)
            return f"Now receiving reminders for the {team_name} {remind_string[10:]}."

        else:
            set_upcoming_game_reminder_times(league, teams_query_idx, remind_times_query_idx, user_id)
            return f"UPDATE not made, you already receive game reminders for the {team_name} {remind_string[10:]}."

#Function used to remove reminders for a user
def remove_reminders(user_id, team_id, league):
    league_teams = league + "_teams"
    team_name = ""
    teams_query_idx = 0

    if league == 'nba':
        team_name = nba_teams[team_id]
        teams_query_idx = 1
    elif league == 'nfl':
        team_name = nfl_teams[team_id]
        teams_query_idx = 3
    elif league == 'nhl':
        team_name = nhl_teams[team_id]
        teams_query_idx = 5

    #Query to see if user already in database or not
    id_query = "SELECT * FROM users WHERE user_id = %s"
    cur.execute(id_query, (user_id,))
    id_query_result = cur.fetchone()

    #If reminders have been set for this team
    if team_id in id_query_result[teams_query_idx]:
        updated_reminder_teams_bit_string = id_query_result[teams_query_idx]
        updated_reminder_teams_bit_string = updated_reminder_teams_bit_string.replace(team_id + ',', '')
        update_statement = "UPDATE users SET " + league_teams + " = %s WHERE user_id = %s"
        values = (updated_reminder_teams_bit_string, user_id)
        cur.execute(update_statement, values)
        conn.commit()
        delete_statement = "DELETE FROM reminders WHERE user_id = %s AND home_team = %s OR visiting_team = %s"
        values = (user_id, team_id, team_id,)
        cur.execute(delete_statement, values)
        conn.commit()
        return f"Reminders removed for the {team_name}"
    #User has no reminders for the selected team
    elif team_id not in id_query_result[teams_query_idx]:
        return f"You do not have any reminders set for the {team_name}"
    #User has no reminders for the specified league.
    elif id_query_result[teams_query_idx] is None:
        return f"You do not have any reminders set for the {league.upper()}"
    # User does not exist in database
    elif id_query_result is None:
        return f"You do not have any reminders set for any leagues."

def remove_all_reminders_fn(user_id, league):

    # Query to see if user already in database or not
    id_query = "SELECT * FROM users WHERE user_id = %s"
    cur.execute(id_query, (user_id,))
    id_query_result = cur.fetchone()
    # Valid reminders have been set for this league and should be removed
    if league == 'NBA' and id_query_result[1] is not None:
        update_statement = "UPDATE users SET nba_teams = %s, nba_remind_time = %s WHERE user_id = %s"
        values = (None, None, user_id)
        cur.execute(update_statement, values)
        conn.commit()
        delete_statement = "DELETE FROM reminders WHERE user_id = %s and league = %s"
        values = (user_id, league,)
        cur.execute(delete_statement, values)
        conn.commit()
        return f"All NBA reminders have been successfully removed"
    # No reminders have been set for this league, return error message
    elif league == 'NBA' and id_query_result[1] is None:
        return "You have no reminders set for any NBA teams."
    # Valid reminders have been set for this league and should be removed
    elif league == 'NFL' and id_query_result[3] is not None:
        update_statement = "UPDATE users SET nfl_teams = %s, nfl_remind_time = %s WHERE user_id = %s"
        values = (None, None, user_id)
        cur.execute(update_statement, values)
        conn.commit()
        delete_statement = "DELETE FROM reminders WHERE user_id = %s and league = %s"
        values = (user_id, league,)
        cur.execute(delete_statement, values)
        conn.commit()
        return f"All NFL reminders have been successfully removed"
    # No reminders have been set for this league, return error message
    elif league == 'NFL' and id_query_result[3] is None:
        return "You have no reminders set for any NFL teams."
    # Valid reminders have been set for this league and should be removed
    elif league == 'nhl' and id_query_result[5] is not None:
        update_statement = "UPDATE users SET nhl_teams = %s, nhl_remind_time = %s WHERE user_id = %s"
        values = (None, None, user_id)
        cur.execute(update_statement, values)
        conn.commit()
        delete_statement = "DELETE FROM reminders WHERE user_id = %s and league = %s"
        values = (user_id, league,)
        cur.execute(delete_statement, values)
        conn.commit()
        return f"All NHL reminders have been successfully removed"
    # No reminders have been set for this league, return error message
    elif league == 'NHL' and id_query_result[5] is None:
        return "You have no reminders set for any NHL teams."
    elif league == 'ALL' and not all(followed_teams_list is None for followed_teams_list in (id_query_result[1], id_query_result[3], id_query_result[5])):
        update_statement = "UPDATE users SET nba_teams = %s, nba_remind_time = %s, nfl_teams = %s, nfl_remind_time = %s, nhl_teams = %s, nhl_remind_time = %s WHERE user_id = %s"
        values = (None, None, None, None, None, None, user_id)
        cur.execute(update_statement, values)
        conn.commit()
        delete_statement = "DELETE FROM reminders WHERE user_id = %s"
        values = (user_id,)
        cur.execute(delete_statement, values)
        conn.commit()
        return f"All reminders have been successfully removed"
    else:
        return "You have no reminders for any leagues."

def get_team_NBA_matches(team_id):
    currentNBAYear = date.today().year - 1
    #Endpoint obtained from https://github.com/rlabausa/nba-schedule-data
    NBA_json_data = requests.get("https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/" + str(currentNBAYear) + "/league/00_full_schedule.json")
    NBA_json = json.loads(NBA_json_data.text)
    nba_games_list = []

       # Getting all team games that have yet to be played with date
    for i in range(len(NBA_json['lscd'])):
        for j in range(len(NBA_json['lscd'][i]['mscd']['g'])):
            # Date when the game takes place
            game_date = NBA_json['lscd'][i]['mscd']['g'][j]['gdte']
            # Start time for the game if it has not occurred, Final otherwise, default EST
            game_status = NBA_json['lscd'][i]['mscd']['g'][j]['stt']
            # Visting team 3 letter abbreviation
            visiting_team = NBA_json['lscd'][i]['mscd']['g'][j]['v']['ta']
            # Home team 3 letter abbreviation
            home_team = NBA_json['lscd'][i]['mscd']['g'][j]['h']['ta']

            # If game hasn't been played, append it to list
            if game_status[-2:] == 'ET' or game_status == "TBD":
                if home_team == team_id or visiting_team == team_id:
                    game_start_time = game_date + " " + game_status
                    if game_status != "TBD":
                        game_start_time = convert_date(game_start_time)
                    nba_games_list.append((game_start_time, visiting_team, home_team))

    return nba_games_list

def user_upcoming_game(away_team_id, home_team_id, league, reminder_message):
    reminder_message_split_up = reminder_message.split("starts")
    reminder_message_split_up[1] = "".join("starts" + reminder_message_split_up[1])
    away = Image.open(league +"/" + away_team_id + '.png')
    away = away.convert("RGBA")
    home = Image.open(league +"/" + home_team_id + '.png')
    home = home.convert("RGBA")
    game_graphic = Image.open(league +"/GameTemplate.png")
    game_graphic = game_graphic.convert("RGBA")
    game_graphic.paste(away, (0, 0), away)
    game_graphic.paste(home, (400, 0), home)
    game_image = ImageDraw.Draw(game_graphic)
    font = ImageFont.truetype("arial.ttf", 25)
    _, _, w, h = game_image.textbbox((0, -270), reminder_message_split_up[0], font=font)
    game_image.text(((700-w)/2, (350-h)/2), reminder_message_split_up[0], font=font)
    _, _, w, h = game_image.textbbox((0, -315), reminder_message_split_up[1], font=font)
    game_image.text(((700-w)/2, (350-h)/2), reminder_message_split_up[1], font=font)
    return game_graphic

def nba_upcoming_game(nba_games_list):
    upcoming_game_idx = 0
    for i in range(0, len(nba_games_list)):
        if nba_games_list[i][0][-3:] == "TBD":
            break
        start_time = datetime.strptime(nba_games_list[i][0][:-4], "%m-%d-%Y %I:%M %p")

        if(datetime.now() >= start_time):
            if(upcoming_game_idx + 1 != len(nba_games_list)):
                upcoming_game_idx += 1
            break

    away = Image.open("NBA/" + nba_games_list[upcoming_game_idx][1] + '.png')
    away = away.convert("RGBA")
    home = Image.open("NBA/" + nba_games_list[upcoming_game_idx][2] + '.png')
    home = home.convert("RGBA")
    game_graphic = Image.open("NBA/GameTemplate.png")
    game_graphic = game_graphic.convert("RGBA")
    game_graphic.paste(away, (0, 0), away)
    game_graphic.paste(home, (400, 0), home)
    game_image = ImageDraw.Draw(game_graphic)
    #font = ImageFont.truetype("arial.ttf", 50)
    #game_image.text((100, 290), nba_games_list[0][0], font=font)
    font = ImageFont.truetype("arial.ttf", 50)
    _, _, w, h = game_image.textbbox((0, -290), nba_games_list[upcoming_game_idx][0], font=font)
    game_image.text(((700-w)/2, (350-h)/2), nba_games_list[upcoming_game_idx][0], font=font)

    return game_graphic

#https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c#apissitev2sportsfootballnflteamsteam_id
def get_team_NFL_matches(team_id):
    nfl_games_list = []
    current_date = datetime.strptime(datetime.now().strftime("%Y-%m-%dT%H:%M"), "%Y-%m-%dT%H:%M")

    NFL_json_data = requests.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/" + str(team_id) + "/schedule")
    NFL_json = json.loads(NFL_json_data.text)

    #Going over each game
    for i in range(0, len(NFL_json['events'])):
        game_start_time = NFL_json['events'][i]['date']

        #Converting game start time to datetime to be compared with the current datetime, first must convert string to datetime then back to string then datetime again to get
        #correct format (ANNOYING).
        game_start_time_dt = datetime.strptime(game_start_time, "%Y-%m-%dT%H:%M%f%z")
        game_start_time_dt = datetime.strptime(game_start_time_dt.strftime("%Y-%m-%dT%H:%M"), "%Y-%m-%dT%H:%M")

        if game_start_time_dt >= current_date:
            game_start_time = convert_date(NFL_json['events'][i]['date'])
            game = NFL_json['events'][i]['name']
            game = game.split(' at ')
            #Visting team ID obtained by using the team name
            visiting_team = list(nfl_teams.keys())[list(nfl_teams.values()).index(game[0])]
            #Home team ID obtained by using the team name
            home_team = list(nfl_teams.keys())[list(nfl_teams.values()).index(game[1])]
            nfl_games_list.append((game_start_time, visiting_team, home_team))

    return nfl_games_list

def nfl_upcoming_game(nfl_games_list):
    #Finding the upcoming game then breaking from loop and creating graphic of it
    upcoming_game_idx = 0
    for i in range(0, len(nfl_games_list)):
        start_time = datetime.strptime(nfl_games_list[i][0][:-4], "%m-%d-%Y %I:%M %p")

        if(datetime.now() >= start_time):
            if(upcoming_game_idx + 1 != len(nfl_games_list)):
                upcoming_game_idx = i
            break

    away = Image.open("NFL/" + nfl_games_list[upcoming_game_idx][1] + '.png')
    away = away.convert("RGBA")
    home = Image.open("NFL/" + nfl_games_list[upcoming_game_idx][2] + '.png')
    home = home.convert("RGBA")
    game_graphic = Image.open("NFL/GameTemplate.png")
    game_graphic = game_graphic.convert("RGBA")
    game_graphic.paste(away, (0, 0), away)
    game_graphic.paste(home, (400, 0), home)
    game_image = ImageDraw.Draw(game_graphic)
    font = ImageFont.truetype("arial.ttf", 50)
    _, _, w, h = game_image.textbbox((0, -290), nfl_games_list[upcoming_game_idx][0], font=font)
    game_image.text(((700-w)/2, (350-h)/2), nfl_games_list[upcoming_game_idx][0], font=font)

    return game_graphic

def get_team_NHL_matches(team_id , startDate, endDate):
    #Variable for upcoming NHL matches
    upcoming_match_list = []

    #Requesting schedule of team and converting request object to json text
    NHL_json_data = requests.get("https://statsapi.web.nhl.com/api/v1/schedule?teamId=" + str(team_id) +
                                 "&startDate=" + str(startDate) +
                                 "&endDate=" + str(endDate))
    NHL_json = json.loads(NHL_json_data.text)

    number_of_games = len(NHL_json['dates'])
    for i in range(0, number_of_games):
        if NHL_json['dates'][i]['games'][0]['status']['abstractGameState'] == "Preview":
            game_date = NHL_json['dates'][i]['games'][0]['gameDate']
            visiting_team = NHL_json['dates'][i]['games'][0]['teams']['away']['team']['id']
            home_team = NHL_json['dates'][i]['games'][0]['teams']['home']['team']['id']
            upcoming_match_list.append((convert_date(game_date), visiting_team, home_team))

    return upcoming_match_list

def nhl_upcoming_game(nhl_games_list):
    upcoming_game_idx = 0
    for i in range(0, len(nhl_games_list)):
        start_time = datetime.strptime(nhl_games_list[i][0][:-4], "%m-%d-%Y %I:%M %p")

        if(datetime.now() >= start_time):
            if(upcoming_game_idx + 1 != len(nhl_games_list)):
                upcoming_game_idx = i
            break

    away = Image.open("NHL/" + str(nhl_games_list[upcoming_game_idx][1]) + '.png')
    away = away.convert("RGBA")
    home = Image.open("NHL/" + str(nhl_games_list[upcoming_game_idx][2]) + '.png')
    home = home.convert("RGBA")
    game_graphic = Image.open("NHL/GameTemplate.png")
    game_graphic = game_graphic.convert("RGBA")
    game_graphic.paste(away, (0, 0), away)
    game_graphic.paste(home, (400, 0), home)
    game_image = ImageDraw.Draw(game_graphic)
    font = ImageFont.truetype("arial.ttf", 50)
    _, _, w, h = game_image.textbbox((0, -290), nhl_games_list[upcoming_game_idx][0], font=font)
    game_image.text(((700-w)/2, (350-h)/2), nhl_games_list[upcoming_game_idx][0], font=font)

    return game_graphic

def get_reminders():
    cur.execute("SELECT * FROM reminders")
    reminders = cur.fetchall()
    reminders_with_messages = []

    for reminder in reminders:
        if reminder[4] == 'NBA':
            away_team = nba_teams[reminder[2]]
            home_team = nba_teams[reminder[3]]
        elif reminder[4] == 'NFL':
            away_team = nfl_teams[reminder[2]]
            home_team = nfl_teams[reminder[3]]
        else:
            away_team = nhl_teams[reminder[2]]
            home_team = nhl_teams[reminder[3]]

        time_before_game = reminder_times[reminder[5]]
        time_before_game = " ".join(time_before_game.split()[2:4])
        reminder_message = f'{away_team} vs. {home_team} starts in {time_before_game}!'
        reminders_with_messages.append((reminder[0], reminder[1], reminder[2], reminder[3], reminder[4], reminder_message))

    return reminders_with_messages

def run_discord_bot():
    TOKEN = os.environ.get('GamedayBot_TOKEN')
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix = '/', intents=intents)

    @tasks.loop(seconds=15)
    async def send_reminders():
        reminders_to_send = get_reminders()
        delete_reminders = []

        for reminder in reminders_to_send:
            #If current time is past the reminder time or equal to it then send message to user!
            if datetime.now() >= reminder[1]:
                user = await bot.fetch_user(reminder[0])
                bytes_io_obj = BytesIO()
                user_upcoming_game(reminder[2], reminder[3], reminder[4], reminder[5]).save(bytes_io_obj, 'PNG')
                bytes_io_obj.seek(0)
                await user.send(file=discord.File(fp=bytes_io_obj, filename='image.png'))
                delete_reminders.append((reminder[0], reminder[1], reminder[2], reminder[3]))

        #Deletes reminders that were successfully sent to users
        for reminder in delete_reminders:
            delete_statement = "DELETE FROM reminders WHERE user_id = %s AND remind_time = %s AND visiting_team = %s AND home_team = %s"
            values = (reminder[0], reminder[1], reminder[2], reminder[3],)
            cur.execute(delete_statement, values)
            conn.commit()

    @bot.event
    async def on_ready():
        print(f'{bot.user} is now running!')
        try:
            synced = await bot.tree.sync()#guild = discord.Object(id = 518631948197822465))
            print(f"Synced {len(synced)} command(s)")
            send_reminders.start()
        except Exception as e:
            print(e)


    ##########################   GENERAL COMMANDS   ###############################

    @bot.tree.command(name="remove_all_reminders", description="Removes all reminders for any or all of the leagues")
    @app_commands.describe(league="league to remove reminders from")
    @app_commands.choices(league = [
        discord.app_commands.Choice(name = 'NBA', value = 'NBA'),
        discord.app_commands.Choice(name = 'NFL', value = 'NFL'),
        discord.app_commands.Choice(name = 'NHL', value = 'NHL'),
        discord.app_commands.Choice(name = 'All Leagues', value = 'ALL')
    ])
    async def remove_all_reminders(interaction: discord.Interaction, league: discord.app_commands.Choice[str]):
        response = remove_all_reminders_fn(str(interaction.user.id), str(league.value))
        await interaction.response.send_message(response)

    ##########################   GENERAL COMMANDS   ###############################

    ##########################   NBA RELATED COMMANDS   ###############################

    @bot.tree.command(name="nba_nextgame", description="Returns a graphic of selected NBA team upcoming game.")
    @app_commands.describe(nba_team = "NBA Team")
    async def nba_nextgame(interaction: discord.Interaction, nba_team: str):
        if nba_team in nba_teams:
            team_name = nba_teams.get(nba_team)
            nba_games_list = get_team_NBA_matches(nba_team)
            bytes_io_obj = BytesIO()
            if len(nba_games_list) > 0:
                nba_upcoming_game(nba_games_list).save(bytes_io_obj, 'PNG')
                bytes_io_obj.seek(0)
                await interaction.response.send_message(file = discord.File(fp=bytes_io_obj, filename='image.png'))
            else:
                await interaction.response.send_message("No Upcoming Games for the " + team_name)

    @bot.tree.command(name="nba_remindme", description="User can set reminders for multiple teams")
    @app_commands.describe(nba_team = "NBA Team that user will get game time reminders for")
    @app_commands.describe(remind_time = "Time at which user will be reminded before selected NBA team game starts.")
    async def nba_remindme(interaction: discord.Interaction, nba_team: str, remind_time: int):
        if nba_team in nba_teams:
            response = insert_or_update_user(str(interaction.user.id), nba_team, remind_time, 'nba')
            await interaction.response.send_message(response)

    #Slash command for removing reminders for NBA teams
    @bot.tree.command(name="nba_remove_reminders", description="User can set reminders for multiple teams")
    @app_commands.describe(nba_team = "NBA Team that user will get game time reminders for")
    async def nba_remove_reminders(interaction: discord.Interaction, nba_team: str):
        if nba_team in nba_teams:
            response = remove_reminders(str(interaction.user.id), nba_team, 'nba')
            await interaction.response.send_message(response)

    @nba_nextgame.autocomplete('nba_team')
    @nba_remindme.autocomplete('nba_team')
    @nba_remove_reminders.autocomplete('nba_team')
    # Only gets first 25 teams (LIMIT)
    async def nba_nextgame_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=nba_team, value=team_id)
            for team_id, nba_team in nba_teams.items() if current.lower() in nba_team.lower()
        ][:25]
    
    @nba_remindme.autocomplete('remind_time')
    # Only gets first 25 teams (LIMIT)
    async def nba_remind_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=remind_time, value=remind_time_in_mins)
            for remind_time_in_mins, remind_time in reminder_times.items() if current.lower() in remind_time.lower()
        ]

    ##########################   NBA RELATED COMMANDS   ###############################

    ##########################   NFL RELATED COMMANDS   ###############################

    @bot.tree.command(name="nfl_nextgame", description = "Returns a graphic of selected NFL team upcoming game.")
    #@app_commands.describe(nba_team = "NBA Team")
    async def nfl_nextgame(interaction: discord.Interaction, nfl_team: str):
        if nfl_team in nfl_teams:
            team_name = nfl_teams.get(nfl_team)
            nfl_games_list = get_team_NFL_matches(nfl_team)
            bytes_io_obj = BytesIO()
            if len(nfl_games_list) > 0:
                nfl_upcoming_game(nfl_games_list).save(bytes_io_obj, 'PNG')
                bytes_io_obj.seek(0)
                await interaction.response.send_message(file = discord.File(fp=bytes_io_obj, filename='image.png'))
            else:
                await interaction.response.send_message("No Upcoming Games for the " + team_name)

    @bot.tree.command(name="nfl_remindme", description="User can set reminders for multiple teams")
    @app_commands.describe(nfl_team = "NFL Team that user will get game time reminders for")
    @app_commands.describe(remind_time = "Time at which user will be reminded before selected NFL team game starts.")
    async def nfl_remindme(interaction: discord.Interaction, nfl_team: str, remind_time: int):
        if nfl_team in nfl_teams:
            response = insert_or_update_user(str(interaction.user.id), nfl_team, remind_time, 'nfl')
            await interaction.response.send_message(response)
            
    #Slash command for removing reminders for nfl teams
    @bot.tree.command(name="nfl_remove_reminders", description="User can set reminders for multiple teams")
    @app_commands.describe(nfl_team = "nfl Team that user will get game time reminders for")
    async def nfl_remove_reminders(interaction: discord.Interaction, nfl_team: str):
        if nfl_team in nfl_teams:
            response = remove_reminders(str(interaction.user.id), nfl_team, 'nfl')
            await interaction.response.send_message(response)

    @nfl_nextgame.autocomplete('nfl_team')
    @nfl_remindme.autocomplete('nfl_team')
    @nfl_remove_reminders.autocomplete('nfl_team')
    #Only gets first 25 teams (LIMIT)
    async def nfl_nextgame_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        return [
                   app_commands.Choice(name=nfl_team, value=team_id)
                   for team_id, nfl_team in nfl_teams.items() if current.lower() in nfl_team.lower()
               ][:25]

    @nfl_remindme.autocomplete('remind_time')
    # Only gets first 25 teams (LIMIT)
    async def nfl_remind_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=remind_time, value=remind_time_in_mins)
            for remind_time_in_mins, remind_time in reminder_times.items() if current.lower() in remind_time.lower()
        ]
    ##########################   NFL RELATED COMMANDS   ###############################

    ##########################   NHL RELATED COMMANDS   ###############################

    @bot.tree.command(name="nhl_nextgame", description = "Returns a graphic of selected NHL team upcoming game.")
    async def nhl_nextgame(interaction: discord.Interaction, nhl_team: str):
        if nhl_team in nhl_teams:
            team_name = nhl_teams.get(nhl_team)
            NHL_schedule_startDate = date.today()
            NHL_schedule_endDate = date(date.today().year + 1, 12, 31)
            nhl_games_list = get_team_NHL_matches(nhl_team, NHL_schedule_startDate, NHL_schedule_endDate)
            bytes_io_obj = BytesIO()

            if len(nhl_games_list) > 0:
                nhl_upcoming_game(nhl_games_list).save(bytes_io_obj, 'PNG')
                bytes_io_obj.seek(0)
                await interaction.response.send_message(file=discord.File(fp=bytes_io_obj, filename='image.png'))
            else:
                await interaction.response.send_message("No Upcoming Games for the " + team_name)

    @bot.tree.command(name="nhl_remindme", description="User can set reminders for multiple teams")
    @app_commands.describe(nhl_team = "NHL Team that user will get game time reminders for")
    @app_commands.describe(remind_time = "Time at which user will be reminded before selected NHL team game starts.")
    async def nhl_remindme(interaction: discord.Interaction, nhl_team: str, remind_time: int):
        if nhl_team in nhl_teams:
            response = insert_or_update_user(str(interaction.user.id), nhl_team, remind_time, 'nhl')
            await interaction.response.send_message(response)
            
    #Slash command for removing reminders for nhl teams
    @bot.tree.command(name="nhl_remove_reminders", description="User can set reminders for multiple teams")
    @app_commands.describe(nhl_team = "nhl Team that user will get game time reminders for")
    async def nhl_remove_reminders(interaction: discord.Interaction, nhl_team: str):
        if nhl_team in nhl_teams:
            response = remove_reminders(str(interaction.user.id), nhl_team, 'nhl')
            await interaction.response.send_message(response)

    @nhl_nextgame.autocomplete('nhl_team')
    @nhl_remindme.autocomplete('nhl_team')
    @nhl_remove_reminders.autocomplete('nhl_team')
    # Only gets first 25 teams (LIMIT)
    async def nhl_nextgame_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        return [
                   app_commands.Choice(name=nhl_team, value=team_id)
                   for team_id, nhl_team in nhl_teams.items() if current.lower() in nhl_team.lower()
               ][:25]

    @nhl_remindme.autocomplete('remind_time')
    # Only gets first 25 teams (LIMIT)
    async def nhl_remind_autocomplete(interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=remind_time, value=remind_time_in_mins)
            for remind_time_in_mins, remind_time in reminder_times.items() if current.lower() in remind_time.lower()
        ]
    ##########################   NHL RELATED COMMANDS   ###############################
    #loop = asyncio.get_event_loop()
    #my_task = loop.create_task(send_reminders())
    bot.run(TOKEN)
