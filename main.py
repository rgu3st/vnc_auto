import subprocess
import time
import argparse
import socket
import netifaces
import threading

BROADCAST_INTERVAL =  6  # How often the server broadcasts it's information, in seconds.
SUBNET = '192.168.0'  # ONLY uses the first three octets: assuming subnet mask is 255.255.255.0


''' My arguments for UDP:
	1 - It's a single packet broadcast per server per interval instead of the min 3 required for TCP
	2 - The server goes through minimal effort. It just wakes up once each interval, sends a single packet, and goes back to sleep.
	3 - If one 'broadcast' is missed, the client has another chance in a few seconds and once seen, the vnc connection IS via TCP.
        4 - I see this like non-real-time updates from a game server: it's one to many and it's not critical that each message get received. 
'''


def arg_init():
	parser = argparse.ArgumentParser()
	group = parser.add_mutually_exclusive_group()
	group.add_argument("-s", help="Use this for the computer sharing its screen.", action="store_true")
	group.add_argument("-c", help="Use this to view all server  screens.", action="store_true")
	args = parser.parse_args()
	return args


class comms:
	''' Manages server/client comms. Tries to avoid any duplicate code... '''
	def __init__(self, s_c_type):
		# ip_udp_identifier = b"*automagic*"  # TODO: Add an identifier in case anything else also uses port 41414?
		self.UDP_PORT = 41414
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.broadcast_ip = SUBNET + ".255"  # A little hacky...


	def send_server_info(self, info:str):
		''' Server-side to broadcast its IP. '''
		print(f"Broadcasting my  server info on {SUBNET}.255:{self.UDP_PORT}...")
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.sock.sendto(info.encode('utf8'), (self.broadcast_ip, self.UDP_PORT))  				


	def client_bind(self):
		print(f"Waiting for a vnc server on {SUBNET}.255:{self.UDP_PORT}...")
		broadcast_ip = SUBNET + ".255"
		self.sock.bind((self.broadcast_ip, self.UDP_PORT))  # The 'broadcast' ip should be sub.net.addr.255.


	def client_listen_for_info(self):
		'''Client-side'''
		data, addr = self.sock.recvfrom(1024)  # I'm pretty sure this is blocking: which I want.
		print(f"Got server info: {data.decode('utf8')} from {addr}")	
		return data.decode('utf8')


class client:
	'''Gets each server's info and spawns a vncviewer in its own thread for each. '''
	def __init__(self):
		self.server_infos = []	
		self.com = comms("c")  # Too hackey? TODO: Consider something better?
		self.com.client_bind()
		self.server_infos_lock = threading.Lock()


	def run_main_loop(self):
		while(True):
			server_info = self.com.client_listen_for_info()
			if server_info is None:
				print("Error receiving server info.")
				return None
			if server_info not in self.server_infos:
				# I *think* I need this since I'm spinning off the vncviewer stuff on a seperate thread that also touches this list
				self.server_infos_lock.aquire()
				self.server_infos.append(server_info)
				self.server_infos_lock.release()
			else:
				#print("Already connected. Just continue and see what else comes in.")
				continue
			args = [server_info]
			client_thread = threading.Thread(target=self.vnc_viewer_thread_start, args=args)	
			client_thread.start()


	def vnc_viewer_thread_start(self, server_info)->None:
		print(f"Starting new subprocess thread from server_info: {server_info}")
		server_ip = server_info.split()[0]
		vnc_port = server_info.split()[1]
		vnc_viewer_command = f"vncviewer {server_ip}::{vnc_port}"
		completed_process = subprocess.run(vnc_viewer_command.split())
		# Remove this server from the list if vncviewer closes, so we can re-connect automagically still. 
		# TODO: Ask if this is this a good idea?
		# Lock in case two threads end at the same time.
		self.server_infos_lock.aquire()
		self.server_infos = [x for x in self.server_infos if x != server_info]	
		self.server_infos_lock.release()


class server:
	'''Starts one vnc server and continually broadcasts the information for connecting to its server. '''
	vnc_start_command = "x11vnc -display :0 -ncache 10 -noxdamage -viewonly -shared -many -bg"
	vnc_stop_command = "killall x11vnc"  # This could be too blunt: will end ALL x11vnc processes on the workstation.


	def __init__(self):
		self.ip_address = self.get_server_ip()
		self.is_running = False
		self.com = comms('s')  
		self.is_running = False
		self.output_filename = "x11vnc_output.log"

	def get_server_ip(self, ip_match="192.168.")->str:
		ip_list = []
		ip = None  
		for interface in netifaces.interfaces():  # For each interface
			if netifaces.AF_INET in netifaces.ifaddresses(interface):  # If there's an AF_INET address for the interface
				for link in netifaces.ifaddresses(interface)[netifaces.AF_INET]:  
					if ip_match in link['addr']:  # If the link matches, awesome!
						ip = link['addr']
		return ip


	def broadcast_server_info(self):
		if self.ip_address is None:
			print("Error getting server IP.")
			return
		info = self.ip_address
		info += " 5900"  # TODO: use the current VNC port? It MAY be 5901, 5902, etc. if multiple x11vnc desktops, right?
		self.com.send_server_info(info)	
		print(f"Sent my server info: {info}")  # Should I add a log-level?


	def stop(self):
		subprocess.run(server.vnc_stop_command.split())
	

	def run_main_loop(self):
		self.is_running = True
		with open(self.output_filename, 'w') as f:
			f.write('')  # Clear the output file before all the other appends.
		loop_output_file = open(self.output_filename, 'a')
		subprocess.run(server.vnc_start_command.split(), stdout=loop_output_file, stderr=loop_output_file) 
		# Fun fact: since this is run in the main thread, as soon as we get here, the display number and port are in the last two lines of the file.
		while self.is_running:
			self.broadcast_server_info()
			time.sleep(BROADCAST_INTERVAL)
		loop_output_file.close()

def main(args):
	if (args.s and args.c) or not (args.s or args.c):
		print("You have to select either -s or -c!")
		return
	if args.s:
		serv = server()
		server_main_loop_thread = threading.Thread(target=serv.run_main_loop)
		server_main_loop_thread.start()
		quit_input = input("\nType 'q' then Return/Enter at any time to stop.\n\n")
		if quit_input == 'q' or 'quit' or 'exit' or 'stop':
			serv.is_running = False
			serv.stop()
	elif args.c:
		print("Just ctrl+c to quit for now...")  # TODO: gracefully close?
		clie = client()
		clie.run_main_loop()	


if __name__ == "__main__":
	args = arg_init()
	main(args)

