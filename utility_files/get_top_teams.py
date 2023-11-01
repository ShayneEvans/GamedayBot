#Purpose of this script was to scrape top 30 teams from each region on https://www.hltv.org/ranking/teams/{date}
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
op = webdriver.ChromeOptions()
op.add_argument("--headless=new")
op.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

regions = ['',
           '/country/United%20States',
           '/country/Argentina',
           '/country/Brazil',
           '/country/Czech%20Republic',
           '/country/Denmark',
           '/country/Finland',
           '/country/Germany',
           '/country/Poland',
           '/country/Portugal',
           '/country/Russia',
           '/country/Sweden',
           '/country/Ukraine',
           '/country/United%20Kingdom',
           '/country/China',
           '/country/India',
           '/country/Mongolia',
           '/country/Australia',
           '/country/North%20America',
           '/country/Europe',
           '/country/South%20America',
           '/country/Asia',
           '/country/Oceania']

#Could implement scraping the current date of weekly rankings. Not going to do this at this point since I am using another method (get_new_teams_from_upcoming_matches)
def get_current_ranking_period():
    pass

def get_teams(url, all_teams_list):
    driver.get(url)
    all_teams = driver.find_elements(By.CLASS_NAME, "ranked-team")

    for team in all_teams:
        team_name = team.find_element(By.CSS_SELECTOR, ".ranking-header .name").text
        #team_points = int(team.find_element(By.CSS_SELECTOR, ".ranking-header .points").text.replace("(","").replace(")","").replace('points', ""))
        #has_logo = team.find_element(By.CSS_SELECTOR, ".ranking-header .team-logo img").get_attribute('src')
        team_page_url = team.find_element(By.CSS_SELECTOR, ".lineup-con .more a").get_attribute('href')
        team_id = team_page_url.split('/')[4]

        all_teams_list.append((team_id, team_name, team_page_url))

    driver.quit()
    #Removing duplicates and returning list of tuples
    return all_teams_list

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=op)
all_teams = get_teams()
driver.close()