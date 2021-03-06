from methods import updatePlFixtures, updateGameweekPlayers,updateFixturesWithTablePoints,produceTable,createTable,updateTeamsFinalBench,updateDeadlines,updateViceCaptain,updateKOTM
from jancup import updateJanCup
from loguru import logger
from crontab import CronTab
from config import cronFinalLogPath
import time
import requests

def clearCronjobs():
        cron = CronTab(user='turner_prize')

        for job in cron:
                if job.comment in ['Gameweek Match','Bonus Points','Final Points','Cron weekly']:
                        cron.remove(job)
        cron.write()

def setupLogger():
        logger.add(cronFinalLogPath, format="{time} {level} {message}")

if __name__ == "__main__":
        setupLogger()
        logger.info('Starting Final Script')
        while True:
            try:
                r = requests.get("https://fantasy.premierleague.com/api/event-status/")
                x=r.json()
                if x['leagues'] == 'Updated':
                        logger.info('bonus added')
                        updatePlFixtures()
                        updateGameweekPlayers()
                        updateTeamsFinalBench()
                        updateViceCaptain()
                        updateFixturesWithTablePoints()
                        updateDeadlines()
                        produceTable()
                        createTable()
                        updateKOTM()
                        updateJanCup()
                        clearCronjobs()
                        break
                else:
                        logger.info('nothing yet')
                        time.sleep(900)
            except Exception as e:
                        logger.info('Error!')
                        logger.info(e)
        logger.info('Final Update Completed')
