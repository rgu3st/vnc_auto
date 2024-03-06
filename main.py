import subprocess
import argparse
import socket
import netifaces



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
		UDP_PORT = 41414
		UDP_IP = "127.0.0.1"
		if s_c_type == "s":  # Hacky...
			UDP_IP = "192.168.0.3"
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		# self.sock.bind((UDP_IP, UDP_PORT))


	def send_server_ip(self):
		''' Server-side to broadcast its IP. '''
		# TODO: set this up to have a reference to THIS server if 
		message = self.server.ip_address
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.sock.sendto(message, ('255.255.255.255', UPD_PORT)
				

	def listen_for_ip(self):
		'''Client-side'''
		self.sock.bind(('192.168.0.255', UDP_PORT))  # The 'broadcast' ip should be sub.net.addr.255.
		data, addr = sock.recvfrom(1024)  # I'm pretty sure this is blocking: which I want here...
		print("Connecting to server at ip: {}")	


class client:
	def __init__(self):
		self.server_ips = []	

	serverip = "192.168.0.3"
	port = 5900
	vnc_viewer_command = f"vncviewer {serverip}::{port}"

	def start():
		subprocess.run(client.vnc_viewer_command.split())

class server:
	def __init__(self):
		self.ip_address = self.get_server_ip()

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
						print(f"Found my ip I care about: {ip}!")	
		return ip

	def stop():
		subprocess.run(server.vnc_stop_command.split())
	
	def start():
		subprocess.run(server.vnc_start_command.split())


def main(args):
	com = comms("s")
	com.send_server_ip()

	serv = server()
	# serv.get_server_ip()

	if (args.s and args.c) or not (args.s or args.c):
		print("You have to select either -s or -c!")
		return
	if args.s:
		print(f'Starting sever stuffs with command:\n {server.vnc_start_command}')
		server.start()
		quit_input = input("Type 'q' then Return/Enter to stop.\n")
		if quit_input == 'q':
			server.stop()
	elif args.c:
		print(f"Starting to view server {client.serverip} on port {client.port}.")
		com.get_server_ip()
		client.start()	


if __name__ == "__main__":
	args = arg_init()
	main(args)

