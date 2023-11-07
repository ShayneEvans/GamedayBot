#The purpose of this script is to find new teams from the upcoming matches. Since HLTV has no way to see all ranked teams
#this will have to do for collecting the names, ids, and profile links of those teams.
#Each new team that is found is compared to the list from the database and added if new

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import psycopg2
import os
from datetime import datetime
import time
op = webdriver.ChromeOptions()
op.add_argument("--headless=new")
op.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

#Gets list of cs2 teams from csv
def get_cs2_teams_list():
	#Connecting to database
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

    select_statement = "SELECT team_id, team_name FROM cs2_teams"
    cur.execute(select_statement)
    cs2_teams_list = cur.fetchall()

    cur.close()
    conn.close()

    return cs2_teams_list

#Inserts newly found teams into database
def insert_new_teams_to_database(new_cs2_teams_list):
    pycopg2.connect(
  		database= os.environ.get('GamedayBot_database'),
        user= os.environ.get('GamedayBot_user'),
        password= os.environ.get('GamedayBot_password'),
        host = os.environ.get('GamedayBot_host'),
        port = os.environ.get('GamedayBot_port'),
        keepalives=1,
        keepalives_idle=1)

    cur = conn.cursor()
    #Batch insert of new teams into database
    cs2_args_str = ','.join(cur.mogrify("(%s,%s,%s,%s)", i).decode('utf-8')
                            for i in new_cs2_teams_list)
    cur.execute("INSERT INTO cs2_teams VALUES " + (
        cs2_args_str) + " ON CONFLICT(team_id) DO NOTHING")
    conn.commit()
    cur.close()
    conn.close()

#Attempting to find new teams to add to csv from the upcoming matches
def get_teams_from_upcoming_matches():
    upcoming_games_teams = []
    url = 'https://www.hltv.org/matches'
    #Initializing driver for webscraping
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=op)
    
    try:
        driver.get(url)
        all_matches = driver.find_elements(By.CLASS_NAME, "upcomingMatch")
        for match in all_matches:

            no_game = False
            #See if match exists yet, for example could be placeholder for a future match such as Final or semi-final
            #If no exceptions both team names will be obtained.
            try:
                #Check to see if team is decided yet (doesn't depend on another match result)
                try:
                    team1_name = match.find_element(By.CSS_SELECTOR, ".matchTeam.team1 .matchTeamName").text
                except NoSuchElementException:
                    team1_name = match.find_element(By.CSS_SELECTOR, ".matchTeam.team1 .team").text

                #Check to see if team is decided yet (doesn't depend on another match result)
                try:
                    team2_name = match.find_element(By.CSS_SELECTOR, ".matchTeam.team2 .matchTeamName").text
                except NoSuchElementException:
                    team2_name = match.find_element(By.CSS_SELECTOR, ".matchTeam.team2 .team").text

            except NoSuchElementException:
                no_game = True

            #Scraping match information for each match
            if no_game == False:
                # Getting Team IDs
                team1_id = match.get_attribute("team1")
                team2_id = match.get_attribute("team2")

                if team1_id is not None and team1_id not in {t[0] for t in upcoming_games_teams}:
                    upcoming_games_teams.append((team1_id, team1_name))
                if team2_id is not None and team2_id not in {t[0] for t in upcoming_games_teams}:
                    upcoming_games_teams.append((team2_id, team2_name))

    except Exception as e:
        print(f"Error: {str(e)}")
    
    finally:
        if driver is not None:
            driver.quit()

    return upcoming_games_teams

#Combines old list from csv with new one to create updated csv file with new teams
def create_new_teams_list(cs2_teams, cs2_teams_from_upcoming_matches):
    new_teams = list(set(cs2_teams_from_upcoming_matches) - set(cs2_teams))
    return new_teams

#Adds team_url to list
def create_insertable_new_teams_list(new_cs2_team_list):
    insertable_cs2_teams_list = []

    for team in new_cs2_team_list:
        insertable_cs2_teams_list.append((team[0], team[1], f'https://www.hltv.org/team/{team[0]}/{team[1].replace(" ", "-")}', False))

    return insertable_cs2_teams_list

start_time = time.time()
#Getting list of tuples from the database
cs2_teams = get_cs2_teams_list()

#Getting all teams from upcoming matches
cs2_teams_from_upcoming_matches = get_teams_from_upcoming_matches()

#Adding new teams to the original cs2_teams
new_teams_list = create_new_teams_list(cs2_teams, cs2_teams_from_upcoming_matches)
end_time = time.time()
execution_time = end_time - start_time

#New teams have been found
if len(new_teams_list) > 0:
    #Inserting new teams to database
    insertable_teams_list = create_insertable_new_teams_list(new_teams_list)
    insert_new_teams_to_database(insertable_teams_list)
    insert_result = f"{len(new_teams_list)} New Teams Added"
else:
    insert_result = "No new teams added"

current_time = datetime.now()

print(f"[{current_time}]: get_new_teams_from_upcoming_cs2_matches Executed in {execution_time}, RESULT: {insert_result}")
