from methods import updatePlFixtures, updateGameweekPlayers,updateGameweeks,updateTeams,updatePlPlayers,updateChips,checkDrops,checkReefs
from models import CreateSession,Gameweeks,PlFixtures
from dateutil import tz
import requests
import datetime
import time
from crontab import CronTab
from collections import namedtuple

def getKickoffTimes():
    session=CreateSession()
    q = session.query(PlFixtures.kickoff_time) \
            .distinct(PlFixtures.kickoff_time) \
            .order_by(PlFixtures.kickoff_time) \
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
	job  = cron.new(command='/home/turner_prize/leagueolas/bot-env/bin/python3 /home/turner_prize/leagueolas/league-site/league-site/data/cronWeekly.py',comment='testcomment')
	dt = DateToCron()
	job.setall(dt)
	cron.write()

def CreateMatchCronjobs():
	cron = CronTab(user='turner_prize')
	for i in getKickoffTimes():
		job  = cron.new(command='/home/turner_prize/leagueolas/bot-env/bin/python3 /home/turner_prize/leagueolas/league-site/league-site/data/cron.py',comment='testcomment')
		job.setall(i[0])
		cron.write()


def DataAvailable():
    PC = requests.get("https://fantasy.premierleague.com/api/bootstrap-static")
    try:
        PC.json()
        return True
    except ValueError:
        return False

def WeeklySetup():
    updateGameweeks()
    updatePlFixtures
    updatePlPlayers()
    updateTeams()
    updateChips()
    checkDrops()
    checkReefs()
    CreateWeeklyCronjob()
    

CreateMatchCronjobs()

#while True:
#	if DataAvailable():
#		WeeklySetup()
#		break
#	else:
#		sleep(120)


