#This script is used to obtain new games from https://www.hltv.org/matches
#and import them into the database to quickly retrieve match info with nextgame commands.

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
op = webdriver.ChromeOptions()
op.add_argument("--headless=new")
op.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
op.add_argument("--no-sandbox")
from dateutil import parser
import pytz
est_time_zone = pytz.timezone('US/Eastern')
from datetime import datetime, timedelta
import psycopg2
import os
import sys
import time
from datetime import datetime

#Used for date conversion to readable string in EST.
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

#Calculate the time until the match starts
def get_time_until_match(game_start_time):
    current_time = datetime.now().replace(microsecond=0)
    #Difference between current time and the time the game starts
    delta = game_start_time - current_time

    days = delta.days
    seconds = delta.seconds
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    #Exclude days if the game is happening today
    if days > 0:
        time_until_match_starts_msg = f'{days}d {hours}h {minutes}m {seconds}s'
    else:
        time_until_match_starts_msg = f'{hours}h {minutes}m {seconds}s'

    return time_until_match_starts_msg

#Used to scrape new matches
def get_upcoming_matches():
    upcoming_games = []
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=op)
    url = 'https://www.hltv.org/matches'
    try:
        driver.get(url)
        match_list = driver.find_element(By.CLASS_NAME, "matches-list-wrapper")
        match_wrappers = match_list.find_elements(By.CLASS_NAME, "match-wrapper")
        for match in match_wrappers:
            match_url = match.find_element(By.CSS_SELECTOR, ".match-info.a-reset").get_attribute("href")

            no_game = False
            #See if match exists yet, for example could be placeholder for a future match such as Final or semi-final
            #If no exceptions both team names will be obtained.
            try:
                #Check to see if team is decided yet (doesn't depend on another match result)
                try:
                    team1_name = match.find_element(By.CSS_SELECTOR, ".match-team1 .match-teamname").text.strip()
                except NoSuchElementException:
                    pass
                    #team1_name = match.find_element(By.CSS_SELECTOR, ".match-team team2 .match-teamname text-ellipsis").text

                #Check to see if team is decided yet (doesn't depend on another match result)
                try:
                    team2 = match.find_element(By.CSS_SELECTOR, ".match-team2 .match-teamname").text.strip()
                except NoSuchElementException:
                    pass
                    #team2_name = match.find_element(By.CSS_SELECTOR, ".matchTeam.team2 .team").text

            except NoSuchElementException:
                no_game = True

            #Scraping match information for each match
            if no_game == False:
                #Getting Team IDs
                team1_id = match.get_attribute("team1")
                team2_id = match.get_attribute("team2")

                #Match type: BO1/BO3/BO5 (sometimes 3 map letter abbreviation if BO1 determined map idk)
                match_length = match.find_element(By.CLASS_NAME,"match-meta").get_attribute("textContent")

                #Getting the starting date and time until the game
                unix_timestamp_start_date = match.find_element(By.CSS_SELECTOR, ".match-time").get_attribute("data-unix")
                start_time_dt = datetime.fromtimestamp(int(unix_timestamp_start_date)/1000)
                start_time_str = start_time_dt.strftime("%m-%d-%Y %H:%M")
                start_time_converted = convert_date(start_time_str)

                #Checkin if LAN or ONLINE game
                match_env = match.get_attribute("lan")
                if match_env == "true":
                    match_env = "LAN"
                else:
                    match_env = "ONLINE"

                #Making sure that both teams are truthy values (Not None or empty)
                if team1_id and team2_id:
                    upcoming_games.append((start_time_converted, team1_id, team2_id, match_length.upper(), match_env, match_url))
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    finally:
        if driver is not None:
            driver.quit()

    return upcoming_games

#Inserts all new games into database
def insert_upcoming_matches_to_db(cs2_upcoming_matches):
    conn_get_games = psycopg2.connect(
        database= os.environ.get('GamedayBot_database'),
        user= os.environ.get('GamedayBot_user'),
        password= os.environ.get('GamedayBot_password'),
        host= os.environ.get('GamedayBot_host'),
        port= os.environ.get('GamedayBot_port')
    )

    cur_get_games = conn_get_games.cursor()

    #If there are upcoming games
    if len(cs2_upcoming_matches) != 0:
        result_message = f'{len(cs2_upcoming_matches)} Games Insertion Attempted'
        cs2_args_str = ','.join(cur_get_games.mogrify("(%s,%s,%s,%s,%s,%s)", i).decode('utf-8')
                                for i in cs2_upcoming_matches)
        cur_get_games.execute("INSERT INTO cs2_games VALUES " + (
            cs2_args_str) + " ON CONFLICT(match_url) DO UPDATE SET start_time = EXCLUDED.start_time")
        conn_get_games.commit() 
    else:
        result_message = "No New Games to Insert"
    
    cur_get_games.close()
    conn_get_games.close()
    return result_message

#Getting upcoming matches from https://www.hltv.org/matches and putting new games into database
start_time = time.time()
cs2_upcoming_matches = get_upcoming_matches()
insert_result = insert_upcoming_matches_to_db(cs2_upcoming_matches)
end_time = time.time()
execution_time = end_time - start_time
current_time = datetime.now()
print(f"[{current_time}]: Executed get_cs2_games in {execution_time} seconds, RESULT: {insert_result}")