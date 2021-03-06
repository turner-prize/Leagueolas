from methods import getNewPlFixtures, updateGameweekPlayers,updateGameweeks,updateTeams,updatePlPlayers,updateChips,checkDrops,checkReefs, sendMsg
from models import CreateSession,Gameweeks,PlFixtures, Fixtures,Managers
from dateutil import tz
import requests
import datetime
import config
import time
from config import cronWeeklyLogPath,cronWeeklyCommand,cronCommand,cronBonusCommand,cronFinalCommand

from crontab import CronTab
from collections import namedtuple
from loguru import logger

def populateFixtures(): 
    r = requests.get(f"https://fantasy.premierleague.com/api/leagues-h2h-matches/league/{config.LeagueCode}/?page=1")
    data = r.json()
    fixtureData = data['results']
    
    session=CreateSession()
    session.query(Fixtures).delete()
    
    for f in fixtureData:
        teamfplid = f['entry_1_entry']
        opponentId = f['entry_2_entry']
        m = session.query(Managers).filter_by(fplId=teamfplid).first()
        o = session.query(Managers).filter_by(fplId=opponentId).first()
        fxtr = Fixtures(gameweek = f['event'],
                        managerId = m.id,
                        opponentId = o.id)
        rvrsfxtr = Fixtures(gameweek = f['event'],
                        managerId = o.id,
                        opponentId = m.id)
        session.add(fxtr)
        session.add(rvrsfxtr)
    session.commit()
    session.close()

def GetGameweek(session):
    gw = session.query(Gameweeks.id).filter_by(is_current=1).first()
    return gw[0]

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
	job  = cron.new(command=cronWeeklyCommand,comment='Cron weekly')
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

def DataAvailable():
    PC = requests.get("https://fantasy.premierleague.com/api/event-status/")
    try:
        if PC.json() == "The game is being updated.":
            return False
        else:
            return True
    except ValueError:
        return False

def setupLogger():
	logger.add(cronWeeklyLogPath, format="{time} {level} {message}")

def WeeklySetup():
    updateGameweeks()
    logger.info('gameweeks updated')
    session=CreateSession()
    gw=GetGameweek(session)
    session.close()
    if gw == 1:
        populateFixtures()
    logger.info('fixtures populated,for first week at least')
    getNewPlFixtures()
    logger.info('plfixtures updated')
    updatePlPlayers()
    logger.info('plplayers updated')
    updateTeams()
    logger.info('Teams updated')
    updateChips()
    logger.info('chips updated')
    checkDrops()
    logger.info('drops updated')
    checkReefs()
    logger.info('reefs updated')
    CreateMatchCronjobs()
    CreateWeeklyCronjob()
    CreateBonusCronjobs()
    CreateFinalCronjobs()   
    sendMsg("Data updated, the gameweek has begun!")

if __name__ == "__main__":
    setupLogger()
    sendMsg("Deadline has passed! Congratulations to Elmo who has taken a decade to literally win anything!")
    logger.info('sleeping for 5 minutes to not fuck things up')
    time.sleep(300)
    while True:
        try:
            logger.info('trying to access api')
            if DataAvailable():
                logger.info('success! running weekly setup')
                WeeklySetup()
                break
            else:
                logger.info('not available, sleeping for 2 minutes')
                time.sleep(120)
        except Exception as e:
            logger.info('Error:')
            logger.info(e)
            break
	
