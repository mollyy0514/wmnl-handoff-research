######xml_mi.py#########
#==============instructions==============
######This file requires the txt file which is generated from offline_analysis.py and the mi2log file
######The rows shows the information of each diag mode packets (dm_log_packet) from Mobile Insight 
######The columns are indicators about whether a packet has the type of the message

from bs4 import BeautifulSoup
import sys
import os
from pprint import pprint
import argparse
from pytictoc import TicToc

# --------------------- Arguments ---------------------
parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", type=str,
                    help="input filepath")
parser.add_argument("-D", "--indir", type=str,
                    help="input dirctory path")
parser.add_argument("-O", "--outdir", type=str,
                    help="output dirctory path")
args = parser.parse_args()

# ********************* User Settings *********************
database = "/home/wmnlab/D/database/"
date = "2022-10-11"
Exp_Name = {  # experiment_name:(number_of_experiment_rounds, list_of_experiment_round)
              # If the list is empty, it will list all directories in the current directory by default.
              # If the number of experiment times != the length of existing directories of list, it would trigger warning and skip the directory.
    "_Bandlock_Udp":(4, []),
    "_Bandlock_Tcp":(4, []),
}
devices = [
    "sm03",
    "sm04",
    "sm05", 
    "sm06",
    "sm07",
    "sm08",
]
db_path = os.path.join(database, date)
# *********************************************************

# --------------------- Util Functions ---------------------
# def xml_to_csv_rrc(fin, fout):
# def xml_to_csv_phy(fin, fout):
def xml_to_csv(fin, fout):
    fp_in = open(fin, encoding='utf-8')
    fp_out = open(fout, 'w')
    ### Writing the column names...
    fp_out.write(",".join(["time", "type_id",
        "PCI",
        "UL_DL",
        "measurementReport",
        "rrcConnectionReconfiguration",
        "rrcConnectionReestablishmentRequest",
        "rrcConnectionReestablishment",
        "rrcConnectionReestablishmentReject",
        "rrcConnectionSetup",
        "rrcConnectionSetupComplete",
        "lte-rrc.nr_SecondaryCellGroupConfig_r15",
        "rrcConnectionReconfigurationComplete",   
        "scgFailureInformationNR-r15",
        "nr-rrc.t304",
        "lte-rrc.t304",
        "nr-Config-r15: release (0)",
        "nr-Config-r15: setup (1)",
        "dualConnectivityPHR: setup (1)",
        "dualConnectivityPHR: release (0)",
        "nr-rrc.RRCReconfiguration_element",
        "nr-rrc.eventA",
        "nr-rrc.spCellConfig_element",
        "lte-rrc.targetPhysCellId",
        "nr_pci"])+'\n')

    l = fp_in.readline()
    ### For each dm_log_packet, we will check that whether strings in type_list are shown in it.
    ### If yes, type_code will record what types in type_list are shown in the packet.
    type_list = [
        "\"measurementReport\"",
        "\"rrcConnectionReconfiguration\"",
        "\"rrcConnectionReestablishmentRequest\"",
        "\"rrcConnectionReestablishment\"",
        "\"rrcConnectionReestablishmentReject\"",
        "\"rrcConnectionSetup\"",
        "\"rrcConnectionSetupComplete\"",
        "\"lte-rrc.nr_SecondaryCellGroupConfig_r15\"",
        "\"rrcConnectionReconfigurationComplete\"",
        "\"scgFailureInformationNR-r15\"",
        "\"nr-rrc.t304\"",
        "\"lte-rrc.t304\"",
        "\"nr-Config-r15: release (0)\"",
        "\"nr-Config-r15: setup (1)\"",
        "\"dualConnectivityPHR: setup (1)\"",
        "\"dualConnectivityPHR: release (0)\"",
        "\"nr-rrc.RRCReconfiguration_element\"",
        "nr-rrc.eventA",
        "\"nr-rrc.spCellConfig_element\"",
        "\"lte-rrc.targetPhysCellId\""
    ]
    while l:
        type_code = ["0"] * len(type_list)
        
        if "pair key" in l and r"</dm_log_packet>" in l:  # If the packet just have one line (5G RRC OTA packet)
            soup = BeautifulSoup(l, 'html.parser')
            timestamp = soup.find(key="timestamp").get_text()
            type_id = soup.find(key="type_id").get_text()
            try:
                PCI = soup.find(key="Physical Cell ID").get_text()
            except:
                PCI = "-"
            fp_out.write(",".join([timestamp, type_id, PCI, "-"] + type_code)+'\n')
            
            l = fp_in.readline()
            continue
        
        elif "pair key" in l and r"</dm_log_packet>" not in l:  # If the packet has more than one line
            soup = BeautifulSoup(l, 'html.parser')
            timestamp = soup.find(key="timestamp").get_text()
            type_id = soup.find(key="type_id").get_text()
            try:
                PCI = soup.find(key="Physical Cell ID").get_text()
            except:
                PCI = "-"
            
            UL_DL = "-"
            nr_pci = "-"
            l = fp_in.readline()
            
            while l and r"</dm_log_packet>" not in l:
                
                if "UL-DCCH-Message" in l:
                    UL_DL = "UL"
                if "DL-DCCH-Message" in l:
                    UL_DL = "DL"
                    
                if "nr-rrc.physCellId" in l:
                    nr_pci = l.split("\"")[9]
                    #print(nr_pci)
                
                c = 0
                for type in type_list:
                    if type in l:
                        type_code[c] = "1"
                    c += 1
                l = fp_in.readline()
            fp_out.write(",".join([timestamp, type_id, PCI, UL_DL] + type_code + [nr_pci])+'\n')
        else:
            l = fp_in.readline()
    fp_in.close()
    fp_out.close()

def makedir(dirpath, mode=0):  # mode=1: show message, mode=0 hide message
    if os.path.isdir(dirpath):
        if mode:
            print("mkdir: cannot create directory '{}': directory has already existed.".format(dirpath))
        return
    ### recursively make directory
    _temp = []
    while not os.path.isdir(dirpath):
        _temp.append(dirpath)
        dirpath = os.path.dirname(dirpath)
    while _temp:
        dirpath = _temp.pop()
        print("mkdir", dirpath)
        os.mkdir(dirpath)


if __name__ == "__main__":
    t = TicToc()  # create instance of class
    t.tic()  # Start timer
    # --------------------- (1) convert only one file (set arguments) ---------------------
    if args.input:
        fin = args.input
        ### Check the input filename format, and whether users specify output filename.
        if not fin.endswith(".txt"):
            print("Input: '{}' does not endswith 'txt', the program is terminated.".format(fin))
            sys.exit()
        fout = "{}.csv".format(fin[:-4])
        ### decoding ...
        print(">>>>> convert from '{}' into '{}'...".format(fin, fout))
        xml_to_csv(fin, fout)
        print()
        t.toc()
        sys.exit()

    # --------------------- (2) convert files in one directory (set arguments) ---------------------
    if args.indir:
        err_handles = []
        input_path = args.indir
        ### Check if the input directory exists
        if not os.path.isdir(input_path):
            print("FileExistsError: directory '{}' does not exists, the program is terminated.".format(input_path))
            sys.exit()
        output_path = args.outdir if args.outdir else input_path
        filenames = os.listdir(input_path)
        pprint(filenames)
        for filename in filenames:
            # if not filename.endswith(".pcap"):
            if not filename.startswith("diag_log") or not filename.endswith(".txt"):
                continue
            fin = os.path.join(input_path, filename)
            fout = os.path.join(output_path, "{}.csv".format(filename[:-4]))
            makedir(output_path)
            ### decoding ...
            print(">>>>> convert from '{}' into '{}'...".format(fin, fout))
            xml_to_csv(fin, fout)
        print()
        t.toc()
        sys.exit()

    # --------------------- (3) decode a batch of files (User Settings) ---------------------
    ### iteratively decode every diag_log.txt file
    for _exp, (_times, _rounds) in Exp_Name.items():
        ### Check if the directories exist
        exp_path = os.path.join(db_path, _exp)
        print(exp_path)
        if _rounds:
            exp_dirs = [os.path.join(exp_path, item) for item in _rounds]
        else:
            exp_dirs = [os.path.join(exp_path, item) for item in sorted(os.listdir(exp_path))]
        exp_dirs = [item for item in exp_dirs if os.path.isdir(item)]
        print(_times)
        pprint(exp_dirs)
        if len(exp_dirs) != _times:
            print("************************************************************************************************")
            print("Warning: the number of directories does not match your specific number of experiment times.")
            print("************************************************************************************************")
            print()
            continue
        print()

        ### Check if a diag_log.txt file exists, and then run decoding
        print(_exp)
        for exp_dir in exp_dirs:
            print(exp_dir)
            for dev in devices:
                dir = os.path.join(exp_dir, dev, "data")
                filenames = os.listdir(dir)
                for filename in filenames:
                    # if "diag_log" not in filename or not filename.endswith(".mi2log"):
                    if not filename.startswith("diag_log") or not filename.endswith(".txt"):
                        continue
                    # print(filename)
                    fin = os.path.join(dir, filename)
                    fout = os.path.join(dir, "{}.csv".format(filename[:-4]))
                    # makedir(os.path.join(dir, "..", "data"))
                    ### decoding ...
                    print(">>>>> decode from '{}' into '{}'...".format(fin, fout))
                    xml_to_csv(fin, fout)
            print()
    t.toc()
