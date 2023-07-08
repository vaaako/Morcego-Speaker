import discord
import gtts
import os, io, time
#import functools
import asyncio
#import threading

from discord.ext import commands
#from dotenv import load_dotenv

from keep_alive import keep_alive


class PlayTTS():

	def __init__(self):
		self.track_list = []  # { "file_name": "tmp.wav", "audio_souce": source }
		self.track_list_all_items = 0
		self.track_list_current_item = 0
		self.current_track_time = 0

		self.vc = None
		self.send_playing = True
		self.is_ctx = False
		self.method = None
		self.client = None

	async def _send_message(self, message, ephemeral=True, send_channel=False):
		if self.is_ctx:
			if send_channel:
				await self.method.channel.send(message)
			else:
				#print("aqui")
				await self.method.respond(message, ephemeral=ephemeral)
		else:
			await self.method.channel.send(message)

	def _play_callback(self,
	                   error):  # This is unnecessary, but i code it, so now IS!
		if error:
			print(error)
		os.remove(self.track_list[0]['file_name'])

		# Go to next speak, if have
		del self.track_list[0]

	def clear_old_files(self):
		# Remove files
		for file in os.listdir():
			if os.path.isfile(file) and file.split('.')[1] == 'wav':
				os.remove(file)
		

	def clear_track_list(self):
		self.track_list = []
		self.track_list_all_items = 0
		self.track_list_current_item = 0
		self.current_track_time = 0


	async def generate_tts(self, text, buffer=True, language='pt'):
		tts = gtts.gTTS(text, lang=language, slow=False)

		if buffer:
			buffer = io.BytesIO()  # Make buffer
			tts.write_to_fp(buffer)  # Write to buffer
			buffer.seek(0)
			audio_data = buffer.getvalue()
		else:
			audio_data = 'tmp' + str(time.time()).split('.')[0] + '.wav'
			tts.save(audio_data)  # In this case is not the data but yah
		return audio_data

	async def play_audio(self, speak_item=None):
		if not speak_item:
			speak_item = self.track_list[0]

		# Update track
		self.track_list_current_item += 1

		# callback_with_args = functools.partial(self._play_callback, file=self.track_list[0]) # Pre-fill the args of _play_callback
		if self.send_playing:  # Send message that's playing
			await self._send_message(f"*Speaking:* {speak_item['text']}")
			if len(self.track_list
			       ) > 1:  # Just send track if there is more of th- aaah you got it
				await self._send_message(
				 f"*Track*: {self.track_list_current_item}/{self.track_list_all_items}",
				 send_channel=True)

		self.vc.play(speak_item['audio_source'],
		             after=self._play_callback)  # Pass callback with args pre-filled

		# Wait until stop playing and play next item
		while self.vc.is_playing():
			await asyncio.sleep(1)
			self.current_track_time += 1

		if len(self.track_list) > 0:
			self.current_track_time = 0
			await self.play_audio()

		else:
			self.track_list_all_items = 0
			self.track_list_current_item = 0

	async def do_speak(self, text, method=None, client=None, send_playing=True, add_track=True):
		self.method = method
		self.send_playing = send_playing

		self.is_ctx = 'context' in str(self.method)
		self.client = client
		if not self.is_ctx and not client:
			raise TypeError("Message method must have a client")


		
		voice_channel = self.method.author.voice.channel
		self.vc = self.method.voice_client if self.is_ctx else discord.utils.get(
		self.client.voice_clients, guild=method.guild)  # If client is in voice channel

		if not voice_channel:
			return await self._send_message(
			 "Você não está em nenhum canal de voz! Idiota")
		elif not self.vc:
			self.clear_track_list()
			self.vc = await voice_channel.connect()
		# vc.stop()
		await self.method.guild.change_voice_state(channel=voice_channel,
		                                           self_mute=False,
		                                           self_deaf=True)

		# Generate TTS Buffer/File
		tts_file = await self.generate_tts(text, buffer=False)
		audio_source = discord.FFmpegPCMAudio(
		 tts_file, options='-filter:a "atempo=1.5"')  # atempo = speed

		# Play it
		# self.track_list.append(tts_file)
		if add_track:
			self.track_list.append({
			 "file_name": tts_file,
			 "audio_source": audio_source,
			 "text": text
			})
			self.track_list_all_items += 1
			# print(self.track_list)

		# if self.vc.is_playing(): # If is playing warn
		if len(self.track_list) > 1:  # I think this can avoid some bugs
			return await self._send_message(
			 f"Já vou falar sua mensagem, guenta ai! \n*Playing now:* {self.track_list_current_item}/{self.track_list_all_items}"
			)  #00:{str(self.current_track_time).zfill(2)} - 00:{str(int(duration)).zfill(2)}")
		await self.play_audio()


class Client(commands.AutoShardedBot):

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.play_tts = PlayTTS()
		self.message = None

	async def on_ready(self):
		print(f'*happy bat noises* {client.user}!')

		discord.opus.load_opus("./libopus.so.0.8.0")
		if not discord.opus.is_loaded():
			raise RunTimeError('Opus failed to load')

		await client.change_presence(activity=discord.Game(name="Morcega Falante 🦇"))

	async def _get_input(self, message):
		to_play = input('] ')
		if to_play == 'exit':
			return
		self.play_tts.do_speak(to_play,
		                               message,
		                               client=client,
		                               send_playing=False)
		await self._get_input(message)

	async def on_message(self, message):
		if message.author.bot:  # do not reply bot
			return

		command = message.content
		if command.lower().startswith('speak') and len(command.split()) > 1:
			# ' '.join(command.split()[1:])
			await self.play_tts.do_speak(' '.join(command.split()[1:]),
			                               message,
			                               client=client,
			                               send_playing=False)
		elif command.lower() == 'input_mode':
			await self._get_input(message)

	async def on_voice_state_update(self, member, before, after):
		voice_channel = before.channel or after.channel

		# Verifica se o bot está conectado ao mesmo canal de voz
		voice_client = discord.utils.get(client.voice_clients, guild=member.guild)
		if voice_client and voice_channel == voice_client.channel:
			# Desconecta o bot quando não houver mais nenhum usuário além do próprio bot
			if len(voice_channel.members) == 1 and voice_channel.members[0] == client.user:
				await voice_client.disconnect()


# Init client
client = Client(intents=discord.Intents.all(),
                # help_command=None,
                # command_prefix='speak'
                )


# bot = commands.Bot(command_prefix='\'', help_command=commands.DefaultHelpCommand())
#load_dotenv(dotenv_path='.env')  # Load .env
@client.slash_command(name="speak", description="TTS na sua mensagem")
async def speak(ctx, text: discord.Option(str, "O que vou falar?")):
	if len(text) > 250:
		return await ctx.respond("Uma mensagem menor por favor!")
	await client.play_tts.do_speak(text, ctx)


@client.slash_command(name="reset",
                      description="Reset caso algo de errado aconteça")
async def reset(ctx):
	client.play_tts.clear_track_list()
	return await ctx.respond("Reset feito!", ephemeral=True)


@client.slash_command(name="leave", description="Sair do canal")
async def leave(ctx):
	client.play_tts.clear_track_list()

	
	if not ctx.author.voice:
		return await ctx.respond("Eu não estou em um canal de voz! Dumb", ephemeral=True)
	await ctx.voice_client.disconnect()
	
	return await ctx.respond("Saido", ephemeral=True)



@client.slash_command(name="clear", description="Clear old audio files")
async def clear(ctx):
	client.play_tts.clear_old_files()

	return await ctx.respond("Arquivos de áudio antigos removidos!", ephemeral=True)



if __name__ == '__main__':
	keep_alive()
	client.run(os.getenv('TOKEN'))  # Importing TOKEN from .env
"""
Change Nickname
Manage Nickname
Read Messages/View Channels
Send Messsages
Send Messages in Threads
Send TTS Messages
Manage Messages
Embed Links
Attach Files
Read Message History
Use External Emojis
Add Reactions
Use Slash Commands
Connect
Speak
Video
Mute Members
Deafen Members
Move Members
Use Voice Activity
Priority Speaker
Request To Speak
Use Embedded Activities
Use Soundboard
Use External Sounds

40413762551616
"""
