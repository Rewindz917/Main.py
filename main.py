from discord import *
import discord
import datetime
import json
import chat_exporter
import io
import datetime
import sqlite3
import asyncio
from discord import *
from discord.ext import commands, tasks
import pytz
import random
import string
from vars import *
from typing import Union
from decimal import Decimal, ROUND_DOWN
from cogs.tickets import *
from cogs.Buttons.Assign import *

from dotenv import load_dotenv
load_dotenv()

conn = sqlite3.connect('user.db')
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS ticket 
           (id INTEGER PRIMARY KEY AUTOINCREMENT, discord_name TEXT, discord_id INTEGER, channel_id INTEGER, staff_id INTEGER, vocal_chat INTEGER, ticket_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
conn.commit()
conn.close()

conninvoices = sqlite3.connect('invoicesID.db')
cursorinvoices = conninvoices.cursor()

cursorinvoices.execute('''
    CREATE TABLE IF NOT EXISTS invoices (
        invoice_id TEXT PRIMARY KEY,
        user_id TEXT,
        product TEXT,
        product_subscription TEXT,
        payment_method TEXT,
        payment_total REAL,
        paid BOOLEAN,
        date_and_time DATETIME
    )
''')

cursorinvoices.execute('''
    CREATE TABLE IF NOT EXISTS loyalty (
        discord_id TEXT PRIMARY KEY,
        earnings REAL
    )
''')

conninvoices.commit()
conninvoices.close()

connInteractions = sqlite3.connect("interactions.db")
cursorInteractions = connInteractions.cursor()

cursorInteractions.execute('''
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        selected_product TEXT,
        selected_sub TEXT,
        payment_total REAL,
        payment_method TEXT,
        invoice_id TEXT,
        paid TEXT,
        channel_id INTEGER
    )
''')

cursorInteractions.execute('''
    CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        selected_product TEXT,
        selected_sub TEXT,
        payment_total REAL,
        payment_method TEXT,
        invoice_id TEXT,
        paid TEXT,
        channel_id INTEGER,
        referral TEXT,
        reward REAL
    )
''')

connInteractions.commit()
connInteractions.close()

connStaff = sqlite3.connect('staffstats.db')
curStaff = connStaff.cursor()

curStaff.execute("""CREATE TABLE IF NOT EXISTS staffer (
                id INTEGER PRIMARY KEY,
                discord_id INTEGER,
                tickets_managed INTEGER DEFAULT 0,
                total_rates INTEGER DEFAULT 0,
                staff_rating INTEGER DEFAULT 0
            )""")
connStaff.commit()
connStaff.close()

connRF = sqlite3.connect('referral.db')
cursorRF = connRF.cursor()

cursorRF.execute('''
    CREATE TABLE IF NOT EXISTS referrals (
        discord_id TEXT PRIMARY KEY,
        referral_code TEXT UNIQUE,
        earnings INTEGER
    )
''')
connRF.commit()
connRF.close()

class Bot(commands.Bot):
    def __init__(self, intents: discord.Intents, **kwargs):
        super().__init__(command_prefix="$", intents=intents, case_insensitive=True)

    async def on_ready(self):
        print(f'Logged in as {self.user.name} ({self.user.id})')
        await bot.change_presence(activity=discord.Streaming(name="Hanzo FN", url="https://twitch.tv/HanzoFN"))
        await self.tree.sync()

intents = discord.Intents.all()
bot = Bot(intents=intents)

@bot.event
async def on_member_remove(member):
    memberID = member.id
    conn = sqlite3.connect("user.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM ticket WHERE discord_id = ?
    ''', (memberID,))
    resultsInv = cursor.fetchall()
    conn.close()
    if resultsInv is not None:
        rowInv = resultsInv[0]
        channel_id = rowInv[3]
        with sqlite3.connect('user.db') as conn:
            cur = conn.cursor()
            guild = bot.get_guild(member.guild)
            channel_log = bot.get_channel(transcripts_channel)
            channel = bot.get_channel(channel_id)
            topic = channel.topic
            parts = topic.split(" | ")
            ticket_creator = int(parts[1])
            cur.execute("DELETE FROM ticket WHERE discord_id=?", (ticket_creator,))
            conn.commit()

            military_time: bool = True
            transcript = await chat_exporter.export(
                channel,
                limit=200,
                tz_info=timezone_set,
                military_time=military_time,
                bot=bot,
            )       
            if transcript is None:
                return
            
            transcript_file = discord.File(
                io.BytesIO(transcript.encode()),
                filename=f"transcript-{channel.name}.html")
            transcript_file2 = discord.File(
                io.BytesIO(transcript.encode()),
                filename=f"transcript-{channel.name}.html")
            
            embed = discord.Embed(
                title=f"{emoji_hanzo} Hanzo | Ticket Closed {emoji_hanzo}",
                description=(
                        f"Thank you for using our ticketing system. This ticket is now closed.\n\n"
                        f"**Opened By**: {ticket_creator.mention}\n"
                        f"**Closed By**: User Leaved\n\n"
                ),
                color=default_color
            )
            await channel.send(embed=embed)
            transcript_info_log2 = discord.Embed(
            title=f"{emoji_hanzo} Hanzo | Ticket Closed {emoji_hanzo}",
            description=(
                f"This ticket is now closed, signifying the conclusion of its journey.\n\n"
                f"**Ticket Opened By**: {ticket_creator.mention}\n"
                f"**Ticket Name**: {channel.name}\n"
                f"**Closed By**: User Leaved\n\n"
            ),
                color=default_color
            )
            await channel_log.send(embed=transcript_info_log2, file=transcript_file2)
            await asyncio.sleep(3)
            await channel.delete(reason="Ticket deleted.")
        conn.close()

@bot.hybrid_command(name="stafftop", description="show staff top 10")
@commands.has_role(staff_team_id)
async def top_staffers(ctx):
    connStaff = sqlite3.connect('staffstats.db')
    curStaff = connStaff.cursor()
    curStaff.execute("SELECT discord_id, tickets_managed FROM staffer ORDER BY tickets_managed DESC LIMIT 10")
    top_staffers = curStaff.fetchall()
    connStaff.close()
    embed = discord.Embed(
        title=f"{emoji_hanzo} Top 10 Staffers {emoji_hanzo}",
        color=default_color
    )

    for rank, (discord_id, tickets_managed) in enumerate(top_staffers, start=1):
        member = ctx.guild.get_member(discord_id)
        member_name = member.name if member else f"Unknown Member ({discord_id})"
        
        embed.add_field(
            name=f"{rank}. {member_name}",
            value=f"Tickets Solved: {tickets_managed}",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.hybrid_command(name="staffrating", description="show staff rating top 10")
@commands.has_role(staff_team_id)
async def staffrating(ctx):
    connStaff = sqlite3.connect('staffstats.db')
    curStaff = connStaff.cursor()
    curStaff.execute("SELECT discord_id, staff_rating, total_rates FROM staffer")
    all_staffers = curStaff.fetchall()
    sorted_staffers = sorted(all_staffers, key=lambda x: (x[1]/x[2]) if x[2] != 0 else 0, reverse=True)[:10]

    connStaff.close()

    embed = discord.Embed(
        title=f"{emoji_hanzo} Top 10 Staffers {emoji_hanzo}",
        color=default_color
    )

    for rank, (discord_id, staff_rating, total_rates) in enumerate(sorted_staffers, start=1):
        member = ctx.guild.get_member(discord_id)
        member_name = member.name if member else f"Unknown Member ({discord_id})"
        
        ratio_value = staff_rating / total_rates if total_rates != 0 else 0
        ratio_str = f"{staff_rating}/{total_rates}" if total_rates != 0 else "N/A"
        embed.add_field(
            name=f"{rank}. {member_name}",
            value=f"Staff Rating: {ratio_value:.2f} ({staff_rating}/{total_rates})",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.hybrid_command(name="optionally", description="create a ticket vocal channel")
@commands.has_role(staff_team_id)
async def vocal_command(self):
    if any(role.id == staff_team_id for role in self.author.roles):
        message = f"# Voice call __option__  {emoji_call}\nYou have the choice to either **__accept__** or **__decline__** this option.\n\nPlease leave a check if you would like to **__accept__** `✅`\n\nIf you prefer to chat with a customer representative please Click **__decline__**  `❌`\n\n**__SUPPORTED LANGUAGES __** {emoji_swift}\n\n**__English__ {emoji_english}\n__Arabic__  {emoji_arabic}\n__French __ {emoji_french} \n__Spanish__ {emoji_spanish} **"
        file_path = "optionally.png"
        file = discord.File(fp=file_path, filename="optionally.png")
        message_reply = await self.reply(message, file=file)

        await message_reply.add_reaction("✅")
        await message_reply.add_reaction("❌")

        def check(reaction, user):
            return user == self.author and str(reaction.emoji) in ["✅", "❌"]

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=120, check=check)

            if str(reaction.emoji) == "✅":
                await message_reply.delete()
                conn = sqlite3.connect('user.db')
                cur = conn.cursor()

                guild = self.guild
                topic = self.channel.topic
                transcript_channel = self.guild.get_channel(transcripts_channel)
                parts = topic.split(" | ")
                ticket_creator_id = int(parts[1])
                ticket_creator = guild.get_member(int(parts[1]))

                channel_id = self.channel.id
                cur.execute("SELECT * FROM ticket WHERE channel_id=?", (channel_id,))
                ticket_row = cur.fetchone()
                if ticket_row:
                    staff_id = ticket_row[4]
                    guild = self.guild
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        self.author: discord.PermissionOverwrite(view_channel=True),
                    }
                    if staff_id:
                        staff_member = guild.get_member(staff_id)
                        if staff_member:
                            overwrites[staff_member] = discord.PermissionOverwrite(view_channel=True)

                    name = ticket_creator.name
                    vocal_channel = await guild.create_voice_channel(name=name, overwrites=overwrites)

                    staffembed = discord.Embed(
                        title=f"{emoji_hanzo} Hanzo | Vocal Chat {emoji_hanzo}",
                        description=(
                            f"{vocal_channel.mention} ***has been created for this ticket!***\n"
                        ),
                        color=default_color
                    )
                    await self.reply(embed=staffembed)
                    cur.execute("UPDATE ticket SET vocal_chat=? WHERE channel_id=?", (vocal_channel.id, self.channel.id))
                    conn.commit()
                    conn.close()
                else:
                    await self.reply("No ticket found for this channel.", ephemeral=True)
                    conn.close()
            elif str(reaction.emoji) == "❌":
                await message_reply.delete()
        except asyncio.TimeoutError:
                await message_reply.delete()
    else:
        await self.reply("Only staffers can create a vocal channel.", ephemeral=True)

@bot.hybrid_command(name='delreferraluser', description='Delete a user from the database by Discord ID (OWNER ONLY)')
@commands.has_role(owner_role_id)
async def delreferraluser(ctx: commands.Context, user: discord.User):
    with sqlite3.connect('referral.db') as connRF:
        cursorRF = connRF.cursor()
        user_id = user.id

        cursorRF.execute('SELECT * FROM referrals WHERE discord_id = ?', (str(user_id),))
        connRF.commit()
        user_info = cursorRF.fetchone()

        if user_info:
            cursorRF.execute('DELETE FROM referrals WHERE discord_id = ?', (str(user_id),))
            connRF.commit()
            embed = discord.Embed(
                title=f"{emoji_money} Database Actions {emoji_money}",
                description=(
                    f"User ID: ```{user_id}```\nStatus: ```Deleted from database```"
                ),
                color=default_color
            )
            await ctx.send(embed=embed)
        else:

            embed = discord.Embed(
                title=f"{emoji_money} Database Actions {emoji_money}",
                description=(
                    f"User ID: ```{user_id}```\nStatus: ```Not present in database```"
                ),
                color=default_color
            )
            await ctx.send(embed=embed)
    connRF.close()

@bot.hybrid_command(name="lookupinvoiceid", description="check a invoice id")
@commands.has_role(owner_role_id)
async def invoice_id_lookup(self, invoice_id):
    try:
        with sqlite3.connect('invoicesID.db') as conninvoices:
            cursorinvoices = conninvoices.cursor()
            cursorinvoices.execute('''
                SELECT * FROM invoices
                WHERE invoice_id = ?
            ''', (invoice_id,))
            conninvoices.commit()
            result = cursorinvoices.fetchone()

            if result:
                invoice_info_embed = discord.Embed(
                    title=f"{emoji_hanzo} Invoice ID Info {emoji_hanzo}\nInvoice ID:```{invoice_id}```",
                    description=(
                        f"Product: ```{result[2]}```\n"  
                        f"Product Sub: ```{result[3]}```\n"  
                        f"Payment Method: ```{result[4]}```\n" 
                        f"Payment Total: ```${result[5]}```\n"  
                        f"User ID: ```{result[1]}```\n"
                        f"Paid: ```{result[6]}```\n"  
                        f"Date and Time: ```{result[7]}```"  
                    ),
                    color=default_color
                )

                await self.send(embed=invoice_info_embed)
            else:
                await self.send(f"No information found for Invoice ID: {invoice_id}")
        conninvoices.close()
    except Exception as e:
        print(f"Error fetching invoice information from the database: {e}")


def generate_referral_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

@bot.hybrid_command(name="referral", description="Generate the referral code")
async def referral(ctx: commands.Context, user: discord.User):
    if ctx.author.bot:
        return
    
    user_id = user.id
    with sqlite3.connect('referral.db') as connRF:
        cursorRF = connRF.cursor()
        cursorRF.execute('SELECT * FROM referrals WHERE discord_id = ?', (str(user_id),))
        connRF.commit()
        existing_user = cursorRF.fetchone()

        if existing_user:
            discord_id, referral_code, earnings = existing_user
            embed = discord.Embed(
                title=f"{emoji_money} Referral Action {emoji_money}",
                description=(
                    f"User ID: ```{discord_id}```\nStatus: ```Already Have a Referral Code```\nReferral Code: ```{referral_code}```\nEarnings: ```${earnings}```"
                ),
                color=default_color
            )
            await ctx.send(embed=embed)
        else:
            referral_code = generate_referral_code()
            cursorRF.execute('INSERT INTO referrals VALUES (?, ?, ?)', (str(user_id), referral_code, 0))
            connRF.commit()
            embed = discord.Embed(
                title=f"{emoji_money} Referral Action {emoji_money}",
                description=(
                    f"User ID: ```{user_id}```\nStatus: ```Activated```\nUser Referral: ```{referral_code}```"
                ),
                color=default_color
            )
            await ctx.send(embed=embed)
    connRF.close()

class Referral(commands.Converter):
    async def convert(self, ctx, argument):
        with sqlite3.connect('referral.db') as connRF:
            cursorRF = connRF.cursor()
            cursorRF.execute('SELECT * FROM referrals WHERE referral_code = ?', (argument,))
            connRF.commit()
            referral_data = cursorRF.fetchone()


            if not referral_data:
                return "Invalid referral code. Please check and try again."
            
            return referral_data

@bot.hybrid_command(name='redeem', description='Redeem a referral code (OWNER ONLY)')
@commands.has_role(owner_role_id)
async def redeem(ctx: commands.Context, referral: Referral, total_payment: float):
    if 'Invalid' in referral:
        embed = discord.Embed(
            title=f"{emoji_money} Earnings Action {emoji_money}",
            description=(
                f"Error: ```Invalid Referral Code```"
            ),
            color=default_color
        )
        await ctx.send(embed=embed)
    else:
        with sqlite3.connect('referral.db') as connRF:
            cursorRF = connRF.cursor()
            _, referral_code, earnings = referral
            reward_decimal = Decimal(str(float(total_payment) * (percentage_of_redeem / 100))).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
            reward2 = float(reward_decimal)
            cursorRF.execute('SELECT earnings FROM referrals WHERE referral_code = ?', (referral[1],))
            current_earnings = cursorRF.fetchone()[0]
            new_earnings = current_earnings + reward2
            cursorRF.execute('UPDATE referrals SET earnings = ? WHERE referral_code = ?', (new_earnings, referral[1]))

            connRF.commit()

            embed = discord.Embed(
                title=f"{emoji_money} Earnings Action {emoji_money}",
                description=(
                    f"Referral: ```{referral_code}```\nStatus: ```Redeemed successfully```\nUser Earn: ```${reward2}```"
                ),
                color=default_color
            )
            await ctx.send(embed=embed)    
        connRF.close()

@bot.hybrid_command(name='userearnings', description='Get earnings for a user by Discord ID')
async def earningsUSER(ctx: commands.Context, user: discord.User):
    user_id = user.id
    with sqlite3.connect('referral.db') as connRF:
        cursorRF = connRF.cursor()
        cursorRF.execute('SELECT * FROM referrals WHERE discord_id = ?', (str(user_id),))
        connRF.commit()
        user_info = cursorRF.fetchone()


        if user_info:
            discord_id, referral_code, earnings = user_info
            embed = discord.Embed(
                title=f"{emoji_money} Earnings {emoji_money}",
                description=(
                    f"Referral: ```{referral_code}```\nDiscord ID: ```{discord_id}```\nEarnings: ```${earnings}```"
                ),
                color=default_color
            )
            await ctx.send(embed=embed)
        else:
            
            embed = discord.Embed(
                title=f"{emoji_money} Earnings {emoji_money}",
                description=(
                    f"Discord ID: ```{user_id}```\nStatus: ```No earnings found```"
                ),
                color=default_color
            )
            await ctx.send(embed=embed)
    connRF.close()

@bot.hybrid_command(name='delreferral', description='Delete a referral from the database (OWNER ONLY)')
@commands.has_role(owner_role_id)
async def delete_referral(ctx: commands.Context, referral_code):
    with sqlite3.connect('referral.db') as connRF:
        cursorRF = connRF.cursor()
        cursorRF.execute('SELECT * FROM referrals WHERE referral_code = ?', (referral_code,))
        referral_info = cursorRF.fetchone()
        connRF.commit()
        if referral_info:
            cursorRF.execute('DELETE FROM referrals WHERE referral_code = ?', (referral_code,))
            connRF.commit()
            embed = discord.Embed(
                title=f"{emoji_money} Database Actions {emoji_money}",
                description=(
                    f"Referral: ```{referral_code}```\nStatus: ```Deleted from database```"
                ),
                color=default_color
            )
            await ctx.send(embed=embed)
        else:        
            embed = discord.Embed(
                title=f"{emoji_money} Database Actions {emoji_money}",
                description=(
                    f"Referral: ```{referral_code}```\nStatus: ```Not present in database```"
                ),
                color=default_color
            )
            await ctx.send(embed=embed)
    connRF.close()

@bot.hybrid_command(name='idearnings', description='Get earnings for a referral code')
async def earningsID(ctx: commands.Context, referral_code):
    with sqlite3.connect('referral.db') as connRF:
        cursorRF = connRF.cursor()
        cursorRF.execute('SELECT * FROM referrals WHERE referral_code = ?', (referral_code,))
        connRF.commit()
        referral_info = cursorRF.fetchone()

        if referral_info:
            discord_id, referral_code, earnings = referral_info
            embed = discord.Embed(
                title=f"{emoji_money} Referral Info {emoji_money}",
                description=(
                    f"Referral: ```{referral_code}```\nDiscord ID: ```{discord_id}```\nEarnings: ```${earnings}```"
                ),
                color=default_color
            )
            await ctx.send(embed=embed)
        else:            
            embed = discord.Embed(
                title=f"{emoji_money} Earnings {emoji_money}",
                description=(
                    f"Referral Code: ```{referral_code}```\nStatus: ```No earnings found```"
                ),
                color=default_color
            )
            await ctx.send(embed=embed)

    connRF.close()

@bot.hybrid_command(name="add", description="add user in the current ticket")
@commands.has_role(staff_team_id)
async def add(ctx: commands.Context, user: discord.User):
    
    user_id = user.id
    member = ctx.guild.get_member(user_id)
    await ctx.channel.set_permissions(member, send_messages=True, read_messages=True, add_reactions=False,
                                                embed_links=True, attach_files=True, read_message_history=True,
                                                external_emojis=True)
    ctx.embed = discord.Embed(
        title=f"{emoji_hanzo} Hanzo | Member Added {emoji_hanzo}",
        description=(
            f"{member.mention} ***has been added to this ticket*** (<#{ctx.channel.id}>)!\n"
        ),
        color=default_color
    )
    await ctx.reply(embed=ctx.embed)

@bot.hybrid_command(name="remove", description="remove an user from the current ticket")
@commands.has_role(staff_team_id)
async def remove(ctx: commands.Context, user: discord.User):

    user_id = user.id
    member = ctx.guild.get_member(user_id)
    await ctx.channel.set_permissions(member, send_messages=False, read_messages=False, add_reactions=False,
                                            embed_links=False, attach_files=False, read_message_history=False,
                                            external_emojis=False)
    ctx.embed = discord.Embed(
        title=f"{emoji_hanzo} Hanzo | Member Removed {emoji_hanzo}",
        description=(
            f"{member.mention} ***has been removed from this ticket*** (<#{ctx.channel.id}>)!\n"
        ),
        color=default_color
    )
    await ctx.reply(embed=ctx.embed)

@bot.hybrid_command(name="nuke", description="clone a channel and delete the old one")
@commands.has_role(owner_role_id)
async def nuke(ctx):
    embed = discord.Embed(
    title=f"{emoji_hanzo} Channel Nuked {emoji_hanzo}",
    description=(
        f"\n\n***This channel has been nuked by {ctx.author.mention}!***"
    ),
    color=default_color
    )
    channel = ctx.channel
    new_channel = await channel.clone()
    await new_channel.send(embed=embed)
    await channel.delete()

@bot.hybrid_command(name="delete", description="delete the current ticket")
@commands.has_role(staff_team_id)
async def delete_ticket(self):
    with sqlite3.connect('user.db') as conn:
        cur = conn.cursor()
        guild = self.bot.get_guild(guild_id)
        channel = self.bot.get_channel(transcripts_channel)
        topic = self.channel.topic
        parts = topic.split(" | ")
        ticket_creator = int(parts[1])

        military_time: bool = True
        transcript = await chat_exporter.export(
            self.channel,
            limit=200,
            tz_info=timezone_set,
            military_time=military_time,
            bot=self.bot,
        )       
        if transcript is None:
            return
        
        cur.execute('''
                SELECT * FROM ticket WHERE channel_id = ?
            ''', (self.channel.id,))
        resultsVoc = cur.fetchall()

        if resultsVoc:
            row = resultsVoc[0]
            rowVocal = row[5]
            
            if rowVocal is not None:
                vocal_chat = self.guild.get_channel(rowVocal)
                
                if vocal_chat is not None:
                    await vocal_chat.delete()

        cur.execute("DELETE FROM ticket WHERE discord_id=?", (ticket_creator,))
        conn.commit()

        transcript_file = discord.File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{self.channel.name}.html")
        transcript_file2 = discord.File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{self.channel.name}.html")
        
        ticket_creator = guild.get_member(ticket_creator)
        embed = discord.Embed(
            title=f"{emoji_hanzo} Hanzo | Ticket Closed {emoji_hanzo}",
            description=(
                    f"Thank you for using our ticketing system. This ticket is now closed.\n\n"
                    f"**Opened By**: {ticket_creator.mention}\n"
                    f"**Closed By**: {self.author.mention}\n\n"
            ),
            color=default_color
        )
        transcript_info = discord.Embed(
            title=f"{emoji_hanzo} Hanzo | Ticket Closed {emoji_hanzo}",
            description=(
                    f"This ticket is now closed, signifying the conclusion of its journey.\n\n"
                    f"***Ticket Opened By***: {ticket_creator.mention}\n"
                    f"***Ticket Name***: {self.channel.name}\n"
                    f"***Closed By***: {self.author.mention}\n\n"
                    f"Thanks for your communication in this ticket. If you have more questions or need further help, reach out to us again. Appreciate you choosing our support services!"
                ),
            color=default_color
        )
        await self.reply(embed=embed)
        try:
                await ticket_creator.send(embed=transcript_info, file=transcript_file, view=StaffRating(self.bot, self.author.id))
        except:
            transcript_info.add_field(name="Error", value="Can't send transcript to user. Error: DM's privacy.", inline=True)
        transcript_info_log2 = discord.Embed(
            title=f"{emoji_hanzo} Hanzo | Ticket Closed {emoji_hanzo}",
            description=(
                f"This ticket is now closed, signifying the conclusion of its journey.\n\n"
                f"**Ticket Opened By**: {ticket_creator.mention}\n"
                f"**Ticket Name**: {self.channel.name}\n"
                f"**Closed By**: {self.author.mention}\n\n"
            ),
            color=default_color
        )
        await channel.send(embed=transcript_info_log2, file=transcript_file2)
        await asyncio.sleep(3)
        await self.channel.delete(reason="Ticket deleted.")
    conn.close()

@bot.hybrid_command(name="dbremove", description="remove an user from ticket database")
async def dbremove(ctx: commands.Context, user: discord.User): 
    if ctx.author.bot:
        return
    
    user_id = user.id
    with sqlite3.connect('user.db') as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM ticket WHERE discord_id=?", (user_id,))
        conn.commit()
        await ctx.send(f"Successfully deleted <@{user_id}>'s ticket from database.", ephemeral=True)
    conn.close()

@bot.hybrid_command(name="ticket", description="Send ticket panel")
@commands.has_role(owner_role_id)
async def ticket(self):
        embed = discord.Embed(
            title=f"{emoji_hanzo} **Ticket Panel | Hanzo** {emoji_hanzo}",
            description=f"{emoji_info} **__How Do I Purchase?__**\n"
            f"Simply press the button below and choose the option that fits your needs!\n\n"
            f"{emoji_key} **__Instant Delivery__**\n"
            f"If you have Card or Crypto feel free to purchase directly from our website\n\n"
            f"{emoji_website} **__Website:__**\n"
            f"https://hanzo.cheating.store/\n\n"
            f"{emoji_money2} **__Payment Methods Accepted__**\n"
            f"{emoji_paypal} Paypal\n{emoji_cashapp} CashApp\n{emoji_venmo} Venmo\n{emoji_card} Card\n{emoji_crypto} Crypto (BTC, LTC, ETH)\n{emoji_binance} Binance Giftcards",
            color=default_color,
        )
        embed.set_image(url="https://media.discordapp.net/attachments/1126129988828147794/1195797810990293123/support.png?ex=65b54c7e&is=65a2d77e&hm=f27caee277f5e11f050b79a48dec1823576f27bd006f57a44e6b27abbd6ba1ed&format=webp&quality=lossless&width=1196&height=676&")
        await self.send(embed=embed, view=TicketPanelClass(self.bot))
        await self.reply("Ticket panel sent.", ephemeral=True)

@bot.hybrid_command(name="ping", description="Ping Pong!")
@commands.has_role(staff_team_id)
async def ping(ctx: commands.Context):
    await ctx.reply("Pong!")

@bot.hybrid_command(name="assign", description="Send ticket assign")
@commands.has_role(owner_role_id)
async def assign(self):
        embed = discord.Embed(
            title=f"{emoji_hanzo} **Ticket Assign | Hanzo** {emoji_hanzo}",
            description=f"*press the button below to be assigned to a ticket.*\n",
            color=default_color,
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/1197617187335180288/1198283409500422296/image.png?ex=65be5763&is=65abe263&hm=3a52be36b2a373b05cfec8b60c1e4063eb1c90dad0bd0c2970086e16b9f21c0f&")
        await self.send(embed=embed, view=AssignButton(self.bot))
        await self.reply("Ticket assign sent.", ephemeral=True)

import os
token = os.getenv("TOKEN")
print(f"TOKEN = {token}")  # Debug print to verify it's loading


