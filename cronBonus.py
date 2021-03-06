from methods import updatePlFixtures, updateGameweekPlayers,updateFixturesWithTablePoints,produceTable,createTable,createFPLClassicoTable
import time
from loguru import logger
from config import cronBonusLogPath
import datetime
import requests



def setupLogger():
        logger.add(cronBonusLogPath, format="{time:YYYY-MM-DD @ HH:mm:ss} | {message}",backtrace=True)

setupLogger()
logger.info('Starting Bonus Script')
bonusAdded = False
while not bonusAdded:
    try:
        r = requests.get("https://fantasy.premierleague.com/api/event-status/")
        x = r.json()
        for i in x['status']:
            if i['date'] == str(datetime.datetime.now().date()):
                if i['bonus_added']:
                    bonusAdded = True
                    logger.info('bonus added')
                    updatePlFixtures()
                    updateGameweekPlayers()
                    updateFixturesWithTablePoints()
                    produceTable()
                    createTable()
                    createFPLClassicoTable()
                    break
                else:
                    logger.info('nothing yet')
                    time.sleep(600)
    except Exception as e:
        logger.info('Error!')
        logger.info(e)
        logger.info('Error Logged, sleeping for 10 mins')
        time.sleep(600)
        logger.info('Continuing')
        
logger.info('Bonus script complete')