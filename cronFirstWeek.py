from methods import getNewPlFixtures, updateGameweekPlayers,updateTeams,updatePlPlayers,updateChips,checkDrops,checkReefs, sendMsg, GetGameweek
from models import CreateSession,Gameweeks,PlFixtures
from dateutil import tz
import requests
import datetime
import time
from crontab import CronTab
from collections import namedtuple
from loguru import logger
from config import cronFirstWeekLogPath,cronWeeklyCommand,cronCommand,cronBonusCommand,cronFinalCommand

def getKickoffTimes():
    session=CreateSession()
    gw=GetGameweek(session)
    q = session.query(PlFixtures.kickoff_time) \
            .distinct(PlFixtures.kickoff_time) \
            .order_by(PlFixtures.kickoff_time) \
            .filter_by(gameweek=gw) \
            .all()
    dtRanges=[]
    for i in q:
        #timezone is UTC from database, need to change to current TZ
        dt = datetime.datetime.strptime(i.kickoff_time,'%Y-%m-%dT%H:%M:%SZ')
        dt=dt.replace(tzinfo=tz.gettz('UTC'))
        KickoffTime=dt
        GameEndTime=KickoffTime + datetime.timedelta(hours=2)
        rng = (KickoffTime,GameEndTime)
        dtRanges.append(rng)
    session.close()
    return LoopIt(dtRanges)

def LoopIt(rng):
    Range = namedtuple('Range', ['start', 'end'])
    for i,val in enumerate(rng):
        try:
            r1 = Range(start=val[0], end=val[1])
            r2 = Range(start=rng[i+1][0], end=rng[i+1][1])
            latest_start = max(r1.start, r2.start)
            earliest_end = min(r1.end, r2.end)
            delta = (earliest_end - latest_start).days + 1
            overlap = max(0, delta)
            if overlap==0:
                pass
            else:
                newRng = (val[0],rng[i+1][1])
                rng[i] = newRng
                rng.pop(i+1)
                LoopIt(rng)
        except IndexError:
            pass
    return rng

def DateToCron():
    session=CreateSession()
    q = session.query(Gameweeks) \
            .filter_by(is_next=1) \
            .first()
            
    dt = datetime.datetime.strptime(q.deadline,'%Y-%m-%dT%H:%M:%SZ')
    dt=dt.replace(tzinfo=tz.gettz('UTC'))
    return dt

def CreateWeeklyCronjob():
	cron = CronTab(user='turner_prize')
	job  = cron.new(command=cronWeeklyCommand)
	dt = DateToCron()
	job.setall(dt)
	cron.write()

def CreateMatchCronjobs():
	cron = CronTab(user='turner_prize')
	for i in getKickoffTimes():
		job  = cron.new(command=cronCommand,comment='Gameweek Match')
		job.setall(i[0])
		cron.write()

def CreateBonusCronjobs():
    cron = CronTab(user='turner_prize')
    session=CreateSession()
    gw=GetGameweek(session)
    q = session.query(PlFixtures.kickoff_time).filter_by(gameweek=gw).all()
    gameDays = set([datetime.datetime.strptime(i[0],'%Y-%m-%dT%H:%M:%SZ').date() for i in q])
    for i in gameDays:
        KO = max([datetime.datetime.strptime(j[0],'%Y-%m-%dT%H:%M:%SZ') for j in q if datetime.datetime.strptime(j[0],'%Y-%m-%dT%H:%M:%SZ').date() == i])
        FT = KO + datetime.timedelta(hours=2)
        job  = cron.new(command=cronBonusCommand,comment='Bonus Points')
        job.setall(FT)
        cron.write()
    session.close()

def CreateFinalCronjobs():
    cron = CronTab(user='turner_prize')
    session=CreateSession()
    gw=GetGameweek(session)
    q = session.query(PlFixtures.kickoff_time).filter_by(gameweek=gw).all()
    KO = max([datetime.datetime.strptime(j[0],'%Y-%m-%dT%H:%M:%SZ') for j in q])
    FT = KO + datetime.timedelta(hours=2)
    job  = cron.new(command=cronFinalCommand,comment='Final Points')
    job.setall(FT)
    cron.write()
    session.close()

def setupLogger():
	logger.add(cronFirstWeekLogPath, format="{time} {level} {message}")

def InitialSetup():
    updatePlPlayers()
    logger.info('plplayers updated')
    CreateMatchCronjobs()
    CreateWeeklyCronjob()
    CreateBonusCronjobs()
    CreateFinalCronjobs()

if __name__ == "__main__":
    setupLogger()
    try:
        InitialSetup()
    except Exception as e:
        logger.info('Error:')
        logger.info(e)
	
