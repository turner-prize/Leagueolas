#!/usr/bin/python

#2nd test comment

from telegram.ext import Updater,CommandHandler, MessageHandler, BaseFilter, Filters
from telegram import Bot
import time
import commands
from config import BotToken

def MessageCheck(Message):
    MyList = ["Dan","Neil","Shed","Matt","Shane","Ads","Tom","Elliott","Crigs","Rholo","Sam"]
    for iname in MyList:
        if re.search('(^|\s)'+iname+'(\s|$)',Message,re.I):
            return True


updater = Updater(token=BotToken)
j = updater.job_queue
dispatcher = updater.dispatcher
b = Bot(token=BotToken)

#---Message Functions

def Scores(bot,update,args):
    if args:
        if not args[0] == 'all':
            bot.send_message(chat_id=update.message.chat_id,text='Please format command /scores all')
        else:
            bot.send_message(chat_id=update.message.chat_id,text=commands.getAllScores())
    else:
        id = update.message.from_user['id']
        msg = commands.getOneScore(id)
        bot.send_message(chat_id=update.message.chat_id,text=msg)

def KingOfTheMountain(bot,update):
    bot.send_message(chat_id=update.message.chat_id,text=f"{commands.KOTM()} is the current King of the Mountain")

def Fixtures(bot,update):
    bot.send_message(chat_id=update.message.chat_id,text=commands.GetNextFixtures())

def Table(bot,update):
    bot.send_photo(chat_id=update.message.chat_id, photo=open('/home/turner_prize/leagueolas/bot/table.png', 'rb'))
    
def classicTable(bot,update):
    bot.send_photo(chat_id=update.message.chat_id, photo=open('/home/turner_prize/leagueolas/bot/classictable.png', 'rb'))

def DraftList(bot, update, args):
    if args:
        if not args[0].upper() in ['GKP','DEF','MID','FWD']:
            bot.send_message(chat_id=update.message.chat_id,text='Please use the following arguements for position:\nGKP\nDEF\nMID\nFWD')
        else:
            bot.send_message(chat_id=update.message.chat_id,text=commands.DraftList(args[0].upper()))
    else:
        bot.send_message(chat_id=update.message.chat_id,text=commands.DraftList())

def PlayersDetailed(bot,update):
    id = update.message.from_user['id']
    msg = commands.PlayersDetailed(id)
    bot.send_message(chat_id=update.message.chat_id,text=msg)

def WhoHas(bot, update, args):
    if args:
    	bot.send_message(chat_id=update.message.chat_id, text=commands.WhoHas(args[0]))

def JC(bot, update):
    bot.send_message(chat_id=update.message.chat_id,text=commands.JanCup())

#def echo(update, context): <--uncomment for debugging
#    print(context)

#---Handlers
#------Commands
Handlers = [] # Command Handlers

def AF2L(FunctionName): # add function 2 list
    Handlers.append(FunctionName)

#------Messages

AF2L(CommandHandler('scores', Scores,pass_args=True))
AF2L(CommandHandler('table', Table))
AF2L(CommandHandler('fixtures', Fixtures))
AF2L(CommandHandler('classico', classicTable))
AF2L(CommandHandler('KOTM', KingOfTheMountain))
AF2L(CommandHandler('playersdetailed', PlayersDetailed))
AF2L(CommandHandler('jancup', JC))
AF2L(CommandHandler('draftlist', DraftList,pass_args=True))
AF2L(CommandHandler('whohas', WhoHas,pass_args=True))
#AF2L(MessageHandler(Filters.text & (~Filters.command), echo))

for f in Handlers:
    dispatcher.add_handler(f)
    

b.send_message(chat_id=282457851,text='Bot Restarted')
   
updater.start_polling()
updater.idle()
