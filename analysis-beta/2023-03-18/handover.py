import os, sys
import pandas as pd
import numpy as np
import datetime as dt
from collections import namedtuple
from pprint import pprint
import portion as P

# __all__ = [
#     'myQueue',
#     'mi_parse_ho',
#     'cut_head_tail',
#     'get_ho_interval',
#     'label_ho_info',
# ]

class myQueue:
    def __init__(self, maxsize=0):
        self.data = []
        self.maxsize = maxsize if maxsize > 0 else float('inf')
    def tolist(self):
        return self.data
    def size(self):
        return self.maxsize
    def len(self):
        return len(self.data)
    def empty(self):
        return self.len() == 0
    def full(self):
        return self.len() == self.maxsize
    def pop(self, index=0):
        """
        if index > 0, recursively pop() until pop out the specific element.
        return the final popped-out element.
        """
        for _ in range(index, 0, -1):
            self.pop()
        return self.data.pop(0) if not self.empty() else None
    def push(self, element):
        """
        return 0 if success; 1 if the front is popped.
        """
        flag = 0
        if self.full():
            self.pop()
            flag = 1
        self.data.append(element)
        return flag
    def front(self):
        return self.data[0] if not self.empty() else None
    def rear(self):
        return self.data[-1] if not self.empty() else None
    def get(self, index):
        if isinstance(index, list):
            tmp = []
            for i in index:
                tmp = [*tmp, self.get(i)]
            return tmp
        return self.data[index] if index < self.len() and abs(index) <= self.len() else None
    def find(self, element):
        if isinstance(element, list):
            for ele in element:
                index = self.find(ele)
                if index != None:
                    return index
            return None
        return self.data.index(element) if element in self.data else None

def mi_parse_ho(df, tz=0, debug=False):
    df['Timestamp'] = pd.to_datetime(df['Timestamp']) + pd.Timedelta(hours=tz)
    
    ### Define Basic Element
    HO = namedtuple('HO', 'start, end, cause, others, st_scel', defaults=tuple([None]*4+[0]))
    stNR = namedtuple('stNR', 'snrPCI, tnrPCI', defaults=tuple([None]*2))
    stLTE = namedtuple('stLTE', 'sPCI, sFreq, tPCI, tFreq', defaults=tuple([None]*4))
    NR_CEL = namedtuple('NR_CEL', 'nrPCI, nrFreq', defaults=tuple([None]*2))
    LTE_CEL = namedtuple('LTE_CEL', 'ePCI, ECI, eNB, BID, DL_Freq, DL_BW, UL_Freq, UL_BW', defaults=tuple([None]*8))
    C = namedtuple('C', HO._fields + stLTE._fields + stNR._fields + \
        LTE_CEL._fields + tuple([f'{s}1' for s in LTE_CEL._fields]) + NR_CEL._fields + tuple([f'{s}1' for s in NR_CEL._fields]), 
        defaults=tuple([None]*30))
    
    def dprint(*args, **kwargs):
        if debug:
            print(*args, **kwargs)
    
    def NR_OTA(pos=None):
        row = df.iloc[pos] if pos else df.iloc[i]
        if row.type_id == '5G_NR_RRC_OTA_Packet':
            return True
        else:
            return False
    
    def CEL_INFO(pos=None):
        row = df.iloc[pos] if pos else df.iloc[i]
        if row.type_id == 'LTE_RRC_Serv_Cell_Info':
            return True
        else:
            return False
    
    def nr_track(pos=None):
        row = df.iloc[pos] if pos else df.iloc[i]
        if int(row.PCI) in [0, 65535]:  # 65535 is for samgsung; 0 is for xiaomi.
            return NR_CEL()
        else:
            return NR_CEL(int(row.PCI), int(row.Freq))
    
    def eci_track(pos=None):
        row = df.iloc[pos] if pos else df.iloc[i]
        PCI = int(row['PCI'])
        ECI = int(row['Cell Identity'])
        eNB = ECI // 256
        BID = int(row['Band ID'])
        DL_Freq = int(row['DL frequency'])
        DL_BW = row['DL bandwidth']
        UL_Freq = int(row['UL frequency'])
        UL_BW = row['UL bandwidth']
        return LTE_CEL(PCI, ECI, eNB, BID, DL_Freq, DL_BW, UL_Freq, UL_BW)
    
    def peek_nr(pos=None, look_after=0.5, look_before=0.0):
        ## look_after == 0.5 is a magic number
        ### TODO 先偷看 ho start - end 之間的 cell information
        if pos:  # position of end of an event
            for j in range(i, pos):
                if NR_OTA(j):
                    qpscell.push(nr_track(j))
        ### END TODO
        # dprint(f'pscell={pscell}')
        # dprint(qpscell.tolist())
        index = None
        for j in range(qpscell.len()):
            if pscell != qpscell.get(j):
                index = j
                break
        # dprint(f'index={index}')
        if index != None:
            return qpscell.pop(index)
        ### haven't find pci change yet!
        t = df['Timestamp'].iloc[i]
        for j in range(i, len(df)):  # 往前走，最多走到底
            t1 = df["Timestamp"].iloc[j]
            if (t1 - t).total_seconds() > look_after:
                break
            if df['type_id'].iloc[j] != '5G_NR_RRC_OTA_Packet':
                continue
            row = df.iloc[j]
            if int(row.PCI) in [0, 65535]:  # 65535 is for samgsung; 0 is for xiaomi.
                return NR_CEL()
            else:
                return NR_CEL(int(row.PCI), int(row.Freq))
        return pscell
    
    def peek_eci(pos=None, look_after=0.5, look_before=0.0):
        ## look_after == 0.5 is a magic number
        ### TODO 先偷看 ho start - end 之間的 cell information
        if pos:  # position of end of an event
            for j in range(i, pos):
                if CEL_INFO(j):
                    qpcell.push(eci_track(j))
        ### END TODO
        # dprint(f'pcell={pcell}')
        # dprint(qpcell.tolist())
        index = None
        for j in range(qpcell.len()):
            if pcell != qpcell.get(j):
                index = j
                break
        # dprint(f'index={index}')
        if index != None:
            return qpcell.pop(index)
        ### haven't find pci change yet!
        t = df['Timestamp'].iloc[i]
        for j in range(i, len(df)):  # 往前走，最多走到底
            t1 = df['Timestamp'].iloc[j]
            if (t1 - t).total_seconds() > look_after:
                break
            if df['type_id'].iloc[j] != 'LTE_RRC_Serv_Cell_Info':
                continue
            row = df.iloc[j]
            PCI = int(row['PCI'])
            ECI = int(row['Cell Identity'])
            eNB = ECI // 256
            BID = int(row['Band ID'])
            DL_Freq = int(row['DL frequency'])
            DL_BW = row['DL bandwidth']
            UL_Freq = int(row['UL frequency'])
            UL_BW = row['UL bandwidth']
            return LTE_CEL(PCI, ECI, eNB, BID, DL_Freq, DL_BW, UL_Freq, UL_BW)
        return pcell

    def find_1st_after(target, look_after=1.0):
        for j in range(i, len(df)):  # 往前走，最多走到底
            t1 = df["Timestamp"].iloc[j]
            if (t1 - t).total_seconds() > look_after:
                return None, None
            if df[target].iloc[j] in [1,'1']:
                return t1, j  # timestamp & position
        return None, None

    def find_1st_before(target, look_before=1.0):
        for j in range(i, -1, -1):  # 倒退嚕，最多走回頭
            t1 = df["Timestamp"].iloc[j]
            if (t - t1).total_seconds() > look_before:
                return None, None
            if df[target].iloc[j] in [1,'1']:
                return t1, j  # timestamp & position
        return None, None

    D = {
        ### Conn Setup/Rel & HO
        'Conn_Rel':[],    # Conn Release: rrcConnectionRelease
        'Conn_Setup':[],  # Conn Setup: rrcConnectionRequest + rrcConnectionSetup
        'LTE_HO': [],     # E_PCel -> E_PCel’: lte-rrc.t304 & LTE_PCel does change
        'SN_Rel': [],     # EUTRA + NR -> EUTRA:(CHT) lte-rrc.t304 & LTE_PCel does not change
                          #                     (TWM) nr-Config-r15: release (0) 
        'SN_Setup': [],   # EUTRA -> EUTRA + NR:(CHT) lte-rrc.t304 + nr-rrc.t304 + dualConnectivityPHR: setup (1) & LTE_PCel does not change
                          #                     (TWM) nr-rrc.t304 + dualConnectivityPHR: setup (1)
        'MN_HO': [],      # E_PCel + N_PSCel -> E_PCel’ + N_PSCel: lte-rrc.t304 + nr-rrc.t304 + dualConnectivityPHR: setup (1) & LTE_PCel does change
        'SN_HO': [],      # E_PCel + N_PSCel -> E_PCel + N_PSCel’: nr-rrc.t304
        'MNSN_HO': [],         # (TWM)
        'SN_Rel_MN_HO': [],    # (TWM)
        'SN_Setup_MN_HO': [],  # (TWM)
        ### Link Failure
        'SCG_Failure': [],   # scgFailureInformationNR-r15
        'MCG_Failure': [],   # rrcConnectionReestablishmentRequest + rrcConnectionReestablishmentComplete
        'NAS_Recovery': [],  # rrcConnectionReestablishmentRequest + rrcConnectionReestablishmentReject + rrcConnectionRequest + rrcConnectionSetup
        # MCG_Failure, NAS_Recovery may be caused by 'reconfigurationFailure (0)', 'handoverFailure (1)', 'otherFailure (2)'
        }
    
    A = { 'Conn_Rel':[], 'Conn_Setup':[],
          'LTE_HO': [], 'SN_Rel': [], 'SN_Setup': [], 'MN_HO': [], 'SN_HO': [],
          'MNSN_HO': [], 'SN_Rel_MN_HO': [], 'SN_Setup_MN_HO': [],
          'SCG_Failure': [], 'MCG_Failure': [], 'NAS_Recovery': [] }
    
    qpscell = myQueue(3)
    qpcell = myQueue(3)
    
    init = 1
    pcell, pscell = LTE_CEL(), NR_CEL()
    prev_pci, prev_freq = None, None
    
    for i, row in df.iterrows():
        if NR_OTA():
            qpscell.push(nr_track())
            continue
        elif CEL_INFO():
            qpcell.push(eci_track())
            continue
        if init:
            t_init, pci_init, freq_init = row.Timestamp, int(row.PCI), int(row.Freq)
            pcell = LTE_CEL(ePCI=pci_init, DL_Freq=freq_init)
            dprint(f"{t_init} | Initial PCI={pci_init} EARFCN={freq_init}")
            dprint()
            init = 0
        
        t, pci, freq = row.Timestamp, int(row.PCI), int(row.Freq)
        
        if (prev_pci, prev_freq) != (pci, freq):
            for j in range(i, len(df)):  # 往前走，最多走到底
                if CEL_INFO(j):
                    next_pcell = eci_track(j)
                    if next_pcell[0] == pci:
                        qpcell.push(next_pcell)
                        break
                elif not NR_OTA(j):
                    if df['PCI'].iloc[j] != pci:
                        break
        
        if not qpscell.empty():
            pscell = qpscell.pop()
        if not qpcell.empty():
            pcell = qpcell.pop()
        
        ### Conn_Rel
        if df["rrcConnectionRelease"].iloc[i] == 1:
            D['Conn_Rel'].append(HO(start=t))
            A['Conn_Rel'].append(C(*HO(start=t), *stLTE(sPCI=pci, sFreq=freq), *stNR(snrPCI=pscell[0]), *pcell, *LTE_CEL(), *pscell, *NR_CEL()))
            dprint(f"{t}, {pd.NaT} | Conn_Rel at PCI={pci} EARFCN={freq}.")
            dprint(f'{tuple(pcell)} -> {tuple(LTE_CEL())}')
            dprint(f'{tuple(pscell)} ->{tuple(NR_CEL())}')
            pcell, pscell = LTE_CEL(), NR_CEL()
            dprint()

        ### Conn_Setup
        if df["rrcConnectionRequest"].iloc[i] == 1:
            a, j1 = find_1st_after('rrcConnectionReconfigurationComplete',look_after=2)
            b, j2 = find_1st_after('securityModeComplete',look_after=2)
            end = a if a > b else b
            j = j1 if a > b else j2
            _pcell = peek_eci(pos=j)
            D['Conn_Setup'].append(HO(start=t, end=end))
            A['Conn_Setup'].append(C(*HO(start=t, end=end), *stLTE(tPCI=pci, tFreq=freq), *stNR(), *pcell, *_pcell, *pscell, *pscell))
            dprint(f"{t}, {end} | Conn_Setup to PCI={pci} EARFCN={freq}.")
            dprint(f'{tuple(pcell)} -> {tuple(_pcell)}')
            dprint(f'{tuple(pscell)} -> {tuple(pscell)}')
            dprint()
        
        ### SN_Setup, SN_Rel, MO_HO, LTE_HO
        if df["lte-rrc.t304"].iloc[i] == 1:
            end, j = find_1st_after('rrcConnectionReconfigurationComplete')
            serv_cell, target_cell = pci, int(df['lte_targetPhysCellId'].iloc[i])
            serv_freq, target_freq = freq, int(df['dl-CarrierFreq'].iloc[i])
            nr_target_cell = int(df["nr_physCellId"].iloc[i])
            
            n = 0
            if df["SCellToAddMod-r10"].iloc[i] == 1:
                n =len(str(df["SCellIndex-r10.1"].iloc[i]).split('@'))
                others=f'Set up {n} SCell.'
            else:
                others=None
            
            if serv_freq != target_freq:
                others = f'{others} Inter-Freq HO.' if others else 'Inter-Freq HO.'
            
            ### SN_Setup, MN_HO
            if df["nr-rrc.t304"].iloc[i] == 1 and df["dualConnectivityPHR: setup (1)"].iloc[i] == 1:
                ### SN_Setup
                if serv_cell == target_cell and serv_freq == target_freq:
                    _pscell = peek_nr(pos=j)
                    D['SN_Setup'].append(HO(start=t, end=end, others=others, st_scel=n))
                    A['SN_Setup'].append(C(*HO(start=t, end=end, others=others, st_scel=n), *stLTE(sPCI=serv_cell, sFreq=serv_freq), *stNR(tnrPCI=nr_target_cell), *pcell, *pcell, *pscell, *_pscell))
                    dprint(f"{t}, {end} | SN_Setup to nrPCI={nr_target_cell} | {others}")
                    dprint(f'{tuple(pcell)} -> {tuple(pcell)}')
                    dprint(f'{tuple(pscell)} -> {tuple(_pscell)}')
                    dprint()
                else:
                ### MN_HO
                    _pcell = peek_eci(pos=j)
                    D['MN_HO'].append(HO(start=t, end=end, others=others, st_scel=n))
                    A['MN_HO'].append(C(*HO(start=t, end=end, others=others, st_scel=n), *stLTE(sPCI=serv_cell, sFreq=serv_freq, tPCI=target_cell, tFreq=target_freq), *stNR(snrPCI=pscell[0]), *pcell, *_pcell, *pscell, *pscell))
                    dprint(f"{t}, {end} | MN_HO ({serv_cell}, {serv_freq}) -> ({target_cell}, {target_freq}) | {others}")
                    dprint(f'{tuple(pcell)} -> {tuple(_pcell)}')
                    dprint(f'{tuple(pscell)} -> {tuple(pscell)}')
                    dprint()
            else:
            ### SN_Rel, LTE_HO
                ### SN_Rel
                if serv_cell == target_cell and serv_freq == target_freq:
                    a, b = find_1st_before("scgFailureInformationNR-r15")
                    if a is not None:
                        others = f'{others} Caused by scg-failure.' if others else 'Caused by scg-failure.'
                    D['SN_Rel'].append(HO(start=t, end=end, others=others, st_scel=n))
                    A['SN_Rel'].append(C(*HO(start=t, end=end, others=others, st_scel=n), *stLTE(sPCI=serv_cell, sFreq=serv_freq), *stNR(snrPCI=pscell[0]), *pcell, *pcell, *pscell, *NR_CEL()))
                    dprint(f"{t}, {end} | SN_Rel at nrPCI={pscell[0]} | {others}")
                    dprint(f'{tuple(pcell)} -> {tuple(pcell)}')
                    dprint(f'{tuple(pscell)} -> {tuple(NR_CEL())}')
                    pscell = NR_CEL()
                    dprint()
                else:
                ### LTE_HO
                    _pcell = peek_eci(pos=j)
                    D['LTE_HO'].append(HO(start=t, end=end, others=others, st_scel=n))
                    A['LTE_HO'].append(C(*HO(start=t, end=end, others=others, st_scel=n), *stLTE(sPCI=serv_cell, sFreq=serv_freq, tPCI=target_cell, tFreq=target_freq), *stNR(), *pcell, *_pcell, *pscell, *pscell))
                    dprint(f"{t}, {end} | LTE_HO ({serv_cell}, {serv_freq}) -> ({target_cell}, {target_freq}) | {others}")
                    dprint(f'{tuple(pcell)} -> {tuple(_pcell)}')
                    dprint(f'{tuple(pscell)} -> {tuple(pscell)}')
                    dprint()

        ### SN_HO
        if df["nr-rrc.t304"].iloc[i] == 1 and not df["dualConnectivityPHR: setup (1)"].iloc[i] == 1:
            end, j = find_1st_after('rrcConnectionReconfigurationComplete')
            nr_target_cell = int(df["nr_physCellId"].iloc[i])
            _pscell = peek_nr(pos=j)
            D['SN_HO'].append(HO(start=t, end=end))
            A['SN_HO'].append(C(*HO(start=t, end=end), *stLTE(sPCI=pci, sFreq=freq), *stNR(snrPCI=pscell[0], tnrPCI=nr_target_cell), *pcell, *pcell, *pscell, *_pscell))
            dprint(f"{t}, {end} | SN_HO to nrPCI={nr_target_cell}")
            dprint(f'{tuple(pcell)} -> {tuple(pcell)}')
            dprint(f'{tuple(pscell)} -> {tuple(_pscell)}')
            dprint()

        ### SCG_Failure
        if df["scgFailureInformationNR-r15"].iloc[i] == 1:
            # others = df["failureType-r15"].iloc[i]
            cause = df["failureType-r15"].iloc[i]
            _pscell = peek_nr()
            D['SCG_Failure'].append(HO(start=t, cause=cause))  # end time??
            A['SCG_Failure'].append(C(*HO(start=t, cause=cause), *stLTE(sPCI=pci, sFreq=freq), *stNR(snrPCI=pscell[0]), *pcell, *pcell, *pscell, *_pscell))
            dprint(f"{t}, {pd.NaT} | SCG_Failure at nrPCI={pscell[0]} | {cause}")
            dprint(f'{tuple(pcell)} -> {tuple(pcell)}')
            dprint(f'{tuple(pscell)} -> {tuple(_pscell)}')
            ### SCG Fail 之後必定會 SN Rel
            dprint()
        
        ### MCG_Failure (type II), NAS_Recovery (type III)
        if df["rrcConnectionReestablishmentRequest"].iloc[i] == 1:
            end1, j1 = find_1st_after('rrcConnectionReestablishmentComplete', look_after=1)
            end2, j2 = find_1st_after('rrcConnectionReestablishmentReject', look_after=1)
            end3, j3 = find_1st_after('rrcConnectionRequest', look_after=1)
            # others = df["reestablishmentCause"].iloc[i]
            cause = df["reestablishmentCause"].iloc[i]
            # target_cell = int(df['physCellId.3'].iloc[i])
            serv_cell, target_cell = pci, int(df['physCellId.3'].iloc[i])
            serv_freq, target_freq = freq, None
            
            ### MCG_Failure (type II)
            if (end1 and not end2) or (end1 and end2 and end1 < end2):
                # dprint(end1, end2)
                end, j = end1, j1
                _pcell = peek_eci()
                D['MCG_Failure'].append(HO(start=t, end=end, cause=cause))
                A['MCG_Failure'].append(C(*HO(start=t, end=end, cause=cause), *stLTE(sPCI=serv_cell, sFreq=serv_freq, tPCI=target_cell, tFreq=target_freq), *stNR(snrPCI=pscell[0]), *pcell, *_pcell, *pscell, *NR_CEL()))
                dprint(f"{t}, {end} | MCG_Failure PCI={serv_cell} -> PCI={target_cell}, recconected to {pci} | {cause}")
                dprint(f'{tuple(pcell)} -> {tuple(_pcell)}')
                dprint(f'{tuple(pscell)} -> {tuple(NR_CEL())}')
                pscell = NR_CEL()
                dprint()
                ### MCG Fail 之後有機會不經過 RRC Connection Setup 就 Reconnect
            else: 
            ### NAS_Recovery (type III)
                # dprint(end1, end2)
                end, j = end3, j3
                _pcell = peek_eci()
                D['NAS_Recovery'].append(HO(start=t, end=end-pd.Timedelta(microseconds=1) if end else None, cause=cause))  # end time??
                A['NAS_Recovery'].append(C(*HO(start=t, end=end-pd.Timedelta(microseconds=1) if end else None, cause=cause), *stLTE(sPCI=serv_cell, sFreq=serv_freq, tPCI=target_cell, tFreq=target_freq), *stNR(snrPCI=pscell[0]), *pcell, *_pcell, *pscell, *NR_CEL()))
                dprint(f"{t}, {end} | NAS_Recovery PCI={serv_cell} -> PCI={target_cell} | {cause}")
                dprint(f'{tuple(pcell)} -> {tuple(_pcell)}')
                dprint(f'{tuple(pscell)} -> {tuple(NR_CEL())}')
                pscell = NR_CEL()
                dprint()
        
        ### Update previous pci, freq
        prev_pci, prev_freq = pci, freq
    
    ### Build DataFrame
    df_HO = pd.DataFrame()
    for key in A.keys():
        df_HO = pd.concat([df_HO, \
            pd.DataFrame(A[key], index=[key]*len(A[key]))])
    if df_HO.empty:
        print("************** Empty DataFrame!! **************")
    df_HO = df_HO.sort_values(by=['start']).reset_index()
    df_HO = df_HO.rename(columns={'index': 'ho_type'})
    df_HO = df_HO.reindex(
        ['start','end','ho_type','intr','sPCI','sFreq','tPCI','tFreq','snrPCI','tnrPCI','cause','others','st_scel'] + \
            df_HO.columns.tolist()[df_HO.columns.get_loc('ePCI'):df_HO.columns.get_loc('nrFreq1')+1], axis=1)
    df_HO['start'] = pd.to_datetime(df_HO['start'])
    df_HO['end'] = pd.to_datetime(df_HO['end'])
    df_HO['Timestamp'] = df_HO['start']
    df_HO['intr'] = (df_HO['end'] - df_HO['start']).dt.total_seconds()
    df_HO['type_id'] = 'RRC_OTA_Handover_Parsing'
    ### Set dtypes
    df_HO['ho_type'] = df_HO['ho_type'].astype('category')
    df_HO['cause'] = df_HO['cause'].astype('category')
    df_HO['others'] = df_HO['others'].astype('string')
    df_HO['st_scel'] = df_HO['st_scel'].astype('Int8')
    df_HO['DL_BW'] = df_HO['DL_BW'].astype('category')
    df_HO['DL_BW1'] = df_HO['DL_BW1'].astype('category')
    df_HO['UL_BW'] = df_HO['UL_BW'].astype('category')
    df_HO['UL_BW1'] = df_HO['UL_BW1'].astype('category')
    for tag in df_HO.columns[df_HO.columns.get_loc('sPCI'):df_HO.columns.get_loc('nrFreq1')+1]:
        if tag not in ['cause','others','DL_BW','DL_BW1','UL_BW','UL_BW1']:
            df_HO[tag] = df_HO[tag].astype('Int32')
    df_HO['intr'] = df_HO['intr'].astype('float32')
    df_HO['Timestamp'] = pd.to_datetime(df_HO['Timestamp'])
    df_HO['type_id'] = df_HO['type_id'].astype('category')
    return df_HO, A, D

def cut_head_tail(df_HO, df, mode='ul'):
    if mode == 'ul':
        start = df.iloc[0].xmit_time
        stop = df.iloc[-1].xmit_time
        df_HO = df_HO.query('Timestamp >= @start & Timestamp <= @stop').copy().reset_index(drop=True)
    if mode == 'dl':
        start = df.iloc[0].arr_time
        stop = df.iloc[-1].arr_time
        df_HO = df_HO.query('Timestamp >= @start & Timestamp <= @stop').copy().reset_index(drop=True)
    return df_HO

def is_disjoint(set1, set2):
    """
    Check if two sets are disjoint.
    """
    return (set1 & set2).empty

def is_disjoint_dict(E):
    test_intv = P.empty()
    for key, val in E.items():
        # print(key)
        for intv in val:
            if is_disjoint(test_intv, intv.interval):
                test_intv = test_intv | intv.interval
            else:
                print(key, intv.index)
                return False
    return True

def interp(x, y, ratio):
    """
    Interpolation

    Args:
        x, y (datetime.datetime): x < y
        ratio (float): a decimal numeral in a range [0, 1]; 0 means break at x, 1 means break at y.
    Returns:
        (datetime.datetime): breakpoint of interpolation
    """
    return x + (y - x) * ratio

def get_ho_interval(df, sec=(1, 3), ratio=0.5,
                 ignored=['Conn_Setup','Conn_Rel'],
                 handover=['LTE_HO','SN_Rel','SN_Setup','MN_HO','SN_HO','MNSN_HO','SN_Rel_MN_HO','SN_Setup_MN_HO'],
                 linkfailure=['SCG_Failure','MCG_Failure','NAS_Recovery']):
    
    HO_INTV = namedtuple('HO_INTV', 'index, interval, state1, state2, st_scel, cause, interrupt, \
                                     ePCI, earfcn, nrPCI, ePCI1, earfcn1, nrPCI1', defaults=tuple([None]*12))
    
    def ignore_col(row):
        if row.ho_type in ignored:
            return False
        else:
            return True
    df = df[df.apply(ignore_col, axis=1)].reset_index(drop=True)
    
    column_names = []
    for type_name in handover + linkfailure:
        column_names += ["before_{}".format(type_name), "during_{}".format(type_name), "after_{}".format(type_name)]
    E = { col:[] for col in column_names }
    
    for i, row in df.iterrows():
        prior_row = df.iloc[i-1] if i != 0 else None
        post_row = df.iloc[i+1] if i != len(df)-1 else None
        ### peek the next event
        if i != len(df)-1 and pd.notna(row.end) and row.end > post_row.start:
            print(i, row.start, row.end, row.ho_type, row.cause)
            print(i+1, post_row.start, post_row.end, post_row.ho_type, post_row.cause)
            continue
        ### peri_interval
        if pd.isna(row.end):
            peri_interval = P.singleton(row.start)
        else:
            peri_interval = P.closed(row.start, row.end)
        ### prior_interval
        C = row.start - pd.Timedelta(seconds=sec[0]) if row.ho_type in handover else row.start - pd.Timedelta(seconds=sec[1])
        D = row.start
        prior_interval = P.closedopen(C, D)
        if ratio != None and i != 0:
            A = max(prior_row.start, prior_row.end)
            B = max(prior_row.start, prior_row.end) + pd.Timedelta(seconds=sec[0]) if prior_row.ho_type in handover else max(prior_row.start, prior_row.end) + pd.Timedelta(seconds=sec[1])
            if P.openclosed(A, B).overlaps(prior_interval):
                # print("Overlaps with the previous!")
                bkp = interp(C, B, ratio)
                bkp = max(bkp, A)  # to avoid the breakpoint overlaps the previous event's duration
                # bkp = min(max(bkp, A), D)  # 我不侵犯到其他任何人，代表其他人也不會侵犯到我！
                prior_interval = P.closedopen(bkp, D)
                if A in prior_interval:
                    prior_interval = P.open(bkp, D)
                # blindly set as open inverval is fine, but may miss one point.
        ### post_interval
        C = row.end
        D = row.end + pd.Timedelta(seconds=sec[0]) if row.ho_type in handover else row.end + pd.Timedelta(seconds=sec[1])
        post_interval = P.openclosed(C, D)
        if ratio != None and i != len(df)-1:
            A = min(post_row.start, post_row.end) - pd.Timedelta(seconds=sec[0]) if post_row.ho_type in handover else min(post_row.start, post_row.end) - pd.Timedelta(seconds=sec[1])
            B = min(post_row.start, post_row.end)
            if P.closedopen(A, B).overlaps(post_interval):
                # print("Overlaps with the following!")
                bkp = interp(A, D, ratio)
                bkp = min(bkp, B)  # to avoid the breakpoint overlaps the following event's duration
                # bkp = max(min(bkp, B), C)  # 我不侵犯到其他任何人，代表其他人也不會侵犯到我！
                post_interval = P.open(C, bkp)
        ### append dictionary
        type_name = row.ho_type
        state1, state2 = 'sn_change', 'sn_change'
        if type_name in linkfailure:
            state1, state2 = 'link_failure', 'link_failure'
        if type_name in ['LTE_HO','MN_HO','MNSN_HO','SN_Rel_MN_HO','SN_Setup_MN_HO']:
            state1 = 'inter_freq' if row.sFreq != row.tFreq else 'intra_freq'
            if pd.notna(row.eNB) and pd.notna(row.eNB1) and row.eNB != row.eNB1:
                state2 = 'inter_enb'
            elif row.sPCI != row.tPCI:
                state2 = 'inter_sector'
            elif row.sPCI == row.tPCI:
                state2 = 'intra_sector'
            else:
                print("************** inter_enb, unknown eNB_ID **************")
                state2 = 'inter_enb'
        E[f'before_{type_name}'].append(HO_INTV(i, prior_interval, state1, state2, row.st_scel, row.cause, row.intr, row.sPCI, row.sFreq, row.snrPCI, row.tPCI, row.tFreq, row.tnrPCI))
        E[f'during_{type_name}'].append(HO_INTV(i, peri_interval, state1, state2, row.st_scel, row.cause, row.intr, row.sPCI, row.sFreq, row.snrPCI, row.tPCI, row.tFreq, row.tnrPCI))
        E[f'after_{type_name}'].append(HO_INTV(i, post_interval, state1, state2, row.st_scel, row.cause, row.intr, row.sPCI, row.sFreq, row.snrPCI, row.tPCI, row.tFreq, row.tnrPCI))
        ### check whether the intervals are pairwise disjoint
        if not is_disjoint_dict(E):
            print('Warning: Intervals are not totally disjoint!')
    return E

def label_ho_info(df, E, mode='ul'):
    def removeprefix(string, prefix=['before','during','after']):
        for pref in prefix:
            if string.startswith(pref):
                return pref, string[len(pref)+1:]
        return None, string
    
    df = df.reindex(columns=[*list(df.columns),
            'ho_index','ho_stage','ho_type','ho_type1','ho_type2','ho_scel','ho_cause','ho_intr',
            'ho_ePCI','ho_earfcn','ho_nrPCI','ho_ePCI1','ho_earfcn1','ho_nrPCI1'])
    
    df[['ho_index','ho_stage','ho_type','ho_type1','ho_type2','ho_scel','ho_cause','ho_intr',
        'ho_ePCI','ho_earfcn','ho_nrPCI','ho_ePCI1','ho_earfcn1','ho_nrPCI1']] = \
        [-1, '-', 'stable', 'stable', 'stable', 0, None, None,
         None, None, None, None, None, None]
            
    for key, val in E.items():
        pref, key = removeprefix(key)
        for intv in val:
            if intv.interval.empty:
                continue
            # print(pref, key)
            # print(intv.interval)
            if mode == 'ul':
                df.loc[(df['xmit_time'] >= intv.interval.lower) & (df['xmit_time'] <= intv.interval.upper),
                       ('ho_index','ho_stage','ho_type','ho_type1','ho_type2','ho_scel','ho_cause','ho_intr',
                        'ho_ePCI','ho_earfcn','ho_nrPCI','ho_ePCI1','ho_earfcn1','ho_nrPCI1')] = \
                        [intv.index, pref, key, intv.state1, intv.state2, intv.st_scel, intv.cause, intv.interrupt,
                        intv.ePCI, intv.earfcn, intv.nrPCI, intv.ePCI1, intv.earfcn1, intv.nrPCI1]
            if mode == 'dl':
                df.loc[(df['arr_time'] >= intv.interval.lower) & (df['arr_time'] <= intv.interval.upper),
                       ('ho_index','ho_stage','ho_type','ho_type1','ho_type2','ho_scel','ho_cause','ho_intr',
                        'ho_ePCI','ho_earfcn','ho_nrPCI','ho_ePCI1','ho_earfcn1','ho_nrPCI1')] = \
                        [intv.index, pref, key, intv.state1, intv.state2, intv.st_scel, intv.cause, intv.interrupt,
                        intv.ePCI, intv.earfcn, intv.nrPCI, intv.ePCI1, intv.earfcn1, intv.nrPCI1]
    
    df['ho_type0'] = df['ho_type']
    df.loc[np.in1d(df['ho_type'], ['SCG_Failure','MCG_Failure','NAS_Recovery']), 'ho_type0'] = \
        df.loc[np.in1d(df['ho_type'], ['SCG_Failure','MCG_Failure','NAS_Recovery']), 'ho_type'] + '_' + df.loc[np.in1d(df['ho_type'], ['SCG_Failure','MCG_Failure','NAS_Recovery']), 'ho_cause']
    
    df['_ho_type'] = df['ho_type']
    df['_ho_type0'] = df['ho_type0']
    df['_ho_type1'] = df['ho_type1']
    df['_ho_type2'] = df['ho_type2']
    df.loc[~np.in1d(df['ho_type'], ['stable']), '_ho_type'] = df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_stage'] + '_' + df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_type']
    df.loc[~np.in1d(df['ho_type'], ['stable']), '_ho_type0'] = df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_stage'] + '_' + df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_type0']
    df.loc[~np.in1d(df['ho_type'], ['stable']), '_ho_type1'] = df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_stage'] + '_' + df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_type1']
    df.loc[~np.in1d(df['ho_type'], ['stable']), '_ho_type2'] = df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_stage'] + '_' + df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_type2']
    
    df['ho_index'] = df['ho_index'].astype('Int32')
    df['ho_stage'] = df['ho_stage'].astype('category')
    df['ho_type'] = df['ho_type'].astype('category')
    df['ho_type0'] = df['ho_type0'].astype('category')
    df['ho_type1'] = df['ho_type1'].astype('category')
    df['ho_type2'] = df['ho_type2'].astype('category')
    df['ho_scel'] = df['ho_scel'].astype('Int8')
    df['ho_cause'] = df['ho_cause'].astype('category')
    df['ho_intr'] = df['ho_intr'].astype('float32')
    for tag in df.columns[df.columns.get_loc('ho_ePCI'):df.columns.get_loc('ho_nrPCI1')+1]:
        df[tag] = df[tag].astype('Int32')
    df['_ho_type'] = df['_ho_type'].astype('category')
    df['_ho_type0'] = df['_ho_type'].astype('category')
    df['_ho_type1'] = df['_ho_type1'].astype('category')
    df['_ho_type2'] = df['_ho_type2'].astype('category')
    
    return df

