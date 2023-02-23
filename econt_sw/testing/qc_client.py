

import socket
import os, time, datetime
# from tqdm import tqdm
import sqlite3
from sqlite3_database import create_database, add_many_column, show_all_plan
import os
import paramiko
import warnings
from cryptography.utils import CryptographyDeprecationWarning
# for chip in range(100):
# chip = 9999999
import argparse
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-c', '--chip',     default=-999,    type=int, help='Number of chip.')

args = parser.parse_args()

chip = args.chip

start_time = time.time()
# IP = "192.168.1.48"
IP = "127.0.0.1"
PORT = 9999
# SIZE = 1024
SIZE = 1024
FORMAT = "utf-8"
CLIENT_FOLDER = "data"

# chip = 4
folder_name = f"chip_{chip}"
max_with_thresold, second_max_width_thresold, max_IO_delay_scan_width_thresold, second_max_IO_delay_scan_width_thresold = 3, 2, 13, 12
#  Socket to talk to server
print("Connecting to  server ")
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((IP, PORT))

test_ended = False

print(f"Sending request to server")
client.send(bytes(f"start|{chip}|{max_with_thresold}|{second_max_width_thresold}|{max_IO_delay_scan_width_thresold}|{second_max_IO_delay_scan_width_thresold}",FORMAT))
print(f"start request  sent to server")
# time.sleep(150)
now = datetime.datetime.now()
datetime_now = now.strftime("%Y-%m-%d_%H:%M:%S")

#  Get the reply from server
message2 = client.recv(SIZE).decode()
data = message2.split('|')
if os.path.exists("Econt_database.db") == False:
    create_database()

d0 = chip
d1 = datetime_now
d2 = data[0]
d3 = data[1]
d4 = data[2]
d5 = data[3]
d6 = data[4]
d7 = data[5]
d8 = max_with_thresold
d9 = second_max_width_thresold
d10 = max_IO_delay_scan_width_thresold
d11 = second_max_IO_delay_scan_width_thresold
# files = data[6]
test_ended = data[6]
print("Test completed ---->", test_ended)
stuff=[(d0, d1, d2, d3, d4, d5, d6, d7, d8, d9, d10, d11, test_ended)]
add_many_column(stuff)
# add_many_column([data])
show_all_plan()
test_end_time = time.time()

# print(""" Copying files from server """)
#
# """ Creating the folder """
#
# folder_path = os.path.join(CLIENT_FOLDER, folder_name)
# if not os.path.exists(folder_path):
#     os.makedirs(folder_path)
#
#
#
#
# files = [ f"best_phase_scan_seting_chip_{chip}.txt",
# f"error_counts_chip_{chip}.csv",
# f"from_io_delayscanchip_{chip}.csv",
# f"good_capSelected_values_chip_{chip}.txt",
# f"io_delay_width_comparion_chip_{chip}.txt",
# f"logFile_chip_{chip}.log",
# f"phase_width_comparion_chip_{chip}.txt",
# f"pll_capSelect_scanchip_{chip}.csv",
# f"power_voltage_current_chip_{chip}.txt",
# f"prbs_counters_scan_0.05schip_{chip}.csv",
# f"rw_pair_one_comparion_chip_{chip}.txt",
# f"rw_pair_zero_comparion_chip_{chip}.txt",
# f"trackmode1_phaseSelectchip_{chip}.csv",
# f"trackmode2_phaseSelectchip_{chip}.csv",
# f"trackmode3_phaseSelectchip_{chip}.csv",
# f"width_of_io_scan_seting_chip_{chip}.txt",
# f"width_of_phase_scan_seting_chip_{chip}.txt"]
#
# warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
# ssh = paramiko.SSHClient()
# ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
# ssh.connect(hostname= IP, username='HGCAL_dev', password='daq5HGCAL!', port=22)
# sftp_client = ssh.open_sftp()
# for file_name in files:
#     try:
#         sftp_client.get(f'/home/HGCAL_dev/bbbam/econt_sw/econt_sw/data/{file_name}',f'{folder_path}/{file_name}')
#     except FileNotFoundError:
#         print("NO SUCH FILE", file_name)
#         os.system(f'rm  {folder_path}/{file_name}')
# sftp_client.close()
# ssh.close()
#
#
#
#
#
# total_end_time = time.time()
test_time_taken = test_end_time - start_time
# total_time_taken = total_end_time - start_time
#
print("test time taken----->  ", test_time_taken)
# print("Total time taken------>  ", total_time_taken)
# time.sleep(1)
