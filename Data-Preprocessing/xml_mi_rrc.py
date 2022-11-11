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
date = "2022-10-20"
db_path = os.path.join(database, date)
Exp_Name = {  # experiment_name:(number_of_experiment_rounds, list_of_experiment_round)
                # If the list is empty, it will list all directories in the current directory by default.
                # If the number of experiment times != the length of existing directories of list, it would trigger warning and skip the directory.
    # "_Bandlock_Udp":(1, ["#01"]),
    # "_Bandlock_Udp":(5, ["#02", "#03", "#04", "#05", "#06"]),
    # "_Bandlock_Udp":(4, ["#01", "#02", "#03", "#04"]),
    # "_Bandlock_Udp":(6, []),
    # "_Bandlock_Udp":(4, []),
    # "_Bandlock_Tcp":(4, []),
    "_Udp_Stationary_Bandlock":(1, []), 
    "_Udp_Stationary_SameSetting":(1, []),
}
devices = sorted([
    # "sm03",
    "sm04",
    "sm05", 
    "sm06",
    "sm07",
    "sm08",
])
# *********************************************************

def get_text(l, NAME): ## Given l, return XXXX if NAME in l, else it will error, with format "NAME: XXXX".
    a = l.index('"' + NAME)
    k = len(NAME)+3
    b = l.index("\"", a+1)
    return l[a+k:b]

def passlines(num, f): ## Given num(int) and open file, read the file to next num line. 
    for i in range(num):
        l = f.readline()
    return l

def multi_output_write(type_code, c, type, l=None, sep='@'):
    if l is None:
        if type_code[c] == '0':
            type_code[c] = type
        else:
            type_code[c] = type_code[c] + sep +  type
    else:    
        if type_code[c] == '0':
            type_code[c] = get_text(l, type)
        else:
            type_code[c] = type_code[c] + sep +  get_text(l, type)

def find_next_str_and_write(type_code, f, L, c):
    l = f.readline()
    while l:
        for x in L:
            if x in l:
                multi_output_write(type_code, c, x, l)
                ans = get_text(l, x)
                return ans, l
        l = f.readline()
        
def get_meas_report_pairs(f, sep="&"): ## (MeasId & measObjectId & reportConfigId)
    l = f.readline()
    measId = get_text(l, "measId")
    l = f.readline()
    measObjectId = get_text(l, "measObjectId")
    l = f.readline()
    reportConfigId = get_text(l, "reportConfigId")
    return '('+measId+sep+measObjectId+sep+reportConfigId+')'

def get_event_paras(f, eventId, l):

    def lte_get_hys_and_ttt():
        l = passlines(4, f)
        hysteresis = get_text(l, "hysteresis")
        hysteresis = hysteresis.split(" ")[0]
        l = passlines(2, f)
        timeToTrigger = get_text(l, "timeToTrigger")
        timeToTrigger = timeToTrigger.split(" ")[0]
        return  hysteresis, timeToTrigger 
    
    def nr_get_hys_and_ttt():
        l = passlines(3, f)
        hysteresis = get_text(l, "hysteresis")
        hysteresis = hysteresis.split(" ")[0]
        l = passlines(2, f)
        timeToTrigger = get_text(l, "timeToTrigger")
        timeToTrigger = timeToTrigger.split(" ")[0]
        return  hysteresis, timeToTrigger 

    paras = {}
    if eventId == "eventA1 (0)" or eventId == "eventA2 (1)": ## A1 or A2
        if "\"lte-rrc.eventId\"" in l:
            l = passlines(4, f)
            threshold =  get_text(l, "threshold-RSRP")
            threshold = threshold.split(" ")[0]
            hysteresis, timeToTrigger = lte_get_hys_and_ttt()
            paras['thr'], paras['hys'], paras['ttt'] = threshold, hysteresis, timeToTrigger
        elif "\"nr-rrc.eventId\"" in l:
            l = passlines(4, f)
            threshold =  get_text(l, "rsrp")
            threshold = '[' + threshold.split(" ")[0] + ', ' + threshold.split(" ")[4] + ')'
            hysteresis, timeToTrigger = nr_get_hys_and_ttt()
            paras['thr'], paras['hys'], paras['ttt'] = threshold, hysteresis, timeToTrigger
    elif eventId == "eventA3 (2)": ## A3
        if "\"lte-rrc.eventId\"" in l:
            l = passlines(2, f)
            offset =  get_text(l, "a3-Offset")
            offset = offset.split(" ")[0]
            hysteresis, timeToTrigger = lte_get_hys_and_ttt()
            paras['off'], paras['hys'], paras['ttt'] = offset, hysteresis, timeToTrigger
        elif "\"nr-rrc.eventId\"" in l:
            l = passlines(4, f)
            offset = get_text(l, "rsrp")
            hysteresis, timeToTrigger = nr_get_hys_and_ttt()
            paras['off'], paras['hys'], paras['ttt'] = offset, hysteresis, timeToTrigger
    elif eventId == "eventA5 (4)": ## A5
        if "\"lte-rrc.eventId\"" in l:
            l = passlines(4, f)
            threshold1 =  get_text(l, "threshold-RSRP")
            threshold1 = threshold1.split(" ")[0]
            l = passlines(4, f)
            threshold2 =  get_text(l, "threshold-RSRP")
            threshold2 = threshold2.split(" ")[0]
            hysteresis, timeToTrigger = lte_get_hys_and_ttt()
            paras['thr1'], paras['thr2'], paras['hys'], paras['ttt'] = threshold1, threshold2, hysteresis, timeToTrigger
        elif "\"nr-rrc.eventId\"" in l:
            pass
    elif eventId == "eventA6-r10 (5)": ## A6
        if "\"lte-rrc.eventId\"" in l:
            l = passlines(2, f)
            offset =  get_text(l, "a6-Offset-r10")
            offset = offset.split(" ")[0]
            hysteresis, timeToTrigger = lte_get_hys_and_ttt()
            paras['off'], paras['hys'], paras['ttt'] = offset, hysteresis, timeToTrigger
        elif "\"nr-rrc.eventId\"" in l:
            pass
    elif eventId == "eventB1-NR-r15 (5)": ## interRAT B1
        if "\"lte-rrc.eventId\"" in l:
            l = passlines(4, f)
            offset =  get_text(l, "nr-RSRP-r15")
            offset = '[' + offset.split(" ")[0] + ', ' + offset.split(" ")[4] + ')'
            l = f.readline()
            hysteresis, timeToTrigger = lte_get_hys_and_ttt()
            paras['off'], paras['hys'], paras['ttt'] = offset, hysteresis, timeToTrigger
        elif "\"nr-rrc.eventId\"" in l:
            pass
    else:
        pass
    
    return str(paras).replace(',', '&')

def xml_to_csv_rrc(fin, fout):
    f = open(fin, encoding='utf-8')
    f2 = open(fout, 'w') # _rrc.csv
    # Writing the column names... If you want to add something, don't forget the comma at the end!!
    # -------------------------------------------------
    f2.write(",".join(["Timestamp", "type_id",
        "PCI",
        "UL_DL",
        "Freq",

        ## Measure report related
        "measurementReport",
        "measId",
        "MeasResultEUTRA",
        "physCellId",               ## LTE measured target PCI for MeasResultEUTRA 
        "MeasResultServFreqNR-r15", ## When lte and nr both HO, this will be emerged with MeasResultEUTRA.
        "pci-r15",
        "MeasResultNR",
        "physCellId",               ## NR measured target PCI for MeasResultNR
        "measResultServingCell",
        "physCellId",
        "MeasResultCellNR-r15",
        "pci-r15",                  ## NR measured target PCI for MeasResultCellNR-r15
        ###########################

        ## Configuration dissemination Related
        "MeasObjectToAddMod",
        "measObjectId", 
        "measObject",               ## measObjectEUTRA (0) OR measObjectNR-r15 (5)
        "carrierFreq",              ## For E-UTRA
        "carrierFreq-r15",          ## For E-UTRA
        "ssbFrequency",             ## For measObjectNR
        
        "ReportConfigToAddMod",
        "reportConfigId",
        "triggerType",              ## reportType for 5G OTA 
        "eventId",
        "parameter",                ## Most difficult part...
        
        "measIdToRemoveList",
        "MeasIdToAddMod",           ## (MeasId & measObjectId & reportConfigId)
        ###########################

        ## Basic reconfiguration
        "rrcConnectionReconfiguration",
        "rrcConnectionReconfigurationComplete",
        "RRCReconfiguration",
        "RRCReconfigurationComplete",
        ###########################

        ## LTE RLF related
        "rrcConnectionReestablishmentRequest",
        "physCellId",               ## Target PCI for rrcConnectionReestablishmentRequest.
        "reestablishmentCause",     ## ReestablishmentCause for rrcConnectionReestablishmentRequest.
        "rrcConnectionReestablishment",
        "rrcConnectionReestablishmentComplete",
        "rrcConnectionReestablishmentReject",
        ###########################

        ## Initial setup related
        "rrcConnectionSetup",
        "rrcConnectionSetupComplete",
        "securityModeCommand",
        "SecurityModeComplete",
        ###########################

        "rrcConnectionRelease",
        
        ## NSA mode SN setup and release 
        "nr-Config-r15: release (0)",
        "nr-Config-r15: setup (1)",
        "dualConnectivityPHR: release (0)",
        "dualConnectivityPHR: setup (1)",
        ###########################

        ## NSA mode SN RLF related
        "scgFailureInformationNR-r15",
        "failureType-r15",          ## Failure cause of scgfailure .
        ###########################

        ## LTE and NR ho related
        "lte_targetPhysCellId",     ## Handover target.
        "lte-rrc.t304",

        "nr_physCellId",            ## NR measured target PCI
        "nr-rrc.t304",
        ###########################
        

        ## SCell add and release 
        "sCellToReleaseList-r10",
        "SCellIndex-r10",
        "sCellToAddMod-r10",
        "SCellIndex-r10",
        "physCellId-r10",
        "dl-CarrierFreq-r10",
        ###########################

        ])+'\n')

    # For each dm_log_packet, we will check that whether strings in type_list are shown in it.
    # If yes, type_code will record what types in type_list are shown in the packet.
    # -------------------------------------------------
    type_list = [
        ## MeasurementReport Related 
        "\"measurementReport\"",
        "measId",
        "\"MeasResultEUTRA\"",
        "physCellId",
        "\"MeasResultServFreqNR-r15\"",
        "pci-r15",
        "\"MeasResultNR\"",
        "physCellId",
        "\"measResultServingCell\"",
        "physCellId",
        "\"MeasResultCellNR-r15\"",
        "pci-r15",
        ###########################

        ## Configuration dissemination Related
        "\"MeasObjectToAddMod\"",
        "measObjectId", 
        "measObject", 
        "carrierFreq", 
        "carrierFreq-r15",
        "ssbFrequency",

        "\"ReportConfigToAddMod\"",
        "reportConfigId",
        "triggerType",
        "eventId",
        "parameter",

        "measIdToRemoveList",
        "\"MeasIdToAddMod\"",
        ###########################


        ## Basic reconfiguration
        "\"rrcConnectionReconfiguration\"",
        "\"rrcConnectionReconfigurationComplete\"",
        "\"RRCReconfiguration\"",
        "\"RRCReconfigurationComplete\"",
        ###########################

        ## LTE RLF related 
        "\"rrcConnectionReestablishmentRequest\"",
        "physCellId", 
        "reestablishmentCause",
        "rrcConnectionReestablishment",
        "\"rrcConnectionReestablishmentComplete\"",
        "\"rrcConnectionReestablishmentReject\"",
        ###########################

        ## Initial Setup related
        "\"rrcConnectionSetup\"",
        "\"rrcConnectionSetupComplete\"",
        "\"securityModeCommand\"",
        "\"SecurityModeComplete\"",
        ###########################

        "\"rrcConnectionRelease\"",

        ## NSA mode SN setup and release 
        "\"nr-Config-r15: release (0)\"",
        "\"nr-Config-r15: setup (1)\"",
        "\"dualConnectivityPHR: release (0)\"",
        "\"dualConnectivityPHR: setup (1)\"",
        ###########################

        ## NSA mode SN RLF related
        "\"scgFailureInformationNR-r15\"",
        "failureType-r15",
        ###########################

        ## LTE and NR ho related
        "\"lte-rrc.targetPhysCellId\"",     
        "\"lte-rrc.t304\"",
        "\"nr-rrc.physCellId\"",
        "\"nr-rrc.t304\"",
        ###########################

        ## SCell add and release 
        "\"sCellToReleaseList-r10:",
        "SCellIndex-r10",
        "\"SCellToAddMod-r10\"",
        "sCellIndex-r10",
        "physCellId-r10",
        "dl-CarrierFreq-r10",
        ###########################

        ]

    l = f.readline()
            
    while l:
        if r"<dm_log_packet>" in l:
            type_code = ["0"] * len(type_list)
            soup = BeautifulSoup(l, 'html.parser')
            timestamp = soup.find(key="timestamp").get_text()
            type_id = soup.find(key="type_id").get_text()
            try:
                PCI = soup.find(key="Physical Cell ID").get_text()
                Freq = soup.find(key="Freq").get_text()
            except:
                PCI = "-"
                Freq = '-'

            if type_id != 'LTE_RRC_OTA_Packet' and type_id != '5G_NR_RRC_OTA_Packet': ## 只處理RRC
                while l and r"</dm_log_packet>" not in l:
                    l = f.readline()
                l = f.readline()
                continue
            # if r"</dm_log_packet>" in l: # 過濾不能parse只有一行的message
            #     l = f.readline()
            #     continue
            #     f2.write(",".join([timestamp, type_id, PCI, "-"] + type_code)+'\n')
            # print(222)

            else:
                UL_DL = '-'
                while l and r"</dm_log_packet>" not in l:
                        
                    if "UL-DCCH-Message" in l:
                        UL_DL = "UL"
                    elif "DL-DCCH-Message" in l:
                        UL_DL = "DL"

                    c = 0
                    next = 0 
                    for type in type_list:
                        if next != 0:
                            next -= 1
                            continue
    
                        if type in l and type == "\"measurementReport\"":
                            type_code[c] = "1"
                            c += 1
                            if "\"lte-rrc.measurementReport_element\"" in l:
                                l = passlines(10, f)
                                type_code[c] = get_text(l, "measId")
                            elif "\"nr-rrc.measurementReport_element\"" in l:
                                l = passlines(9, f)
                                try :
                                    type_code[c] = get_text(l, "measId")
                                except:
                                    type_code[c] = "none"
                            next = 1
                        elif type in l and type == "\"MeasResultEUTRA\"":
                            type_code[c] = "1"
                            c += 1
                            l = passlines(2, f)
                            multi_output_write(type_code, c, "physCellId", l)
                            next = 1
                        elif type in l and type == "\"MeasResultServFreqNR-r15\"":
                            type_code[c] = "1"
                            c += 1
                            l = passlines(8, f)
                            type_code[c] = get_text(l, "pci-r15")
                            next = 1 
                        elif type in l and type == "\"MeasResultNR\"":
                            type_code[c] = "1"
                            c += 1
                            l = passlines(3, f)
                            multi_output_write(type_code, c, "physCellId", l)
                            next = 1
                        elif type in l and type == "\"measResultServingCell\"":
                            type_code[c] = "1"
                            c += 1
                            l = passlines(3, f)
                            multi_output_write(type_code, c, "physCellId", l)
                            next = 1
                        elif type in l and type == "\"MeasResultCellNR-r15\"":
                            type_code[c] = "1"
                            c += 1
                            l = passlines(3, f)
                            multi_output_write(type_code, c, "pci-r15", l)
                            next = 1
                        elif type in l and type == "\"MeasObjectToAddMod\"":
                            type_code[c] = "1"
                            c += 1
                            l = f.readline()
                            multi_output_write(type_code, c, "measObjectId", l)
                            c += 1 
                            while l:
                                l = f.readline()
                                if "\"lte-rrc.measObject\"" in l:
                                    multi_output_write(type_code, c, "measObject", l)
                                    c += 1
                                    obj = get_text(l, "measObject")
                                    l = passlines(9, f)
                                    if obj == 'measObjectEUTRA (0)':
                                        multi_output_write(type_code, c, "carrierFreq", l)
                                    elif obj == 'measObjectNR-r15 (5)':
                                        c += 1
                                        multi_output_write(type_code, c, "carrierFreq-r15", l)
                                    next = 5
                                    break
                                elif "\"nr-rrc.measObject\"" in l:
                                    multi_output_write(type_code, c, "measObject", l)
                                    c += 1
                                    obj = get_text(l, "measObject")
                                    l = passlines(18, f)
                                    if obj == 'measObjectNR (0)':
                                        c += 2
                                        multi_output_write(type_code, c, "ssbFrequency", l)
                                    next = 5
                                    break
                        elif type in l and type == "\"ReportConfigToAddMod\"":
                            type_code[c] = "1"
                            c += 1
                            l = f.readline()
                            multi_output_write(type_code, c, "reportConfigId", l)

                            c += 1
                            triggerType, l = find_next_str_and_write(type_code, f, ["triggerType", "reportType"], c)

                            c += 1
                            if triggerType == "event (0)":
                                eventId, l = find_next_str_and_write(type_code,f,["eventId"],c)
                                c += 1
                                paras = get_event_paras(f, eventId, l)
                                multi_output_write(type_code, c, paras)
                            elif triggerType == "periodical (1)":
                                l = passlines(3, f)
                                multi_output_write(type_code, c, "purpose", l)
                                c += 1
                                paras = r'{}'
                                multi_output_write(type_code, c, paras)
                            elif triggerType == "eventTriggered (1)":
                                eventId, l = find_next_str_and_write(type_code,f,["eventId"],c)
                                c += 1
                                paras = get_event_paras(f, eventId, l)
                                multi_output_write(type_code, c, paras)

                            next = 4
                        elif type in l and type == 'measIdToRemoveList':
                            if "lte-rrc.measIdToRemoveList" in l:
                                n = ''.join(filter(str.isdigit, get_text(l, "measIdToRemoveList")))
                                n = int(n)
                                l = passlines(2, f)
                                for i in range(n):
                                    multi_output_write(type_code, c, get_text(l, "MeasId"))
                                    l = passlines(3, f)
                        elif type in l and type == "\"MeasIdToAddMod\"":
                            multi_output_write(type_code, c, get_meas_report_pairs(f))
                        elif type in l and type == "\"rrcConnectionReestablishmentRequest\"":
                            type_code[c] = "1"
                            c += 1
                            l = passlines(6, f)
                            type_code[c] = get_text(l, "physCellId")
                            c += 1 
                            l = passlines(4, f)
                            type_code[c] = get_text(l, "reestablishmentCause")
                            next = 2
                        elif type in l and type == "\"scgFailureInformationNR-r15\"":
                            type_code[c] = "1"
                            c += 1
                            l = passlines(13, f)
                            type_code[c] = get_text(l, "failureType-r15")
                            next = 1
                        elif type in l and type == "\"lte-rrc.targetPhysCellId\"":
                            type_code[c] = get_text(l, "targetPhysCellId")                                         
                        elif type in l and type == "\"nr-rrc.physCellId\"":
                            type_code[c] = get_text(l, "physCellId")
                        elif type in l and type == "\"sCellToReleaseList-r10:":
                            type_code[c] = "1"
                            c += 1
                            l = passlines(2, f)
                            type_code[c] = get_text(l, "SCellIndex-r10")
                            next = 1
                        elif type in l and type == "\"SCellToAddMod-r10\"":
                            type_code[c] = "1"
                            c += 1
                            l = passlines(5, f)
                            type_code[c] = get_text(l, "sCellIndex-r10")
                            try:
                                c += 1
                                l = passlines(2, f)
                                type_code[c] = get_text(l, "physCellId-r10")
                                c += 1
                                l = passlines(1, f)
                                type_code[c] = get_text(l, "dl-CarrierFreq-r10")
                            except:
                                c += 2
                            next = 3
                        elif type in l and type not in ["physCellId", "measObjectId", "measObject", "reportConfigId", "measId",]:
                            type_code[c] = "1"
                            
                        c += 1
                    
                    l = f.readline()
                l = f.readline()
                f2.write(",".join([timestamp, type_id, PCI, UL_DL, Freq] + type_code)+'\n')
        else:
            print(l,"Error!")
            break 
            
    f2.close()
    f.close()

def makedir(dirpath, mode=0):  # mode=1: show message, mode=0: hide message
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
        fout = "{}_rrc.csv".format(fin[:-4])
        ### decoding ...
        print(">>>>> convert from '{}' into '{}'...".format(fin, fout))
        xml_to_csv_rrc(fin, fout)
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
            fout = os.path.join(output_path, "{}_rrc.csv".format(filename[:-4]))
            makedir(output_path)
            ### decoding ...
            print(">>>>> convert from '{}' into '{}'...".format(fin, fout))
            xml_to_csv_rrc(fin, fout)
        print()
        t.toc()
        sys.exit()

    # --------------------- (3) decode a batch of files (User Settings) ---------------------
    ### iteratively decode every diag_log.txt file
    for _exp, (_times, _rounds) in Exp_Name.items():
        ### Check if the directories exist
        exp_path = os.path.join(db_path, _exp)
        print(exp_path)
        exp_dirs = []
        for i, dev in enumerate(devices):
            if _rounds:
                exp_dirs.append([os.path.join(exp_path, dev, _round) for _round in _rounds])
            else:
                _rounds = sorted(os.listdir(os.path.join(exp_path, dev)))
                exp_dirs.append([os.path.join(exp_path, dev, item) for item in _rounds])
            exp_dirs[i] = [item for item in exp_dirs[i] if os.path.isdir(item)]
            print(_times)
            pprint(exp_dirs[i])
            if len(exp_dirs[i]) != _times:
                print("************************************************************************************************")
                print("Warning: the number of directories does not match your specific number of experiment times.")
                print("************************************************************************************************")
                print()
                sys.exit()
        print()
        ### Check if a diag_log.txt file exists, and then run decoding
        print(_exp)
        for j in range(_times):
            for i, dev in enumerate(devices):
                print(exp_dirs[i][j])
                dir = os.path.join(exp_dirs[i][j], "data")
                filenames = os.listdir(dir)
                for filename in filenames:
                    # if "diag_log" not in filename or not filename.endswith(".mi2log"):
                    if not filename.startswith("diag_log") or not filename.endswith(".txt"):
                        continue
                    # print(filename)
                    fin = os.path.join(dir, filename)
                    fout = os.path.join(dir, "{}_rrc.csv".format(filename[:-4]))
                    # makedir(os.path.join(dir, "..", "data"))
                    ### decoding ...
                    print(">>>>> decode from '{}' into '{}'...".format(fin, fout))
                    xml_to_csv_rrc(fin, fout)
            print()
    t.toc()
