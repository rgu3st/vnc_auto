import subprocess
import time
import argparse
import socket
import netifaces

BROADCAST_INTERVAL =  6  # In seconds
SUBNET = '192.168.0'

def arg_init():
	parser = argparse.ArgumentParser()
	group = parser.add_mutually_exclusive_group()
	group.add_argument("-s", help="Use this for the computer sharing its screen.", action="store_true")
	group.add_argument("-c", help="Use this to view all server  screens.", action="store_true")
	args = parser.parse_args()
	return args

class comms:
	def __init__(self, s_c_type):
		# ip_udp_identifier = b"*automagic*"
		self.UDP_PORT = 41414
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


	def send_server_info(self, info:str):
		''' Server-side to broadcast its IP. '''
		print(f"Broadcasting my  server info on {SUBNET}.255:{self.UDP_PORT}...")
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		broadcast_ip = SUBNET + ".255"
		self.sock.sendto(info.encode('utf8'), (broadcast_ip, self.UDP_PORT))  				


	def client_listen_for_info(self):
		'''Client-side'''
		print(f"Waiting for a vnc server on {SUBNET}.255:{self.UDP_PORT}...")
		self.sock.bind(('192.168.0.255', self.UDP_PORT))  # The 'broadcast' ip should be sub.net.addr.255.
		data, addr = self.sock.recvfrom(1024)  # I'm pretty sure this is blocking: which I want here...
		print(f"Got server info: {data.decode('utf8')} from {addr}")	
		return data.decode('utf8')


class client:
	def __init__(self):
		self.server_infos = []	

	def start(self):

		com = comms("c")  # Too hackey: TODO: something better!
		server_info = com.client_listen_for_info()
		if server_info is None:
			print("Error receiving server info.")
			return None
		if server_info not in self.server_infos:
			self.server_infos.append(server_info)
		server_ip = server_info.split()[0]
		vnc_port = server_info.split()[1]
		vnc_viewer_command = f"vncviewer {server_ip}::{vnc_port}"
		# print(f"vncviewer command: {vnc_viewer_command}")
		subprocess.run(client.vnc_viewer_command.split())

class server:
	def __init__(self):
		self.ip_address = self.get_server_ip()
		self.is_running = False
		self.com = comms('s')  # TODO: decide if this can be static

	vnc_start_command = "x11vnc -display :0 -ncache 10 -noxdamage -viewonly -shared -many -bg"
	vnc_stop_command = "killall x11vnc"
	

	def get_server_ip(self, ip_match="192.168."):
		ip_list = []
		ip = "NotFound"  # Try to make it stoopud obvious if not found. 
		for interface in netifaces.interfaces():  # For each interface
			if netifaces.AF_INET in netifaces.ifaddresses(interface):  # If there's an AF_INET address for the interface
				for link in netifaces.ifaddresses(interface)[netifaces.AF_INET]:  
					if ip_match in link['addr']:  # If the link matches, awesome!
						ip = link['addr']
						# print(f"Found my ip I care about: {ip}!")	
		return ip


	def broadcast_server_info(self):
		info = self.ip_address
		info += " 5900"  # TODO: use the current VNC port, it MAY be 5901, 5902, etc. if multiple x11vnc runs.
		self.com.send_server_info(info)	
		print(f"Sent my server info: {info}")  # Should I add a log-level?


	def stop(self):
		subprocess.run(server.vnc_stop_command.split())
	

	def start(self):
		is_running = True
		subprocess.run(server.vnc_start_command.split())  # TODO: uncomment when ready to actually run VNC!
		while is_running:
			self.broadcast_server_info()
			time.sleep(BROADCAST_INTERVAL)


def main(args):
	if (args.s and args.c) or not (args.s or args.c):
		print("You have to select either -s or -c!")
		return
	if args.s:
		serv = server()
		serv.start()
		quit_input = input("\nType 'q' then Return/Enter to stop.\n")
		if quit_input == 'q':
			server.stop()
	elif args.c:
		clie = client()
		clie.start()	


if __name__ == "__main__":
	args = arg_init()
	main(args)

