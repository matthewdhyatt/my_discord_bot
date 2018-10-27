import discord
from discord.ext import commands
import random
import os
import psycopg2
from psycopg2 import sql
from datetime import datetime

token=os.environ['TOKEN']
DATABASE_URL = os.environ['DATABASE_URL']

#constants
prefix='?'
wsclear_roles={'First Officer', 'Officer', 'Bot Handler'}

#a function for getting member when it's the optional second word in a message (in mention form)
def lookup_member(message):
    x=message.content.split()
    if len(x)>1:
        for member in message.server.members:
            if x[1]==member.mention:
                candidate=member
                break
        else:
            candidate=''
    else:
        candidate=message.author
    return candidate

#open connection to the database
def dbopen():
    global conn
    global cur
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()

#close connection to the database, don't forget to commit changes!!!
def dbclose():
    global conn
    global cur
    cur.close()
    conn.close()



client = discord.Client()



@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    print('')

    dbopen()
    #for server in client.servers:
    for server in client.guilds:
        #print(server)
        #print(server.id)
        tablename=sql.Identifier('server'+server.id)
        #COLUMNS: memberid, ws_joined, ws_join_time, wsgear
        SQL=sql.SQL('CREATE TABLE IF NOT EXISTS {} (memberid varchar PRIMARY KEY, ws_joined boolean, ws_join_time timestamp, wsgear varchar)').format(tablename)
        cur.execute(SQL)
        for member in server.members:
            SQL=sql.SQL('INSERT INTO {} (memberid) SELECT %s WHERE NOT EXISTS (SELECT memberid FROM {} WHERE memberid = %s)').format(tablename,tablename)
            cur.execute(SQL,(member.id,member.id))

        #use this to print database info
        '''
        cur.execute('SELECT * FROM server{};'.format(server.id))
        for x in cur.fetchall():
            print(server.get_member(x[0]).name,x[1:])
        print('')
        '''

        #create a role for all people currently playing the white star
        '''
        def create_role(newrole):
            for x in server.roles:
                if x.name==newrole:
                    break
            else:
                try:
                    await client.create_role(server,name=newrole,mentionable=True)
                except:
                    print('bot does not have role permissions on server {}'.format(server))
        #create_role('WSplaying')
        #create_role('Offense')
        #create_role('Defense')
        '''

    conn.commit()
    dbclose()



        
@client.event
async def on_message(message):
    #private messages not supported
    if not message.server:
        return

    #msg is the bot's reply
    msg=''
    #used for SQL commands
    tablename=sql.Identifier('server'+message.server.id)

    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    #just to say hi to you
    elif message.content.startswith(prefix+'hello'):
        msg = 'Hello {0.author.mention}'.format(message)

    #join or add someone to a squad
    elif message.content.startswith(prefix+'squad'):
        candidate=lookup_member(message)
        if candidate=='':
            msg = message.content.split()[1]+' is not on this server'
        else:
            try:
                newrole = message.content.split()[2]
                if newrole.lower() in ['offense', 'off']:
                    role = discord.utils.get(candidate.server.roles, name="Offense")
                    await client.add_roles(candidate,role)
                    msg = '{0.mention} has been added to the Offense squad!'.format(candidate)
                elif newrole.lower() in ['defense', 'def']:
                    role = discord.utils.get(candidate.server.roles, name="Defense")
                    await client.add_roles(candidate,role)
                    msg = '{0.mention} has been added to the Defense squad!'.format(candidate)
                elif newrole.lower() in ['other', 'none']:
                    role=discord.utils.get(candidate.server.roles, name="Offense")
                    await client.remove_roles(candidate,role)
                    role=discord.utils.get(candidate.server.roles, name="Defense")
                    await client.remove_roles(candidate,role)
                    msg = '{0.mention} has been removed from the Offense/Defense squads'.format(candidate)
            except:
                pass      
        
    #join or add someone to the roster for the next white star mission!
    elif message.content.startswith(prefix+'join'):
        candidate=lookup_member(message)
        if candidate=='':
            msg = message.content[6:]+' is not on this server'
        else:
            dbopen()
            SQL=sql.SQL('INSERT INTO {} (memberid) SELECT %s WHERE NOT EXISTS (SELECT memberid FROM {} WHERE memberid = %s)').format(tablename,tablename)
            cur.execute(SQL,(candidate.id,candidate.id))
            conn.commit()
            SQL=sql.SQL('SELECT ws_joined FROM {} WHERE memberid = %s').format(tablename)
            cur.execute(SQL,(candidate.id,))
            if cur.fetchone()[0]:
                msg = '{0.name} is already on the White Star roster'.format(candidate)
            else:
                now=datetime.now()
                SQL=sql.SQL('UPDATE {} SET ws_joined = True, ws_join_time = %s WHERE memberid = %s').format(tablename)
                cur.execute(SQL,(datetime.now(),candidate.id))
                conn.commit()
                try:
                    role=discord.utils.get(candidate.server.roles, name="WSplaying")
                    await client.add_roles(candidate,role)
                except:
                    pass
                msg = '{0.mention} has been added to the White Star roster!'.format(candidate)
            dbclose()
            
        
    #remove yourself or someone else from the roster for the next white star mission :(
    elif message.content.startswith(prefix+'unjoin'):
        candidate=lookup_member(message)
        if candidate=='':
            msg = message.content[8:]+' is not on this server'
        else:
            dbopen()
            SQL=sql.SQL('SELECT ws_joined FROM {} WHERE memberid = %s').format(tablename)
            cur.execute(SQL,(candidate.id,))
            if not cur.fetchone()[0]:
                msg = '{0.name} was not on the White Star roster anyway'.format(candidate)
            else:
                SQL=sql.SQL('UPDATE {} SET ws_joined = False, ws_join_time = NULL, wsgear = NULL WHERE memberid = %s').format(tablename)
                cur.execute(SQL,(candidate.id,))
                conn.commit()
                try:
                    role=discord.utils.get(candidate.server.roles, name="WSplaying")
                    await client.remove_roles(candidate,role)
                except:
                    pass
                msg = '{0.mention} has been removed from the White Star roster'.format(candidate)
            dbclose()
            
    #clear the ws roster
    elif message.content.startswith(prefix+'wsclear'):
        for role in message.author.roles:
            if role.name in wsclear_roles:
                for user in message.server.members:
                    try:
                        role=discord.utils.get(message.server.roles, name="WSplaying")
                        await client.remove_roles(user,role)
                    except:
                        pass
                    
                dbopen()
                SQL=sql.SQL('UPDATE {} SET ws_joined = %s, ws_join_time = NULL, wsgear = NULL').format(tablename)
                cur.execute(SQL,(False,))
                conn.commit()
                msg = 'The White Star roster and gear list have been cleared'
                dbclose()
                break
        else:
            msg = 'Sorry, you don\'t have clearance to clear the roster, Clarence. Please ask someone with role {}.'.format(wsclear_roles)

    #indiviually mention everybody on the server, please use this sparingly!!!
    elif message.content.startswith(prefix+'everybody'):
        for role in message.author.roles:
            if role.name in wsclear_roles:
                msg = ''
                for member in message.server.members:
                    msg += member.mention+' '
                break
        else:
            msg = 'Sorry, you don\'t have clearance to use this command. Please ask someone with role {}.'.format(wsclear_roles)
    
    #Individually mention everybody on ws roster. In next update this should actually create a role and add players to it.
    elif message.content.startswith(prefix+'wsmention'):
        for role in message.author.roles:
            if role.name in wsclear_roles:
                dbopen()
                cur.execute('SELECT memberid FROM server{} WHERE ws_joined = True;'.format(message.server.id))
                ws_roster=list(cur.fetchall())
                dbclose()
                msg = ''
                for memberid in ws_roster:
                    msg += message.server.get_member(memberid[0]).mention + ' '
                break
        else:
            msg = 'Sorry, you don\'t have clearance to use this command. Please ask someone with role {}.'.format(wsclear_roles)
    
    #print the current white star roster    
    elif message.content.startswith(prefix+'wswho'):
        dbopen()
        cur.execute('SELECT memberid FROM server{} WHERE ws_joined = True ORDER BY ws_join_time;'.format(message.server.id))
        ws_roster=list(cur.fetchall())
        dbclose()
        if ws_roster==[]:
            msg = 'The White Star roster is currently empty'
        else:
            msg = 'CURRENT WHITE STAR ROSTER'+'\n'
            for i in range(len(ws_roster)):
                msg += '{}. '.format(i+1)+message.server.get_member(ws_roster[i][0]).name+'\n'

    #declare the gear you're bringing to this white star mission
    elif message.content.startswith(prefix+'mygear'):
        dbopen()
        SQL=sql.SQL('SELECT ws_joined FROM {} WHERE memberid = %s').format(tablename)
        cur.execute(SQL,(message.author.id,))
        if not cur.fetchone()[0]:
            msg = '{0.name} is not on the White Star roster! Please sign up first using the {1}join command.'.format(message.author,prefix)
        else:
            gear=message.content[8:]
            SQL=sql.SQL('UPDATE {} SET wsgear = %s WHERE memberid = %s').format(tablename)
            cur.execute(SQL,(gear,message.author.id))
            conn.commit()
            msg = '{0.mention} has updated his/her gear for the White Star'.format(message.author)
        dbclose()

    #you can also declare someone else's gear using othersgear [@name] [gear] 
    elif message.content.startswith(prefix+'othersgear'):
        candidate=lookup_member(message)
        if candidate=='':
            msg = message.content.split()[1]+' is not on this server'
        else:
            dbopen()
            SQL=sql.SQL('SELECT ws_joined FROM {} WHERE memberid = %s').format(tablename)
            cur.execute(SQL,(candidate.id,))
            if not cur.fetchone()[0]:
                msg = '{0.name} is not on the White Star roster! Please sign up first using the {1}join command.'.format(candidate,prefix)
            else:
                gear=''
                for w in message.content.split()[2:]:
                    gear+=w+' '
                SQL=sql.SQL('UPDATE {} SET wsgear = %s WHERE memberid = %s').format(tablename)
                cur.execute(SQL,(gear,candidate.id))
                conn.commit()
                msg = '{0.mention} has had his/her gear updated for the White Star'.format(candidate)
            dbclose()

    #print the current white star gear list   
    elif message.content.startswith(prefix+'teamgear'):
        dbopen()
        cur.execute('SELECT memberid,wsgear FROM server{} WHERE ws_joined = True ORDER BY ws_join_time;'.format(message.server.id))
        ws_gear=list(cur.fetchall())
        dbclose()
        if ws_gear==[]:
            msg = 'The White Star roster is currently empty, please add some players first'
        else:
            msg = 'CURRENT WHITE STAR GEAR'+'\n \n'
            for x in ws_gear:
                if x[1]:
                    msg += message.server.get_member(x[0]).name+': '+x[1]+'\n \n'
                else:
                    msg += message.server.get_member(x[0]).name+': '+'\n \n'
        
    #list everyone on this server
    elif message.content.startswith(prefix+'who'):
        msg = ''
        for member in message.server.members:
            msg += member.name+', '
        if msg!='':
            msg=msg[:-2]

    #the help page
    elif message.content.startswith(prefix+'help'):
        msg = prefix+'help : prints this page \n \n'
        msg += prefix+'join : adds your name to ws roster \n \n'
        msg += prefix+'join [@name] : add someone else to ws roster \n \n'
        msg += prefix+'unjoin : remove your name from the ws roster \n \n'
        msg += prefix+'unjoin [@name] : remove someone else from the ws roster \n \n'
        msg += prefix+'wswho : prints the current ws roster \n \n'
        msg += prefix+'wsclear : clear the ws roster and gear list \n \n'
        msg += prefix+'mygear [gear] : declares that you will bring [gear] to the next ws \n \n'
        msg += prefix+'othersgear [@name] [gear] : declares that [@name] will bring [gear] to the next ws \n \n'
        msg += prefix+'teamgear : prints the current list of team gear for the next ws'

    #now send the bot's reply!
    if msg!='':   
        await client.send_message(message.channel, msg)



client.run(token)
