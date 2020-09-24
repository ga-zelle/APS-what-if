#
"""
	Scan APS logfile and extract relevant items
    to compare original SMB analysis vs. the determine_basal.py
"""
#	Version INIT		Started	08.Dec.2019			Author	Gerhard Zellermann
#   - adapted from scanAPSlog.py

import sys
import os
import glob
from email.utils import formatdate
import datetime
from datetime import timezone
import time
import json
import zipfile
from decimal import *
import binascii
import copy

import determine_basal as detSMB
from determine_basal import my_ce_file 


def hole(sLine, Ab, Auf, Zu):
    #E extrahiere Substring ab der Stelle "ab"
    #E	beginnend mit dem Zeichen "Auf" bis zum Zeichen "Zu"
    #E	wobei Level gezählt werden wie in "...[xxx[yy]]..."
    offsetAnf = 0
    offsetEnd = 0
    Anf_pos = sLine[Ab:].find(Auf) + Ab
    #if sLine.find('[Intent')<3: print('hole gerufen mit:' , Auf, ' an Stelle', str(Anf_pos), 'in '+sLine)
    while Anf_pos>=0:
        End_pos = sLine[Anf_pos+offsetEnd+1:].find(Zu) + Anf_pos+offsetEnd+1
        #if sLine.find('[Intent')<3: print(str(Anf_pos)+':'+  Auf+', '+ str(End_pos)+':'+  Zu, 'in '+sLine[Anf_pos+offsetEnd+1:])
        if End_pos == Anf_pos+offsetEnd+1*0:    break
        Zw_Anf = sLine[Anf_pos+offsetAnf+1:End_pos].find(Auf) + Anf_pos+offsetAnf+1
        #if sLine.find('[Intent')<3: print ('suche  2. Vorkommen von '+Auf+' in '+sLine[Anf_pos+offsetAnf+1:End_pos])
        #if sLine.find('[Intent')<3: print (str(Zw_Anf), str(offsetAnf), str(offsetEnd))
        if Zw_Anf==Anf_pos+offsetAnf:   #+1  or  Zw_Anf>End_pos:
            return sLine[Anf_pos:End_pos+1]
            break
        offsetAnf = Zw_Anf  - Anf_pos
        offsetEnd = End_pos - Anf_pos #+ 1
        #wdhl = input('any key')
    return ''

def GetStr(Curly, Ab, Key):
    #E extrahiere Substring für Flag "Key" ab der Stelle Ab

    wo	= Curly[Ab:].find('"' + Key +'"') + Ab
    if wo < Ab:
        Found = ''
    else:
        bis		= Curly[wo+len(Key)+4:].find('"') + wo+len(Key)+4
        Found	= Curly[wo+len(Key)+4:bis]
        #print (str(wo), str(bis))
    return Found 

def GetValStr(Curly, Ab, Key):
    #E extrahiere Number as String für Flag "Key" ab der Stelle Ab

    wo	= Curly[Ab:].find('"' + Key +'"') + Ab
    if wo < Ab:
        Found = ''
    else:
        bis		= Curly[wo+len(Key)+3:].find(',') + wo+len(Key)+3
        Found	= Curly[wo+len(Key)+3:bis]
        #print (str(wo), str(bis))
    return Found 

def GetUnquotedStr(Curly, Ab, Key):
    #E extract unquoted String für Flag "Key" ab der Stelle Ab up to next COMMA

    wo	= Curly[Ab:].find(Key) + Ab
    if wo < Ab:
        Found = ''
    else:
        bis		= Curly[wo+len(Key)+0:].find(',') + wo+len(Key)+0
        Found	= Curly[wo+len(Key)+0:bis]
        #print (str(wo), str(bis))
    return Found 

def printBool(treat, key, log):
    if 'isSMB' in treat:        isSMB = treat[key]
    else:                       isSMB = False
    log.write('  ' + (key+'   ')[:5] + '=' + str(isSMB) + '\n')

def printStr(treat, key, log):
    if key in treat:
        myStr = treat[key]
        wo = myStr.find('\n')
        if wo>0:
            myEnd = myStr[wo+1:]                    # \n counts as 1 character !!
            myStr = myStr[:wo] + ' --> ' + myEnd    # Announcements often take 2 lines
    else:
        myStr = ''
    log.write('  ' + (key+'         ')[:10] + '=' + myStr + '\n')

def printVal(treat, key, log):
    log.write('  ' + (key+'    ')[:6] + '=' + str(treat[key]) + '\n')

def getReason(reason, keyword, ending, dezi):
    wo_key = reason.find(keyword)
    #print (wo_key, reason + '\n')
    if wo_key < 0:
        #print (keyword , 'nicht gefunden')
        return ''
    else:
        wo_com = reason[wo_key+len(keyword)+1:].find(ending) + wo_key+len(keyword)+1
        #print (reason[wo_key:])
        key_str = reason[wo_key+len(keyword):wo_com]
        #print ('complete-->', keyword, '['+key_str+']')
        #key_str = key_str[:-1]
        #print ('  capped-->', keyword, '['+key_str+']')
        return key_str

def checkCarbsNeeded(Curly, lcount):
    #global entries
    global  CarbReqGram, CarbReqTime, lastCOB
    #print('entered "checkCarbsNeeded" in row '+str(lcount)+' with \n'+Curly)
    if isZip:
        wo_apo = Curly.find("\'")
        if wo_apo>0:
            Curly = Curly[:wo_apo-1]+Curly[wo_apo:]
            #print("found \' at position "+str(wo_apo)+"\n" +Curly)
    result = json.loads(Curly)
    stmp = result['deliverAt']                                          # incl milliseconds
    thisTime = ConvertSTRINGooDate(stmp)
    if True:    #thisTime not in entries:
        r_list = {}                                                     # restart with empty list
        reason = result['reason']
        lastCOB= result['COB']
        CarbReqKey            =                   "add'l carbs req w\/in"
        CarbReqTime           = getReason(reason, CarbReqKey,        'm', 0)
        if CarbReqTime == '':
            CarbReqKey        =                   "add'l carbs req w/in"# other spelling
            CarbReqTime       = getReason(reason, CarbReqKey,        'm', 0)
        if CarbReqTime == '':
            CarbReqGram = ''
        else:
            wo_carb = reason.find(CarbReqKey)
            wo_gram = reason[wo_carb-5:].find(' ') + wo_carb-5          # last BLANK before
            CarbReqGram = reason[wo_gram+1:wo_carb-1]
        ##r_list['CarbReqGram'] = CarbReqGram
        #r_list['CarbReqTime'] = CarbReqTime
        #entries[thisTime] = r_list
    #print('leaving "check ..." with', CarbReqGram, 'minutes:', CarbReqTime)
    pass

def basalFromReason(smb, lcount):
    #print(str(smb))
    suggest = smb['openaps']['suggested']
    if 'rate' in suggest :
        rateReq = suggest['rate']
    elif 'TempBasalAbsoluteRate' in  smb['pump']['extended']:
        rateReq = smb['pump']['extended']['TempBasalAbsoluteRate']
    else:
        rateReq = 0         # zero if not explicitely listed
    #print('rateReq in row '+str(lcount)+' from "suggest.json" is ['+str(rateReq)+']')

    return str(rateReq)

def basalFromReasonOnlyold(reason, lcount):
    # the method below is very difficult and still incomplete
    # obviously various programmers followed differnet logic how to declare the new rate    
    if reason.find('no temp required')>1 :
        tempReq = '0'
        tempSource = "no temp required"
    else :
        tempReq = getReason(reason, 'maxSafeBasal:',       ',', 3)
        tempSource = "maxSafeBasal:...,"
    if  tempReq == '':
        tempReq = getReason(reason, 'temp',    '~<', 3)
        tempSource = "temp...~<"
    if  tempReq == '':
        tempReq = getReason(reason, 'temp',    '>~', 3)
        tempSource = "temp...>~"
    if  tempReq == '':
        tempReq = getReason(reason, '<',       'U', 3)
        tempSource = "<...U"
    if  tempReq == '':
        tempReq = getReason(reason, '~ req',   'U', 3)
        tempSource = "~ req...U"
    if  tempReq == '':
        tempReq = getReason(reason, 'temp of', 'U', 3)
        tempSource = "temp of...U"
    if  tempReq == '':
        tempReq = getReason(reason, 'temp',    '<', 3)
        tempSource = "temp...<"
    if tempReq != '':   tempReq = str(round(eval(tempReq),4))
    else : tempReq = '0'
    log_msg('tempReq in row '+str(lcount)+' from "'+tempSource+'" is ['+tempReq+']')
    
    return tempReq

def basalFromReasonOnly(reason, lcount):
    # the method below is very difficult and still incomplete
    # obviously various programmers followed differnet logic how to declare the new rate    
    if reason.find('no temp required')>1 :
        tempReq = '0'
        tempSource = "no temp required"
    else :
        tempReq = getReason(reason, 'maxSafeBasal:',       ',', 3)
        tempSource = "maxSafeBasal:...,"
    if  tempReq == '':
        tempReq = getReason(reason, 'temp',    '~<', 3)
        tempSource = "temp...~<"
    if  tempReq == '':
        tempReq = getReason(reason, 'temp',    '>~', 3)
        tempSource = "temp...>~"
    if  tempReq == '':
        tempReq = getReason(reason, 'm low temp of', 'U', 3)        # near source row 1049
        tempSource = "m low temp of...U"
    if  tempReq == '':
        tempReq = getReason(reason, 'temp of', 'U', 3)
        tempSource = "temp of...U"
    if  tempReq == '':
        tempReq = getReason(reason, 'setting',       'U', 3)
        tempSource = "setting...U"
    if  tempReq == '':
        tempReq = getReason(reason, '<',       'U', 3)
        tempSource = "<...U"
    if  tempReq == '':
        tempReq = getReason(reason, '~ req',   'U', 3)
        tempSource = "~ req...U"
    if  tempReq == '':
        tempReq = getReason(reason, 'temp',    '<', 3)
        tempSource = "temp...<"
    #print('tempReq in row '+str(lcount)+' from "'+tempSource+'" is ['+tempReq+']')
    if tempReq != '':   tempReq = str(round(eval(tempReq),4))
    else : tempReq = '0'
    #print('tempReq in row '+str(lcount)+' from "'+tempSource+'" is ['+tempReq+']')
    
    return tempReq

def basalFromEmulation(returned, lcount):
    #returned = json.loads(reason)
    if 'rate' in returned:
        tempReq = returned['rate']              # soecific basal rate requested
    else:
        tempReq = currenttemp['rate']           # no change, keep current basal rate
    return str(round(tempReq,4))

def setVariant(stmp):
    # set the what-if scenario
    global autosens_data
    global glucose_status
    global bg
    global currenttemp
    global iob_data
    global meal_data
    global profile
    ####################################################################################################################################
    # additional parameters collected here
    # these need an according modification in "determine_basal.py"
    new_parameter = {}
    temp          = {}                                 ### holds interim values in shorter notation
    # first, do the AAPS standard assignments          ### variations are set in the <variant>.dat file
    new_parameter['maxDeltaRatio'] = 0.2               ### additional parameter; AAPS is fix at 0.2
    new_parameter['SMBRatio'] = 0.5                    ### additional parameter; AAPS is fix at 0.5; I use 0.7 as no other rig interferes
    new_parameter['thresholdRatio'] = 0.5              ### additional parameter; AAPS is fix at 0.5; I use 0.6 to lift the minimum 
    new_parameter['maxBolusIOBUsual'] = True           ### additional parameter; AAPS is fix at True, but my basal is too low
    new_parameter['maxBolusIOBRatio'] = 1              ### additional parameter; AAPS is fix at 1, but my basal is too low
    new_parameter['maxBolusTargetRatio'] = 1.001       ### additional parameter; AAPS is fix at 1, bit i saw rounding problems otherwise
    new_parameter['insulinCapBelowTarget'] = False     ### additional parameter; AAPS is fix at False; enable capping below
    new_parameter['CapFactor'] = 0                     ### additional parameter; AAPS is fix at 0; recently I used 4, but try 5
    new_parameter['autoISF_flat'] = False              ### additional parameter; AAPS is fix at False; disable autoISF fpr resistance
    new_parameter['autoISF_slope'] = False             ### additional parameter; AAPS is fix at False; disable autoISF for rise
    new_parameter['autoISF_low'] = False               ### additional parameter; AAPS is fix at False; disable autoISF for lows
    
    ####################################################################################################################################
    STAIR = {}                                                                  # for staircase type functions like basal
    INTERPOL = []                                                               # for linear interpolation between values
    flag_staircase = False
    # read the variations and apply them
    fnam= varLabel + '.dat'
    var = open(varFile, 'r')
    for zeile in var:
        # get array name
        woEndArray  = zeile.find(' ')
        myArray     = zeile[:woEndArray]
        zeile = zeile[woEndArray:]                                              # remaining stuff to be parsed
        while zeile[0] == ' ':              zeile = zeile[1:]                   # truncate leading BLANKS
        woEndItem   = zeile.find(' ')
        myItem      = zeile[:woEndItem]
        zeile = zeile[woEndItem:]                                               # remaining stuff to be parsed
        while zeile[0] == ' ':              zeile = zeile[1:]                   # truncate leading BLANKS
        woEndVal    = zeile.find('###')
        if woEndVal<0 and zeile[-1]=='\n':  woEndVal = len(zeile) - 1           # no trailing comment; drop <CR>
        myVal       = zeile[:woEndVal]
        if myVal != '':
            while myVal[-1] == ' ' :    myVal = myVal[:-1]                      # truncate trailing BLANKS
        #print('['+myArray+'], ['+myItem+'], ['+myVal+']')
       
        woSTAIR = myVal.find('STAIR')
        if woSTAIR >= 0:                                                        # get value from last valid step
            for STEP in STAIR:
                if STEP == stmp:
                    newVal = STAIR[STEP]
                    break
                elif STEP > stmp:
                    break
                newVal = STAIR[STEP]
            myVal = myVal[:woSTAIR] + str(newVal) + myVal[woSTAIR+5:]

        woINTERPOL = myVal.find('INTERPOL')
        if woINTERPOL>= 0:                                                      # get value from last valid step
            (STEP,  sVal)  = INTERPOL[0]                                        # low end tuple
            (STEPt, sValt) = INTERPOL[len(INTERPOL)-1]                          # high end tuple
            if STEP > stmp:                                                     # extrapolate backwards
                (STEPt, sValt) = INTERPOL[1]                                    # second tuple
                lowVal = sVal
                topVal = sValt
                lowTime= ConvertSTRINGooDate(STEP)
                myTime = ConvertSTRINGooDate(stmp)
                topTime= ConvertSTRINGooDate(STEPt)
                newVal = lowVal + (topVal-lowVal)/(topTime-lowTime)*(myTime-lowTime)
            elif STEPt < stmp:                                                  # extrapolate forwards
                (STEP, sVal) = INTERPOL[len(INTERPOL)-2]                        # last but 1 tuple
                lowVal = sVal
                topVal = sValt
                lowTime= ConvertSTRINGooDate(STEP)
                myTime = ConvertSTRINGooDate(stmp)
                topTime= ConvertSTRINGooDate(STEPt)
                newVal = lowVal + (topVal-lowVal)/(topTime-lowTime)*(myTime-lowTime)
            else:                                                               # interpolate inside range
                for i in range(len(INTERPOL)):
                    (STEP, sVal) = INTERPOL[i]
                    if STEP == stmp:
                        newVal = INTERPOL[STEP]
                        break
                    elif STEP > stmp:
                        topVal = sVal
                        lowTime= ConvertSTRINGooDate(lowLabl)
                        myTime = ConvertSTRINGooDate(stmp)
                        topTime= ConvertSTRINGooDate(STEP)
                        newVal = lowVal + (topVal-lowVal)/(topTime-lowTime)*(myTime-lowTime)
                        break
                    lowVal = sVal 
                    lowLabl= STEP
            myVal = myVal[:woINTERPOL] + str(newVal) + myVal[woINTERPOL+8:]

        logmsg = 'appended new entry to'
        validRow = True
        if   myArray == 'autosens_data' :
            if myItem in autosens_data :
                logmsg = 'edited old value of '+str(autosens_data[myItem])+' in'
            autosens_data[myItem] = eval(myVal)
            logres = str(autosens_data[myItem])
        elif myArray == 'glucose_status' :
            if myItem in glucose_status :
                logmsg = 'edited old value of '+str(glucose_status[myItem])+' in'
            glucose_status[myItem] = eval(myVal)
            logres = str(glucose_status[myItem])
        elif myArray == 'currenttemp' :
            if myItem in currenttemp :
                logmsg = 'edited old value of '+str(currenttemp[myItem])+' in'
            currenttemp[myItem] = eval(myVal)
            logres = str(currenttemp[myItem])
        elif myArray == 'iob_data' :
            if myItem in iob_data :
                logmsg = 'edited old value of '+str(iob_data[myItem])+' in'
            iob_data[myItem] = eval(myVal)
            logres = str(iob_data[myItem])
        elif myArray == 'meal_data' :
            if myItem in meal_data :
                logmsg = 'edited old value of '+str(meal_data[myItem])+' in'
            meal_data[myItem] = eval(myVal)
            logres = str(meal_data[myItem])
        elif myArray == 'profile' :
            if myItem in profile :
                logmsg = 'edited old value of '+str(profile[myItem])+' in'
            profile[myItem] = eval(myVal)
            logres = str(profile[myItem])
        elif myArray == 'temp' :
            if myItem in temp :
                logmsg = 'edited old value of '+str(temp[myItem])+' in'
            temp[myItem] = eval(myVal)
            logres = str(temp[myItem])
        elif myArray == 'STAIR' :
            STAIR[myItem] = eval(myVal)
        elif myArray == 'new_parameter' :
            if myItem in new_parameter :
                logmsg = 'edited old value of '+str(new_parameter[myItem])+' in'
            new_parameter[myItem] = eval(myVal)
            logres = str(new_parameter[myItem])
        elif myArray == 'STAIR' :
            STAIR[myItem] = eval(myVal)
        elif myArray == 'INTERPOL' :
            if len(myItem) < 24:                                                # incomplete UTC time label
                oldLen = len(myItem)
                if myItem[oldLen-1:] == 'Z':
                    oldLen += -1
                    myItem = myItem[:-1]
                myItem = myItem + '00:00:00.000Z'[oldLen-11:]
            INTERPOL.append((myItem, eval(myVal)) )
        else:
            validRow = False
    
        if validRow:    varlog.write(logmsg+' '+myArray+' with '+myItem+'='+logres+'\n')
        else:           varlog.write('not actioned: ['+myArray+'], ['+myItem+'], ['+myVal+']'+'\n')
        
    ####################################################################################################################################
    # final clean up
    profile['new_parameter'] = new_parameter                    ### use profile as piggyback to get parameters into determine_basal
    bg[-1] = glucose_status['glucose']                          ### just in case it got changed 
    global emulTarLow
    global emulTarHig
    emulTarLow[-1] = profile['min_bg']                          ### please do not touch
    emulTarHig[-1] = profile['max_bg']                          ### please do not touch
    global emulAs_ratio
    emulAs_ratio.append(autosens_data['ratio']*10)

def getOrigPred(predBGs):
    Fcasts = {}
    for BGs in predBGs:
        Fcasts[BGs] = predBGs[BGs]
    #print ('orig preds --> '+str(Fcasts))
    return Fcasts

def TreatLoop(Curly, log, lcount):
    global SMBreason
    global loop_mills, loop_label
    global origInsReq
    global origSMB, emulSMB
    global origMaxBolus, emulMaxBolus
    global origBasal, lastBasal
    global longDelta, avgDelta, longSlope, rateSlope, glucose_status, emulISF
    global Pred, FlowChart
    #print('\nentered TreatLoop for row '+str(lcount)+' ending with  /'+Curly[-1]+'/ having '+Curly[780:800]+'\n'+Curly)
    wo_apo = Curly.find("\'")
    if wo_apo>0:
        Curly = Curly[:wo_apo-1]+Curly[wo_apo:]
        #print("found \' at position "+str(wo_apo)+"\n" +Curly)
    if not newLoop:                                                 # caught in the middle of a loop
        SMBreason = {}                                              # clear for first filtered debug list
        SMBreason['script'] = '---------- Script Debug --------------------\n'
        return 'MORE'       
    smb = json.loads(Curly)

    if 'openaps' in smb:                                            # otherwise unknown source of entry
        suggest = smb['openaps']['suggested']
        #thisTime = int(round(time.time() * 1000))                  # use as now() or the emulated execution time
        if 'deliverAt' in suggest:
            stmp = suggest['deliverAt']                             # the SMB mode from oref1
        elif 'timestamp' in suggest:
            stmp = suggest['timestamp']                             # the AMA mode 
        else:
            log_msg('no time stamp found in\n' + str(suggest) )
            return 'STOP' 
        if t_startLabel > stmp :                                    # too early
            SMBreason = {}                                          # clear for first filtered debug list
            SMBreason['script'] = '---------- Script Debug --------------------\n'
            return 'MORE'       
        if t_stoppLabel < stmp :            return 'STOP'           # too late; send quit signal
        thisTime = ConvertSTRINGooDate(stmp)
        loop_mills.append(round(thisTime/1000, 1) )                 # from millis to secs
        loop_label.append(stmp[11:19] + stmp[-1])                   # include seconds to distinguish entries
        #print('len loop_mills='+str(len(loop_mills))+'; len labels='+str(len(loop_label)))
        reason = suggest['reason']
        if 'insulinReq' in suggest:
            log.write('\n========== DELTA in row ' + str(lcount) + ' SMB ========== of logfile '+fn+'\n')
            log.write('  created at= ' + smb['created_at'] + '\n')
            log.write(SMBreason['script'])               # the script debug section
            #printVal(suggest, 'bg', log)
            origcob.append(round(suggest['COB'], 1))
            #log.write('  COB   =' + str(cob) + '\n')
            #iob.append(round(suggest['IOB']*10, 1))    # done in iob-data
            key = 'insulinReq'
            ins_Req = suggest[key]
            #log.write('  ' + (key+'    ')[:6] + '=' + str(insReq) + '\n')
            if ins_Req > 0.0:                            # can be empty string; was >0.2 before
                mySMB  = getReason(reason, 'Microbolusing', 'U',  1)
                maxBol = getReason(reason, 'maxBolus',      '. ', 1)
                if len(maxBol) > 5 :
                    maxBol = getReason(reason, 'maxBolus',  '; ', 1)
            else:
                mySMB  = '0'
                maxBol = '0'
        else:
            ins_Req = 0
            mySMB  = '0'
            maxBol = '0'
        if mySMB == '' :    mySMB = '0'
        if maxBol== '' :    maxBol= '0'
        origSMB.append(eval(mySMB))
        origMaxBolus.append(eval(maxBol))
        log.write('---------- Reason --------------------------\n' + str(reason) + '\n')
        tempReq = basalFromReason(smb, lcount)
        origBasal.append(round(eval(tempReq), 4))
        
        # now we can set the remaining iob data section
        #print(str(SMBreason))
        last_temp = {}
        last_temp['typeof'] = 'dummy'                       # may be anything
        last_temp['date']   = thisTime - SMBreason['lastTempAge'] *60*1000   # copy from original logfile
        last_temp['rate']   = currenttemp['rate']
        last_temp['duration'] = currenttemp['duration']
        iob_data['lastTemp']= last_temp
        lastBasal.append(currenttemp['rate'])
        
        log = open(ce_file, 'a')
        log.write('\n========== '+varLabel+' loop in row ' + str(lcount) +' ========== of logfile '+fn+'\n')
        log.write('  created at= ' + stmp[:-5]+stmp[-1] +'\n')
        log.write('---------- Script Debug --------------------\n')
        log.close()
        #tempBasalFunctions = set_tempBasalFunctions()  # look up in profile
        reservoir = 47                                  # currently fixed
        tempBasalFunctionsDummy = ''                    # is handled inside determine_basal as import
        origInsReq.append(ins_Req)
        varlog.write('\nloop execution in row='+str(lcount)+' of logfile '+fn+' at= ' + smb['created_at'] + '\n')
        #longDelta.append(round(glucose_status['long_avgdelta'],2))
        delta05, avg05 = getHistBG(len(bg)-1, 0.05)
        glucose_status['dura05'] = delta05              # for the time being keep name from 1ast attempt
        glucose_status['avg05']   = avg05
        longDelta.append(round(delta05, 2))
        avgDelta.append(round(avg05, 2))
        if delta05<100 or True:                         # no risk of singularity, get linear regression; restriction not needed?
            dura70, slope70, slopes = getSlopeBG(len(bg)-1)
            glucose_status['dura70'] = dura70
            glucose_status['slope70'] = slope70
            longSlope.append(round(dura70, 2))
            rateSlope.append(round(slope70, 2))
            glucose_status['delta05'] = getDeltaBG(slopes, 7.5)
            glucose_status['delta15'] = getDeltaBG(slopes,17.5)
            glucose_status['delta40'] = getDeltaBG(slopes,42.5)
            #print(stmp, str(glucose_status))
            pass
        else:
            longSlope.append(0.0)
            rateSlope.append(0.0)
        Fcasts = getOrigPred(suggest['predBGs'])
        Flows  = []
        setVariant(stmp)
        reT = detSMB.determine_basal(glucose_status, currenttemp, iob_data, profile, autosens_data, meal_data, tempBasalFunctionsDummy, True, reservoir, thisTime, Fcasts, Flows)
        reason = echo_rT(reT)                           # overwrite the original reason
        maxBolStr = getReason(reason, 'maxBolus', '. ', 1)
        if len(maxBolStr) > 5 :
            maxBolStr = getReason(reason, 'maxBolus',  '; ', 1)
        if maxBolStr == '' :     maxBolStr = '0'
        emulMaxBolus.append(eval(maxBolStr))
        mySMBstr = getReason(reason, 'Microbolusing', 'U',  1)
        if mySMBstr == '' :     mySMBstr = '0'
        emulSMB.append(eval(mySMBstr))
        emulISF.append(Fcasts['emulISF'])               # was set in determine_basal.py

        if reason.find('COB: 0,') == 0: 
            Fcasts['COBpredBGs'] = []                   # clear array if COB=0
        Pred[round(thisTime/1000,1)] = Fcasts
        FlowChart[round(thisTime/1000,1)] = Flows
        #print(str(FlowChart))
        #next loop execution
        SMBreason = {}                                  # clear for next debug list
        SMBreason['script'] = '---------- Script Debug --------------------\n'
        return 'MORE'

def code_error(lcount, mess):
    # RhinoException encountered
    SMBreason['script'] += 'logfile row '+str(lcount)+'\n'+mess
    if isZip:       SMBreason['script'] += '\n'
    SMBreason['script'] += '---------- Script Debug --------------------\n'
    newLoop = False
    return 'MORE'       
        
def PrepareSMB(zeile, log, lcount):
    if not newLoop: return
    # collect SMB detail echos before actual, compacted loop protocol comes
    global SMBreason
    key_str = '[LoggerCallback.jsFunction_log():39]'
    what_anf = zeile.find(key_str)
    what = zeile[what_anf+len(key_str)+2:]
    if isZip:       what += '\n'
    SMBreason['script'] += what
    if what.find('SMB enabled')==0:
        SMBreason['rowON'] = lcount
        SMBreason['whyON'] = what[:-1]
    elif what.find('disabling SMB')>0:
        SMBreason['rowOFF'] = lcount
        SMBreason['whyOFF'] = what[:-1]
    elif what.find('maxBolus: ')>0:
        SMBreason['maxSMB'] = what[-4:-1]
    elif what.find('gz maximSMB: from ')==0:
        SMBreason['maxBolus'] = what[:-1]
    elif what.find('currenttemp:')==0:                  # unclear source of TempAge, but should be the same in emulation
        wo_anf = what.find('lastTempAge:')
        wo_end = what.find(' m tempModulus:')
        SMBreason['lastTempAge'] = eval(what[wo_anf+13:wo_end])

def featured(Option):
    # check whethter this feature was in the option list passed from OO.odb
    # or if ALL option were enabled
    # otherwise FALSE
    OK = 'All' in doit  or Option in doit
    if '-'+Option in doit:        OK = False            # explicitly excluded
    return OK

def get_glucose_status(lcount, st) :                    # key = 80
    Curly = st[16:]
    global glucose_status
    global bg
    global newLoop
    newLoop = True
    #print('entered glucose_status for row '+str(lcount)+' with\n'+Curly)
    glucose_status = json.loads(Curly)
    glucose_status['row'] = lcount
    if len(bg)==len(loop_mills) :
        bg.append(glucose_status['glucose'])            # start next iteration
    else:
        bg[-1] = (glucose_status['glucose'])            # overwrite as last loop was not finished
    #print ('\nbg data found in row '+str(lcount)+', total count='+str(len(bg))
    pass

def get_iob_data(lcount, st, log) :                     # key = 81
    if not newLoop: return
    if isZip:
        Curly = st[16:]                                 # zip format: dropped the <LF> earlier
    else:
        Curly = st[16:-1]                               # drop the <CRLF>
    global iob_data
    global activity
    iob_array = json.loads(Curly)
    iob_data = {}
    iob_data['typeof']  = 'dummy'                       # may be anything
    # get first record as current iob
    rec_0 = iob_array[0]
    for ele in rec_0 :
        if ele != 'iobWithZeroTemp':        iob_data[ele] = rec_0[ele]
        if ele == 'iob':
            act = rec_0[ele]
            if len(origiob) ==len(loop_mills):
                origiob.append(act*10)
            else:
                origiob[-1] = (act*10)
        if ele == 'activity':
            act = rec_0[ele]
            if len(activity) ==len(loop_mills):
                activity.append(act*1000)
            else:
                activity[-1] = (act*1000)
            
    iob_data['iobArray']= iob_array
    #print ('preliminary iob data json -->       '+str(lcount) +' : '+ str(iob_data))
    #for ele in iob_array:
    #    log.write(str(ele)+':'+'\n')
    #print ('iob data found in row '+str(lcount)+', total count='+str(len(iob_data)))
    pass

def get_currenttemp(lcount, st) :                       # key = 82
    if not newLoop: return
    Curly = st[16:]
    global currenttemp
    currenttemp = json.loads(Curly)
    currenttemp["typeof"] ="dummy"                      # may be anything
    currenttemp["row"] = lcount
    #print ('currenttemp json -->    '+str(currenttemp))
    pass

def get_profile(lcount, st) :                           # key = 83
    if not newLoop: return
    Curly = st[16:]
    global profile, origISF
    global origTarLow, origTarHig, emulTarLow, emulTarHig
    profile = json.loads(Curly)
    #profile['maxDeltaRatio'] = 0.2                     ### moved to new_parameter: additional parameter; define standard
    profile['row'] = lcount
    # unknown source, use apparent default:
    profile['remainingCarbsFraction'] = 1
    #profile['temptargetSet'] = True                    # historical logfiles say FALSE             !!!!!!!!!!!!!!!!
    profile['sensitivity_raises_target'] = False        # missing from historical logfiles          !!!!!!!!!!!!!!!!
    if len(origTarLow)==len(loop_mills) :               # start next iteration
        origTarLow.append(profile['min_bg'])
        emulTarLow.append(origTarLow[-1])
        origTarHig.append(profile['max_bg'])
        emulTarHig.append(origTarHig[-1])
        origISF.append(profile['sens'])
    else:                                               # overwrite as last loop was not finished
        origTarLow[-1] = profile['min_bg']
        emulTarLow[-1] = origTarLow[-1]
        origTarHig[-1] = profile['max_bg']
        emulTarHig[-1] = origTarHig[-1]
        origISF[-1]    = profile['sens']
    #print ('master profile json in row '+str(lcount)+' --> '+str(profile))
    #print ('target data found in row '+str(lcount)+', total count origTarLow='+str(len(origTarLow)))
    #print ('target data found in row '+str(lcount)+', total count emulTarLow='+str(len(origTarLow)))
    pass

def get_meal_data(lcount, st) :                         # key = 84
    if not newLoop: return
    Curly = st[16:]
    global meal_data
    meal_data = json.loads(Curly)
    meal_data['row'] = lcount
    # use fixed settings for the time being ...
    meal_data['bwCarbs'] = False                        # bolus wizzard carbs
    meal_data['bwFound'] = False                        # bolus wizzard used ?
    #print ('meal data json -->      '+str(meal_data))
    pass

def get_autosens_data(lcount, st) :                     # key = 86
    if not newLoop: return
    Curly = st[16:]
    global autosens_data, profile
    global origAs_ratio, autoISF
    autosens_data = json.loads(Curly)
    autosens_data['typeof'] = 'dummy'                   # may be anything
    autosens_data['row'] = lcount
    if len(origAs_ratio) ==len(loop_mills) :
        origAs_ratio.append(autosens_data['ratio']*10)
        autoISF.append(profile['sens'] / autosens_data['ratio'])    # ISF assigned now as autoense is the last data block
    else:
        origAs_ratio[-1] = (autosens_data['ratio']*10)
        autoISF[-1] = (profile['sens'] / autosens_data['ratio'])    # ISF assigned now as autoense is the last data block
    pass

def ConvertSTRINGooDate(stmp) :
    # stmp is datetime string incl millis, i.e. like "2019-05-22T12:06:48.091Z"
    if stmp < "2019-10-27T03:00:00.000Z":
        dlst = 3600                                 #    dlst period summer 2019
    elif stmp < "2020-03-29T02:00:00.000Z":
        dlst = 0                                    # no dlst period winter 2019/20
    else:
        dlst = 3600                                 #    dlst period summer 2020
    MSJahr		= eval(    stmp[ 0:4])
    MSMonat		= eval('1'+stmp[ 5:7]) -100
    MSTag		= eval('1'+stmp[ 8:10])-100
    MSStunde	= eval('1'+stmp[11:13])-100
    MSMinute	= eval('1'+stmp[14:16])-100
    MSSekunde	= eval('1'+stmp[17:19])-100
    if len(stmp)>20:
        MSmillis = eval('1'+stmp[20:23])-1000   # for SMB mode
    else:               
        MSmillis = 0                            # in AMA mode there are no millis
    #print ('aus', stmp, ' wird', str(MSJahr), str(MSMonat), str(MSTag), str(MSStunde), str(MSMinute), str(MSSekunde), str(MSmillis))
    NumericDate= datetime.datetime(MSJahr, MSMonat, MSTag, MSStunde, MSMinute, MSSekunde, MSmillis*1000)
    #imestamp = NumericDate.replace(tzinfo=timezone.utc).timestamp() + 3600 # 1h MEZ offset
    #print('entered Convert.. with stmp='+stmp+'\n  NumericDate='+str(NumericDate))
    timestamp = int( (NumericDate.timestamp() + 3600 + dlst) * 1000 )       # 1h MEZ offset
    #print('  timestamp='+str(timestamp))
    #print("Eingang: " + stmp + "\nAusgang: " + str(timestamp) )
    return timestamp

def scanLogfile(fn, entries):
    global SMBreason
    global xyf
    global fn_base                              # keep first match in case of wild card file list
    global log
    global varlog
    global newLoop
    global dataType_offset
    global  CarbReqGram,  CarbReqTime, lastCOB
    
    if not newLoop:                             # otherwise continued from provious logfile
        SMBreason = {}
        SMBreason['script'] = '---------- Script Debug --------------------\n'
        dataType_offset = 1                     #################### used for V2.6.1
    if filecount == 0 :                         # initalize file loop
        fn_base =      fn + '.' + varLabel
        xyf     = open(fn + '.' + varLabel + '.tab', 'w')
        varlog  = open(fn + '.' + varLabel + '.log', 'w')
        log     = open(fn + '.orig.txt', 'w')
    varlog.write('\n========== Echo of what-if definitions actioned for variant '+varLabel+'\n========== created on '+formatdate(localtime=True) + '\n========== for loop events found in logfile '+fn+'\n')
    log.write('AAPS scan from AAPS Logfile for SMB comparison created on ' + formatdate(localtime=True) + '\n')
    log.write('FILE='+fn + '\n')
    key_251 = '[DetermineBasalAdapterSMBJS.invoke():144]: Result:'                  # V2.5x  flag for Result record
    key_261 = '[DetermineBasalAdapterSMBJS.invoke():145]: Result:'                  # V2.6.1 flag for Result record
    global lcount
    #isZip = True    # testwise fix
    lcount  = 0
    if isZip:
        with zipfile.ZipFile(fn) as z:
            for filename in z.namelist():
                lf = z.open(filename)                               # has only 1 member file
    else:
        lf = open(fn, 'r')
    #lf = open(fn, 'r')
    notEOF = True                               # needed because "for zeile in lf" does not work with AAPS 2.5
    
    cont = 'MORE'                               # in case nothing found
    while notEOF:                               # needed because "for zeile in lf" does not work with AAPS 2.5
        try:                                    # needed because "for zeile in lf" does not work with AAPS 2.5
            zeile = lf.readline()               # needed because "for zeile in lf" does not work with AAPS 2.5
            if isZip:   zeile = str(zeile)[2:-3]# strip off the "'b....'\n" remaining from the bytes to str conversion
            if zeile == '':                     # needed because "for zeile in lf" does not work with AAPS 2.5
                notEOF = False                  # needed because "for zeile in lf" does not work with AAPS 2.5
                break                           # needed because "for zeile in lf" does not work with AAPS 2.5
            lcount +=  1
            #print(zeile)
            if lcount>100000:  
                print('no end found at row '+str(lcount)+ ' reading /'+zeile+'/')
                return 'STOP'
            if len(zeile)>13:
                headerKey = zeile[2] + zeile[5] + zeile[8] + zeile[12]
                if headerKey == '::. ':
                    sLine = zeile[13:]
                    Action = hole(sLine, 0, '[', ']')
                    sOffset = len(Action)
                    Block2 = hole(sLine, 1+sOffset, '[', ']')
                    if Block2 == '[DataService.onHandleIntent():54]' \
                    or Block2 == '[DataService.onHandleIntent():55]':       # token :54 added for AAPS version 2.5
                        pass
                    elif Block2[:-3] == '[DetermineBasalAdapterAMAJS.invoke():':  # various input items for loop
                        log_msg('\nSorry, this tool is currently only available for SMB\n')
                        return 'STOP'
                    elif Block2[:-4] == '[DetermineBasalAdapterSMBJS.invoke():':  # various input items for loop
                        dataStr = sLine[sLine.find(']: ')+3:]
                        if dataStr.find('RhinoException:')>-1:          code_error(lcount, dataStr)
                        else:
                            was_loop_251 = zeile.find(key_251)
                            was_loop_261 = zeile.find(key_261)
                            was_loop = max(was_loop_251, was_loop_261)
                            if was_loop>-2:
                                checkCarbsNeeded(dataStr[8:], lcount)
                                #print('returned to scanLogfile:', CarbReqGram, 'when:', CarbReqTime)
                    elif Block2[:-3] == '[DetermineBasalAdapterSMBJS.invoke():':  # various input items for loop
                        dataStr = sLine[sLine.find(']: ')+3:]
                        dataType = eval(Block2[len(Block2)-3:-1])           # extract last 2 digits as type key
                        # beware: these datraType differs for AMA mode with glucose at 70
                        if   dataType == 79 :                               # start counter in V2.5.1 only
                            dataType_offset = 0                             #################### used for V2.5.1
                        elif dataType == dataType_offset+80 :               get_glucose_status(lcount, dataStr)
                        elif dataType == dataType_offset+81 :               get_iob_data(lcount, dataStr, log)
                        elif dataType == dataType_offset+82 :               get_currenttemp(lcount, dataStr)
                        elif dataType == dataType_offset+83 :               get_profile(lcount, dataStr)
                        elif dataType == dataType_offset+84 :               get_meal_data(lcount, dataStr)
                        elif dataType == dataType_offset+86 :               get_autosens_data(lcount, dataStr)
                    elif Block2 == '[LoggerCallback.jsFunction_log():39]':  # script debug info from console.error
                        PrepareSMB(sLine, log, lcount)   
                    elif Block2 == '[DbLogger.dbAdd():29]':                 ################## flag for V2.5.1
                        Curly =  hole(sLine, 1+sOffset+len(Block2), '{', '}')
                        #print('calling TreatLoop in row '+str(lcount)+' with\n'+Curly)
                        if Curly.find('{"device":"openaps:')==0:   
                            cont = TreatLoop(Curly, log, lcount)
                            if cont == 'STOP' :     return cont
                elif zeile.find('data:{"device":"openaps:') == 0 :          ################## flag for V2.6.1
                    Curly =  hole(zeile, 5, '{', '}')
                    #print('calling TreatLoop in row '+str(lcount)+' with\n'+Curly)
                    if Curly.find('{"device":"openaps:')==0 and Curly.find('"openaps":{"suggested":{')>0 :   
                        cont = TreatLoop(Curly, log, lcount)
                        if cont == 'STOP' :     return cont

        except UnicodeDecodeError:              # needed because "for zeile in lf" does not work with AAPS 2.5 containing non-printing ASCII codes
            lcount +=  1                        # skip this line, it contains non-ASCII characters!
            
    lf.close()
    return cont

def echo_rT(reT):                                       # echo the unusual SMB result
    global emulInsReq
    global emulBasal
    log = open(ce_file, 'a')
    #log.write ('\nreT --> '+str(reT)+'\n')
    
    if 'error' in reT :
        log_msg ('returned "error" with ...\n  ' + reT['error'])
        reason = reT['error']
    elif 'setTempBasal' in reT:                         # normal finish
        sub_names = ['rate', 'duration', 'profile', 'rT', 'currenttemp']
        ele = reT['setTempBasal']
        reason = ele[3]['reason']
        log.write('---------- Reason --------------------------\n' + str(reason) + '\n')
        emulInsReq.append(ele[3]['insulinReq'])
        emulBasal.append(max(0,ele[0]))
    elif 'reason' in reT:                               # normal finish
        reason = reT['reason']
        log.write('---------- Reason --------------------------\n' + str(reason) + '\n')
        emulInsReq.append(reT['insulinReq'])
        tempReq = basalFromEmulation(reT, lcount)
        emulBasal.append(eval(tempReq))
    else :
        log_msg ('returned "unexpected content" with ...\n  ' + str(reT))
        reason = str(reT)

    log.close()
    return reason

def BGValPlot(ax, BGcount, BGtype, BGlevel, BGedge, BGcol):
    if BGlevel+len(BGtype)/2 > 30:                                      # otherwise BG axis scale gets funny
        BGarrow = dict(arrowstyle='-', fc=BGcol, ec=BGcol, linestyle='dotted')
        posBG   = (BGlevel, BGedge+2000+400*BGcount)                    # vertical position of BG name
        posLine = (BGlevel, BGedge+   0)                                # vertical pos of fcast block
        ax.annotate(BGtype, xy=posLine, xytext=posBG, ha='center',
                            arrowprops=BGarrow, color=BGcol)

def AdrPlot(ax, ele, row, drow, col, dchar):            # add source row number above top left
    if 'adr' in ele: 
        ax.annotate(ele['adr'], xy=(col-dchar*0.31-1, row+drow*3.5+2), fontsize=5)

def getBoxSize(title):                                  # rows and width for flowchart box
    tx = title
    #dchar = tx.find('\n')
    #if dchar < 1:      dchar = len(title)
    dchar = 1
    drow = 1
    #print('--------------------------------------\n'+tx+'\n has initial size('+str(dchar)+','+str(drow)+')')
    #tx = tx[dchar+1:]
    while tx.find('\n')>0:                                              # get count of chars and rows
        drow += 1
        eol = tx.find('\n')
        if eol>dchar:       dchar = eol
        tx = tx[eol+1:]
        #print(' has interim size('+str(dchar)+','+str(drow)+')')
    eol = len(tx)
    if eol>dchar:       dchar = eol
    #print('   has final size('+str(dchar)+','+str(drow)+')')
    return dchar, drow

def getHistBG(iFrame, bw):
    #if iFrame == 0 :       return 0.0, round(bg[iFrame]+0.01,1)
    sumBG = 0
    oldavg= bg[iFrame]
    #bw = 0.05
    for i in range(iFrame, -1, -1):
        if bg[i]>oldavg*(1-bw) and bg[i]<oldavg*(1+bw) :          # still in previous bw ratio range
            sumBG += bg[i]
            oldavg = sumBG / (iFrame-i+1)
            #if iFrame<5:        print ('use', loop_label[i], str(oldavg), str(bg[i]))
        else:
            #if iFrame<5:        print ('break at step', str(i))
            i += 1
            break
    duramins = ( loop_mills[iFrame] - loop_mills[i] ) / 60
    #if iFrame<5:        print ( 'end at step', str(i), str(duramins), str(oldavg))
    return round(duramins,0), round(oldavg,1)

def getDeltaBG(slopes, duration):
    # return the slope just below "duration" for one oof 5, 15 or 40 min deltas
    for i in slopes:
        if slopes[i]['dur'] >= duration:
            if i+1 in slopes:
                use = i+1                   # use last value before
            else:
                use = i                     # only one entry, use it
            slop = slopes[use]['b'] * 5*60  # BG increment per 5 minutes
            return round(slop, 2)
    if len(slopes)>0:
        slop = slopes[i]['b'] * 5*60        # BG increment per 5 minutes
        return round(slop, 2)               # use last fit from record i
    else:
        return 0                            # e.g. less than 3 BG values; same as in GlucoseStatus.java

def getSlopeBG(iFrame):
    # linerar regression analysis after 
    # http://www.carl-engler-schule.de/culm/culm/culm2/th_messdaten/mdv2/auszug_ausgleichsgerade.pdf
    if iFrame < 2:         return 0,0, {}   # first 2 points make a trivial line

    corrMin = 0.70                          # go backwards until the correlation coefficient goes below
    sumBG   = 0                             # y
    sumt    = 0                             # x
    sumBG2  = 0                             # y^2
    sumt2   = 0                             # x^2
    sumxy   = 0                             # x*y-axis
    slopes  = {}
    #t = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10] # test data for x
    #bg= [2, 1, 3, 3, 5, 4, 7, 5, 6, 6,  8] # test data for y=a + x*b
    corrMax = 0
    for i in range(iFrame, -1, -1):
        sumt    += loop_mills[i]
        sumt2   += pow(loop_mills[i], 2)
        sumBG   += bg[i]
        sumBG2  += pow(bg[i], 2)
        sumxy   += loop_mills[i] * bg[i]
        n = iFrame - i + 1
        dividend = n*sumxy - sumt*sumBG
        if (n*sumt2 - pow(sumt,2)) * (n*sumBG2 - pow(sumBG,2)) != 0:    # otherwise DIV ZERO in r_sq
            r_sq    = pow(dividend,2) / abs( (n*sumt2 - pow(sumt,2)) * (n*sumBG2 - pow(sumBG,2)) )
            dur     =(loop_mills[iFrame]-loop_mills[i])/60
            if r_sq < corrMin and dur>42.5:      break  # correlation too bad

            b       = dividend / (n*sumt2 - pow(sumt,2))
            a       = ( sumBG - b*sumt) / n
            if i<iFrame-1:      
                slopePar = dict(n=n-1, a=a, b=b, corr=r_sq, dur=dur)
                if r_sq>corrMax:
                    corrMax = r_sq
                    iMax = i
                    dura70  = ( loop_mills[iFrame] - loop_mills[i] ) / 60
                    slope70 = b * 5 * 60       # 5 minute slope at best correlation
                slopes[i] = slopePar
            #print ('some fit', str(n-1), str(b), str(a),str(r_sq))
    if corrMax == 0:         return 0,0, slopes   # no good correlation found
    #print('found these deltas')
    #for i in slopes:    print(str(i), str(slopes[i]))
    #print('selected deltas are', str(getDeltaBG(slopes,7.5)), str(getDeltaBG(slopes,17.5)), str(getDeltaBG(slopes,42.5)))
    return round(dura70,0), round(slope70,1), slopes
    
def populateColumn(tLast, array, weight, iFirst, loopCount):
    # e.g.  tLast = f'target      {emulTarHig[iLast]:>6}'
    for col in range(loopCount-2, iFirst, -1) :
        val = array[col] * weight
        if weight != 1:     val = round(val,2)          # was autosense
        tLast += f'{val:>10}'
    return tLast
    
def XYplots(loopCount) :
    import matplotlib.pyplot as plt
    from matplotlib.animation import FFMpegWriter
    from matplotlib.backends.backend_pdf import PdfPages
    # ---   ensure that last loop was finished  -------------
    if len(loop_mills) < len(bg)            :   bg.pop()
    if len(loop_mills) < len(origTarLow)    :   origTarLow.pop()
    if len(loop_mills) < len(origTarHig)    :   origTarHig.pop()
    if len(loop_mills) < len(origInsReq)    :   origInsReq.pop()
    if len(loop_mills) < len(origMaxBolus)  :   origMaxBolus.pop()
    if len(loop_mills) < len(origSMB)       :   origSMB.pop()
    if len(loop_mills) < len(origBasal)     :   origBasal.pop()
    if len(loop_mills) < len(longDelta)     :   longDelta.pop()
    if len(loop_mills) < len(avgDelta)      :   avgDelta.pop()
    if len(loop_mills) < len(longSlope)     :   longSlope.pop()
    if len(loop_mills) < len(rateSlope)     :   rateSlope.pop()
    if len(loop_mills) < len(origISF)       :   origISF.pop()
    if len(loop_mills) < len(autoISF)       :   autoISF.pop()
    if len(loop_mills) < len(emulISF)       :   emulISF.pop()
    
    if len(loop_mills) < len(emulTarLow)    :   emulTarLow.pop()
    if len(loop_mills) < len(emulTarHig)    :   emulTarHig.pop()
    if len(loop_mills) < len(emulInsReq)    :   emulInsReq.pop()
    if len(loop_mills) < len(emulMaxBolus)  :   emulMaxBolus.pop()
    if len(loop_mills) < len(emulSMB)       :   emulSMB.pop()
    if len(loop_mills) < len(emulBasal)     :   emulBasal.pop()
    
    if len(loop_mills) < len(origcob)       :   origcob.pop()
    if len(loop_mills) < len(origiob)       :   origiob.pop()
    if len(loop_mills) < len(origAs_ratio)  :   origAs_ratio.pop()
    if len(loop_mills) < len(emulAs_ratio)  :   emulAs_ratio.pop()
    if len(loop_mills) < len(activity)      :   activity.pop()

    # ---   complete the curves to close the polygon for area fill
    cob_area = []
    iob_area = []
    looparea = []
    cob_area.append(0)                      # top left corner
    iob_area.append(0)                      # top left corner
    looparea.append(loop_mills[0])
    i = 0
    for lopmil in loop_mills:
        cob_area.append(origcob[i])             # the regular data
        iob_area.append(origiob[i])             # the regular data
        looparea.append(lopmil)
        i += 1
    cob_area.append(0)                      # bottom left corner
    iob_area.append(0)                      # bottom left corner
    looparea.append(loop_mills[-1])
    cob_area.append(0)                      #  close polygon at top left corner
    iob_area.append(0)                      #  close polygon at top left corner
    looparea.append(loop_mills[0])
        
    # ---   plot the comparisons    -------------------------
    if loopCount <= 30 :                                                                # step size for y-axis (time)
        yStep = 3       # every 15 minutes
    elif loopCount <=60:
        yStep = 6       # every 30 minutes#
    else :
        yStep = 12      # every 60 minutes#
    yTicks = []
    yLabels= []
    
    for i in range(0, loopCount, yStep) :                                               # the time labels
        yTicks.append(loop_mills[i])
        yLabels.append(loop_label[i])
    if loop_mills[-1] != yTicks[-1]:
        yTicks.append(loop_mills[-1])                                                   # last tick could be missed out
        yLabels.append(loop_label[-1])
    if featured('pred'):                                                                # extend time axis for predictions
        for i in range(30, 241, 30):
            yTicks.append(loop_mills[-1]+i*60)                                          # append 4 hours
            yLabels.append('+'+str(i)+'mins')
        maxframes = len(loop_mills)
    else:
        maxframes = 1
    thickness = (loop_mills[-1]-loop_mills[0])/loopCount/4

    maxPlots = 0
    frameIns = featured('insReq') or featured('maxBolus') or featured('SMB') or featured('basal')
    if frameIns :                                                                       # we need frame for insulin type graph(s)
        maxPlots += 1
    frameBG = featured('bg') or featured('target') or featured('pred') or featured('as ratio') or featured ('cob') or featured('iob') or featured('activity')
    if frameBG :                                                                        # we need frame for bg type graph(s)
        bgOffset = maxPlots
        maxPlots += 2
    frameFlow = featured('flowchart')
    if frameFlow :                                                                      # we need frame for decision flow chart
        flowOffset = maxPlots
        maxPlots += 6
    plt.rcParams['savefig.dpi'] = 200
    #lt.rcParams['figure.figsize'] = (9, 18) #6*maxPlots)                               # h,w in inches
    plt.rcParams['figure.dpi'] = 200
    plt.rcParams['legend.fontsize'] = 'small'
    plt.rcParams['legend.facecolor'] = 'grey'
    plt.rcParams['font.size'] = 8
    colFav = {'bg':'red', 'ZT':'cyan', 'IOB':'blue', 'COB':'orange', 'UAM':'brown'}
    bbox = dict(boxstyle="round", fc="0.8")
    flowForward = dict(arrowstyle='<|-')                                                 # points to current box

    log_msg('Emulation finished; generating graphics pages\n')
    pdfFile = fn_first + '.' + varLabel + '.pdf'
    pdfCleared = False
    while True:                                                                         # wait if old pdf is still loaded in pdf viewer
        try:
            os.remove(pdfFile)
            if pdfCleared:    log_msg('continuing ...')
            break
        except PermissionError:
            asleep = 10
            log_msg('Your graphics file seems blocked by other process. Checking again in '+str(asleep)+' sec.'+chr(7)) # sometimes I can hear that BELL
            time.sleep(asleep)
            pdfCleared=True
        except FileNotFoundError:
            break
    xyf = open(fn_base + '.tab', 'r')
    zeile = xyf.readline()                   # header row 1
    log_msg(zeile[:-1])
    zeile = xyf.readline()                   # header row 2
    log_msg(zeile[:-1])

    with PdfPages(pdfFile) as pdf:
        for iFrame in range(0, maxframes):                                              # the loop instances
            zeile = xyf.readline()                                                      # table row 
            log_msg(zeile[:-1])                                                         # print it as heart beat
            #fig, axes = plt.subplots(1, maxPlots, constrained_layout=True, figsize=(9, 15)) #6*maxPlots)  )          
            fig = plt.figure(constrained_layout=True, figsize=(2.2*max(6,maxPlots), 11))# w, h paper size in inches; double width if no flowchart
            gs  = fig.add_gridspec(1,maxPlots)                                          # 1 horizontal; 1+2+6 vertical strips
            fig.set_constrained_layout_pads(w_pad=0., h_pad=0., hspace=0., wspace=0.)   # space to edge and between frames
            fig.suptitle('\nCompare original "' + fn + '" vs emulation case "' + varLabel + '"\n', weight='bold')    # incl. <CR> for space below Headeer
            if frameIns :                                                               # anything related to insulin
                axin = fig.add_subplot(gs[0,0])                                         # 1 strip wide
                axin.xaxis.label.set_color('blue')
                axin.tick_params(axis='x', colors='blue')
                axin.set_xlabel('Insulin', weight='bold')
                if featured('pred'):
                    axin.set_ylim(loop_mills[-1]+thickness*2+48*5*60+45*60, loop_mills[0]-thickness*2)    # add thickness*2 so markers fit into plot frame + 45min space for BG labels
                else:
                    axin.set_ylim(loop_mills[-1]+thickness*2, loop_mills[0]-thickness*2)    # add thickness*2 so markers fit into plot frame
                axin.set_yticks(yTicks)
                axin.set_yticklabels(yLabels)

                if featured('insReq') :
                    axin.plot(emulInsReq, loop_mills, linestyle='None',  marker='o', color='red',   label='insulin Req, emulated')
                    axin.plot(origInsReq, loop_mills, linestyle='solid', marker='.', color='orange',label='insulin Req, original')
                if featured('maxBolus') :
                    axin.plot(emulMaxBolus,loop_mills,linestyle='None',  marker='o', color='green', label='maxBolus, emulated')
                    axin.plot(origMaxBolus,loop_mills,linestyle='solid',             color='green', label='maxBolus, orig')
                if featured('SMB') :
                    axin.plot(emulSMB,    loop_mills, linestyle='None',  marker='o', color='black', label='SMB, emulated')
                    axin.plot(origSMB,    loop_mills, linestyle='solid', marker='.', color='yellow',label='SMB, original')
                if featured('basal') :
                    axin.barh(y=loop_mills, height=thickness*2, width=emulBasal,     color='white', label='tempBasal, emulated', edgecolor='blue')
                    axin.barh(y=loop_mills, height=thickness  , width=origBasal,     color='blue',  label='tempBasal, original')

                #axin.plot([0,0], [loop_mills[0],loop_mills[-1]], linestyle='dotted', color='black')  # grid line for insulin=0                
                axin.legend(loc='lower right')
                
            if frameBG :                                                                # anything related to glucose
                axbg = fig.add_subplot(gs[0, bgOffset:bgOffset+2])                      # 2 strips wide
                axbg.xaxis.label.set_color('red')
                axbg.tick_params(axis='x', colors='red')
                axbg.set_xlabel('....IOB.....Autosense.....COB...           Glucose', weight='bold')
                if frameIns:                                                            # already annotated in insulin frame
                    axbg.set_yticklabels(['',''])                                       # dummy axis labels
                    axbg.set_yticks([-1,9e99])                                          # off scale to suppress ticks
                else:                                                                   # not yet annotated in insulin frame
                    axbg.set_yticks(yTicks)
                    axbg.set_yticklabels(yLabels)
                axbg.set_ylim(loop_mills[-1]+thickness*2, loop_mills[0]-thickness*2)

                if featured('target') :                                                 # plot targets
                    axbg.plot(emulTarHig, loop_mills, linestyle='None',   marker='o', color='black',  label='target high, emulated')
                    axbg.plot(emulTarLow, loop_mills, linestyle='None',   marker='o', color='black',  label='target  low, emulated')
                    axbg.plot(origTarHig, loop_mills, linestyle='dashed', marker='.', color='yellow', label='target high, original')
                    axbg.plot(origTarLow, loop_mills, linestyle='dashed', marker='.', color='yellow', label='target  low, original')

                if featured('bg') :                                                     # plot bg
                    axbg.plot(bg,         loop_mills, linestyle='solid',  marker='o', color='red',    label='blood glucose')
                    dura05, avg05 = getHistBG(iFrame, 0.05)                             # mins in 5% band
                    bg_min = avg05 * (1-0.05)
                    bg_max = avg05 * (1+0.05)
                    minmills = loop_mills[iFrame] - dura05 * 60
                    if dura05>1:
                        axbg.fill_between([bg_min,bg_max], minmills-2*thickness, loop_mills[iFrame]+2*thickness, fc='red', alpha=0.25)
                    dura10, avg10 = getHistBG(iFrame, 0.10)                             # mins in 10% band
                    bg_min = avg10 * (1-0.10)
                    bg_max = avg10 * (1+0.10)
                    minmills = loop_mills[iFrame] - dura10 * 60
                    if dura10>1:
                        axbg.fill_between([bg_min,bg_max], minmills-2*thickness, loop_mills[iFrame]+2*thickness, fc='red', alpha=0.1)
                    if iFrame>1:                                                        # show fit(s)
                        dura70, slope70, slopes = getSlopeBG(iFrame)
                        corrMax = 0
                        for i in slopes:
                            #print ('iFrame', str(iFrame), ' mit', str(i), 'hat', str(slopes[i]))
                            a = slopes[i]['a']
                            b = slopes[i]['b']
                            t1= loop_mills[i]
                            t2= loop_mills[iFrame]
                            b1= b*t1+a
                            b2= b*t2+a
                            axbg.plot([b1,b2], [t1,t2], linestyle='dotted', marker='*', color='#c0c0c0')#all the fits
                            r_sq = slopes[i]['corr']
                            if r_sq>corrMax:
                                corrMax = r_sq
                                iMax = i
                        if corrMax > 0:
                            i = iMax                                                    # index of best fit
                            a = slopes[i]['a']
                            b = slopes[i]['b']
                            t1= loop_mills[i]
                            t2= loop_mills[iFrame]
                            b1= b*t1+a
                            b2= b*t2+a
                            axbg.plot([b1,b2], [t1,t2], linestyle='dotted', marker='*', color='black', label='regression fit')   #best fit
                        
                if featured('as ratio') :                                               # plot autosense ratio
                    axbg.plot([10,10],[loop_mills[0],loop_mills[-1]],linestyle='dotted',color='black',label='Autosense(x10) OFF')
                    axbg.plot(origAs_ratio,loop_mills,linestyle='solid',  marker='.',   color='black',label='Autosense(x10), original')
                    axbg.plot(emulAs_ratio,loop_mills,linestyle='none',   marker='o',   color='black',label='Autosense(x10), emulated')

                if featured('ISF') :                                                    # plot ISF
                    axbg.plot(emulISF,loop_mills,linestyle='none',   marker='o',    color='#007000',label='ISF, emulated')
                    axbg.plot(autoISF,loop_mills,linestyle='dashed', marker='.',    color='#009000',label='ISF, autosensed')
                    axbg.plot(origISF,loop_mills,linestyle='dotted', marker='.',    color='#00FF00',label='ISF, original')

                if featured('activity') :                                               # plot activity
                    axbg.plot(activity, loop_mills, linestyle='solid',              color='yellow', label='Activity(x1000)')

                if featured('iob') :                                                    # plot IOB
                    axbg.plot(origiob,  loop_mills, linestyle='solid',              color='blue',   label='IOB(x10)')
                    axbg.fill(iob_area, looparea, c='blue',   alpha=0.2)
        
                if featured('cob') :                                                    # plot COB
                    axbg.plot(origcob,  loop_mills, linestyle='solid',              color='orange', label='COB')
                    axbg.fill(cob_area, looparea, c='orange', alpha=0.4)

                if featured('pred') :                                                   # plot the predictions
                    thisTime = loop_mills[iFrame]
                    loopCount = 48+1
                    fcastmills = []
                    for lp in range(loopCount):
                        fcastmills.append(round(thisTime/1.000 + lp*5*60, 1 ))          # from millis to secs
                    bbox_props = dict(boxstyle='larrow', fc='grey', alpha=0.7)          # slider with time label
                    axbg.set_ylim(loop_mills[-1]+thickness*2+48*5*60+45*60, loop_mills[0]-thickness*2)  # incl 45min space for BG labels
                    axbg.set_xlim(0,250)                                                # otherwise we need to find scale over all time steps
                    bg_min, bg_max = axbg.get_xlim()
                    axbg.text(bg_min+3, fcastmills[0], loop_label[iFrame], va='center', size=8, bbox=bbox_props)
                    axbg.fill_between([bg_min,bg_max], fcastmills[0]-2*thickness, fcastmills[-1]+2*thickness, fc='grey', alpha=0.6)  # time window
                    if frameIns:
                        in_min, in_max = axin.get_xlim()
                        axin.plot([in_min,in_max], [fcastmills[0],fcastmills[0]], linestyle='dotted', color='grey', lw=0.5)          # time line

                    Fcasts = Pred[thisTime]
                    Levels = Fcasts['Levels']

                    #print (str(loop_label[iFrame]), str(Levels))
                    if 'minPredBG'    in Levels:
                        BGValPlot(axbg,-1, 'minPredBG',    Levels['minPredBG'],    fcastmills[-1], colFav['bg'])
                    if 'minZTGuardBG' in Levels:
                        BGValPlot(axbg, 1, 'minZTGuardBG', Levels['minZTGuardBG'], fcastmills[-1], colFav['ZT'])
                    if 'minIOBPredBG' in Levels:
                        BGValPlot(axbg, 2, 'minIOBPredBG', Levels['minIOBPredBG'], fcastmills[-1], colFav['IOB'])
                    if 'minCOBPredBG' in Levels:
                        BGValPlot(axbg, 3, 'minCOBPredBG', Levels['minCOBPredBG'], fcastmills[-1], colFav['COB'])
                    if 'minUAMPredBG' in Levels:
                        BGValPlot(axbg, 4, 'minUAMPredBG', Levels['minUAMPredBG'], fcastmills[-1], colFav['UAM'])
                    if 'avgPredBG'    in Levels:
                        BGValPlot(axbg, 0, 'avgPredBG',    Levels['avgPredBG'],    fcastmills[-1], 'black')
                    if 'naive_eventualBG'    in Levels:
                        BGValPlot(axbg,-2, 'naive_eventualBG', Levels['naive_eventualBG'], fcastmills[-1], 'purple')
                    if 'eventualBG'    in Levels:
                        BGValPlot(axbg,-3, 'eventualBG', Levels['eventualBG'], fcastmills[-1], 'green')
                    
                    if 'SMBoff' in Levels:
                        SMBmsg = 'SMB disabled:\n' + Levels['SMBoff']
                        threshold = Levels['value']
                        label = Levels['type']
                        SMBsource = Levels['source']
                        couleur = colFav[SMBsource]
                        if 'minGuardBG1' not in Levels:    print(str(Levels))
                        minGuardBG = Levels['minGuardBG1']                                  # get maxin/only contributioon
                        SMBarrow = dict(arrowstyle='<|-|>', fc=couleur, ec=couleur)
                        if label == 'maxDelta' :
                            Tmin = thisTime - 3*5*60
                            Tmax = thisTime + 3*5*60
                            posText = (minGuardBG+2, thisTime)
                            posArrow= (threshold, thisTime)
                        else:                                                               # why SMB is disabled
                            Tmin = fcastmills[0]
                            Tmax = fcastmills[-1]
                            when_mills = Levels['timePos']
                            if minGuardBG < 0 :                                             # off screen location supresses all
                                minGuardBG = 20
                                SMBarrow = dict(arrowstyle='<|-', fc=couleur, ec=couleur)
                                axbg.plot([0,20], [fcastmills[when_mills],fcastmills[when_mills]], linestyle='dotted', color=couleur)
                            posText = (threshold+2, fcastmills[when_mills])
                            posArrow= (minGuardBG,  fcastmills[when_mills])
                        axbg.plot([threshold,threshold], [Tmin,Tmax], linestyle='dashed', color='grey', label=label)
                        if not 'source2' in Levels:                                         # single source
                            axbg.annotate(SMBmsg, xy=posArrow, xytext=posText, va='center',
                                            arrowprops=SMBarrow )                           # no alignment option: va='center') )
                        else:                                                               # blended minGuard case !
                            SMBsource2  = Levels['source2']
                            minGuardBG2 = Levels['minGuardBG2']
                            hub_bg   = Levels['minGuardBG']                                 # bg position of hub for "balance"
                            couleur2 = colFav[SMBsource2]
                            when_mills2 = Levels['timePos2']
                            share2 = (minGuardBG2-hub_bg)/(minGuardBG2-minGuardBG)          # fraction of BG2
                            hub_mills = fcastmills[when_mills2]+(fcastmills[when_mills]-fcastmills[when_mills2])*share2   # time of hub for "balance"
                            posText = (threshold+2, hub_mills)
                            posArrow= (hub_bg,  hub_mills)
                            axbg.annotate(SMBmsg, xy=posArrow, xytext=posText, va='center',
                                            arrowprops=SMBarrow )                           # no alignment option: va='center') )
                            axbg.plot((hub_bg,minGuardBG2), (hub_mills,fcastmills[when_mills2]),
                                linestyle='dotted',  marker='o', color=couleur2)            # plot the lever arm of lesser contribution
                            axbg.plot((hub_bg,minGuardBG), (hub_mills,fcastmills[when_mills]), 
                                linestyle='dotted',  marker='o', color=couleur)             # plot the lever arm of lesser contribution
                    else:
                        SMBsource = ''
                        axbg.plot([0,0], [0,0], linestyle='dashed', color='grey', label='...')# inactive, i.e. off screen; placeholder for legend
    
                    if 'COB' in Fcasts:                                                 # assume same logic as in original
                        origCOB = Fcasts['COB']                                         # the original array from logfile
                        initCOB = Fcasts['COBinitBGs']                                  # the emulated array before cleanup
                        predCOB = Fcasts['COBpredBGs']                                  # is empty if COB=0; after cleanup
                        axbg.plot(origCOB, fcastmills[:len(origCOB)], linestyle='solid',            color=colFav['COB'], label='predCOB, original')
                        axbg.plot(initCOB, fcastmills[:len(initCOB)], linestyle='None', marker='.', color=colFav['COB'], fillstyle='none')
                        axbg.plot(predCOB, fcastmills[:len(predCOB)], linestyle='None', marker='.', color=colFav['COB'], label='predCOB, emulated')
                    else:
                        axbg.plot([0,0], [0,0],                       linestyle='none',             color=colFav['COB'], label='no COB active') # inactive
                    
                    if 'UAM' in Fcasts :                             # same logic as in original or minGuard source
                        origUAM = Fcasts['UAM']                                         # the initial array before cleanup
                        axbg.plot(origUAM, fcastmills[:len(origUAM)], linestyle='solid',            color=colFav['UAM'], label='predUAM, original')
                    elif 'UAM'==SMBsource :
                        initUAM = Fcasts['UAMinitBGs']                                  # the initial array before cleanup
                        predUAM = Fcasts['UAMpredBGs']
                        axbg.plot(initUAM, fcastmills[:len(initUAM)], linestyle='None', marker='.', color=colFav['UAM'], fillstyle='none')
                        axbg.plot(predUAM, fcastmills[:len(predUAM)], linestyle='None', marker='.', color=colFav['UAM'], label='predUAM, emulated')
                    else:
                        axbg.plot([0,0], [0,0],                       linestyle='none',             color=colFav['UAM'], label='no UAM active') # inactive
        
                    if 'IOB' in Fcasts:                                                 # assume same logic as in original
                        origIOB = Fcasts['IOB']                                         # the original array from logfile
                        initIOB = Fcasts['IOBinitBGs']                                  # the emulated array before cleanup
                        predIOB = Fcasts['IOBpredBGs']                                  # the emulated array after cleanup
                        axbg.plot(origIOB, fcastmills[:len(origIOB)], linestyle='solid',            color=colFav['IOB'], label='predIOB, original')
                        axbg.plot(initIOB, fcastmills[:len(initIOB)], linestyle='None', marker='.', color=colFav['IOB'], fillstyle='none')
                        axbg.plot(predIOB, fcastmills[:len(predIOB)], linestyle='None', marker='.', color=colFav['IOB'], label='predIOB, emulated')
                    else:
                        axbg.plot([0,0], [0,0],                       linestyle='none',             color=colFav['IOB'], label='no IOB active') # inactive
    
                    if 'ZT' in Fcasts:                                                  # assume same logic as in original
                        origZT = Fcasts['ZT']                                               # from the orig loop
                        initZT = Fcasts['ZTinitBGs']                                        # the initial array before cleanup
                        predZT = Fcasts['ZTpredBGs']
                        axbg.plot(origZT,  fcastmills[:len(origZT)],  linestyle='solid',            color=colFav['ZT'],  label='predZT, original')
                        axbg.plot(initZT,  fcastmills[:len(initZT)],  linestyle='None', marker='.', color=colFav['ZT'],  fillstyle='none')
                        axbg.plot(predZT,  fcastmills[:len(predZT)],  linestyle='None', marker='.', Color=colFav['ZT'],  label='predZT, emulated')
                    else:
                        axbg.plot([0,0], [0,0],                       linestyle='none',             color=colFav['ZT'],  label='no ZT  active') # inactive
                    
                axbg.legend(loc='lower right')
            
            if frameFlow :                                                              # anything related to flow chart
                axfl = fig.add_subplot(gs[0, flowOffset:])
                axfl.set_xticklabels(['',''])                                           # dummy axis labels
                axfl.set_xticks([-99,99999])                                            # off scale to suppress ticks
                axfl.set_xlim(10, 200)
                axfl.set_yticklabels(['',''])                                           # dummy axis labels
                axfl.set_yticks([-99999,99])                                            # off scale to suppress ticks
                axfl.set_ylim(-700, 0)
                axfl.set_xlabel('Flowchart and decision logic at time ' + loop_label[iFrame], weight='bold')
                 
                thisTime = loop_mills[iFrame]
                Flows = FlowChart[thisTime]
                row =  +20                                                              # start row, i.e. where the arrow starts
                row_dist = 50
                col = 20                                                                # start col, i.e. initial horizontal center
                col_dist = 25
                old_Thigh = 5                                                           # short start arrow
                stripOffset = 0                                                         # later offset into second strip
                for ele in Flows:                
                    row_old = row
                    col_old = col
                    title = ele['title']
                    indent = ele['indent']
                    dchar, drow = getBoxSize(title)
                    if eval(indent) == 0 :
                        row -= row_dist
                        col_offset = 0
                        arr_offset = 1 + old_Thigh*4
                        if indent == '0' :      col = 20 + stripOffset
                    else:
                        col += eval(indent)*col_dist
                        col_offset = 1 + old_Tlen*0.3
                        arr_offset = 0

                    if row<-680:                                                        # later : 650? check for bottom of first strip
                        row = 20 - row_dist
                        stripOffset += 100 - 5                                          # half of frame width
                        col += stripOffset

                    if col<col_old:                                                     # when going back in columns
                        flowBackwrd = dict(arrowstyle='<|-', 
                            connectionstyle='bar, angle=180, fraction='+str((old_Thigh-16)/(col_old-col))) # lower number makes final downstroke longer
                        axfl.annotate(ele['title'], xy=(col_old+col_offset, row_old-arr_offset), xytext=(col, row),
                                 ha='center',  va='center', bbox=bbox, arrowprops=flowBackwrd, fontsize=6)
                        AdrPlot(axfl, ele, row, drow, col, dchar)

                    elif stripOffset>0 and row>row_old:                                 # switch to 2nd strip
                        flowBackwrd = dict(arrowstyle='<|-', linestyle='dotted',
                            connectionstyle='bar, angle=90, fraction='+str(-5/(col_old-col)))
                        axfl.annotate(ele['title'], xy=(col_old+old_Tlen*0.3, row_old-arr_offset*0), xytext=(col, row),
                                 ha='center',  va='center', bbox=bbox, arrowprops=flowBackwrd, fontsize=6)
                        AdrPlot(axfl, ele, row, drow, col, dchar)

                    else:                                                               # normal situation
                        axfl.annotate(ele['title'], xy=(col_old+col_offset, row_old-arr_offset), xytext=(col, row),
                                 ha='center',  va='center', bbox=bbox, arrowprops=flowForward, fontsize=6)
                        AdrPlot(axfl, ele, row, drow, col, dchar)

                    old_Tlen = dchar
                    old_Thigh= drow

            pdf.savefig()
            if not featured('pred'):
                for i in range(iFrame+1,  len(loop_mills)+2):
                    zeile = xyf.readline()      # table row i
                    log_msg(zeile[:-1])         # w/o the <CR><LF>
                if how_to_print != 'GUI':    plt.show()      # otherwise conflict with root.mainloop() in tkinter
            plt.close()                         # end of current page
        #pdf.close()                            # not needed due to "with ..." method triggered above
    if featured('pred'):
        zeile = xyf.readline()                  # summary row 1
        log_msg(zeile[:-1])
        zeile = xyf.readline()                  # summary row 2
        log_msg(zeile[:-1])
    xyf.close()

def parameters_known(myseek, arg2, variantFile, startLabel, stoppLabel, entries):
    #   start of top level analysis
    
    global fn
    global ce_file
    global varLabel
    global doit
    global fn_first

    global  loop_mills, loop_label
    global  bg
    global  origTarLow, emulTarLow, origTarHig, emulTarHig
    global  origAs_ratio, emulAs_ratio
    global  origiob, origcob
    global  activity
    global  origInsReq, emulInsReq
    global  origSMB, emulSMB, origMaxBolus, emulMaxBolus
    global  origBasal, emulBasal, lastBasal
    global  origISF, autoISF, emulISF, longDelta, avgDelta, longSlope, rateSlope
    global  Pred, FlowChart 
    global  filecount
    global  t_startLabel, t_stoppLabel
    global  varFile
    global  CarbReqGram, CarbReqTime, lastCOB
    
    global  isAndroid                               # flag for running on Android
    global  isZip                                   # flag for input file type
    global  newLoop                                 # flag whether data collection for new loop started
    #global  entries
    
    loop_mills  = []
    loop_label  = []
    bg          = []
    origTarLow  = []
    emulTarLow  = []
    origTarHig  = []
    emulTarHig  = []
    
    origAs_ratio= []
    emulAs_ratio= []
    origiob     = []
    origcob     = []
    activity    = []
    
    origInsReq  = []
    emulInsReq  = []
    origSMB     = []
    emulSMB     = []
    origMaxBolus= []
    emulMaxBolus= []
    origBasal   = []
    emulBasal   = []
    lastBasal   = []
    longDelta   = []                                # holds the duration of recent 5% range
    avgDelta    = []                                # holds the average BG of recent 5% range
    longSlope   = []                                # holds the duration of regression fit
    rateSlope   = []                                # holds the fitted rate (mg/dl/5mins)
    origISF     = []                                # holds the original ISF defined in the active profile
    autoISF     = []                                # holds the ISF after checking the autosense impact
    emulISF     = []                                # holds the ISF after strengthening due to long lasting highs
    
    Pred        = {}                                # holds all loop predictions
    FlowChart   = {}                                # holds all loop decisions for flow chart
    
    t_startLabel= startLabel
    t_stoppLabel= stoppLabel
    filecount   = 0
    newLoop     = False
        
    myfile = ''
    arg2 = arg2.replace('_', ' ')                   # get rid of the UNDERSCOREs
    doit = arg2.split('/')
    varFile = variantFile                           # on Windows
    varLabel = os.path.basename(varFile)            # do not overwrite the calling arg value
    if varLabel[len(varLabel)-4:] == '.dat' :       # drop the tail coming from DOS type ahead
        varLabel = varLabel[:-4]
    
    logListe = glob.glob(myseek+myfile, recursive=False)
    filecount = 0
    if arg2[:7] == 'Android' :
        isAndroid = True
    else:
        isAndroid = False
        
    for fn in logListe:
        ftype = fn[len(fn)-3:]
        useFile = False
        if isAndroid and ftype=='log':                                  useFile = True
        elif not isAndroid and (ftype=='zip' or ftype.find('.')>0) :    useFile = True      # valid logfiles should end with "_.0" thru "_.99" or "zip"
        if useFile:
            isZip = ( ftype == 'zip')
            if filecount == 0 :                     # initalize file loop
                ce_file = fn + '.' + varLabel + '.txt'
                cel = open(ce_file, 'w')
                cel.write('AAPS scan from ' + varLabel + ' for SMB comparison created on ' + formatdate(localtime=True) + '\n')
                cel.write('FILE='+fn + '\n')
                cel.close()
                my_ce_file(ce_file)                 # exports name to determine_basal.py
                fn_first = fn
            if not isAndroid:        log_msg ('Scanning logfile '+fn)
            cont = scanLogfile(fn, entries)
            #print('returned to parameters_known:', CarbReqGram, 'when:', CarbReqTime)
            filecount += 1
            if cont == 'STOP':      break           # end of time window reached
    
    if filecount == 0 :
        log_msg ('no such logfile: "'+myseek+'"')
        return 'Z', 0, '', '', 0
    loopCount = len(loop_mills)
    if loopCount == 0 :
        log_msg ('no entries found in logfile: "'+myseek+'"')
        #return     #sys.exit()
    log.write('ENDE\n')
    log.close()
    varlog.close()
    
    if loopCount > 0 :   # ---   save the results from current logfile   --------------
        for iFrame in range(len(loop_label)):
            thisTime = loop_mills[iFrame]
            if thisTime not in entries:                 # holds the rows to be printed on Android or windows
                r_list = loop_label[iFrame][:5]+'Z'
                if featured('bg'):      
                    r_list += f'{bg[iFrame]:>5}'
                if featured('target'):
                    r_list += f'{(origTarLow[iFrame] + origTarHig[iFrame])/2:>6}'
                if featured('iob'):     
                    r_list += f'{round(origiob[iFrame]/10,2):>6}'   # was scaled up for plotting
                if featured('cob'):     
                    r_list += f'{round(origcob[iFrame],2):>6}'
                if featured('as_ratio'):
                    r_list += f'{origAs_ratio[iFrame] / 10:>6}'     # was scaled up for plotting
                if featured('range'):
                    r_list += f'{longDelta[iFrame]:>6}{avgDelta[iFrame]:>7}'
                if featured('slope'):
                    r_list += f'{longSlope[iFrame]:>7}{rateSlope[iFrame]:>6}'
                if featured('ISF'):
                    r_list += f'{round(origISF[iFrame],1):>6}{round(autoISF[iFrame],1):>6}{round(emulISF[iFrame],1):>6}'
                if featured('insReq'):
                    r_list += f'{origInsReq[iFrame]:>7}{emulInsReq[iFrame]:>6}'
                if featured('SMB'):
                    r_list += f'{origSMB[iFrame]:>6}{emulSMB[iFrame]:>5}'
                if featured('basal'):
                    r_list += f'{round(origBasal[iFrame],2):>7}{round(emulBasal[iFrame],2):>7}'
                entries[thisTime] = r_list
                    
        # ---   print the comparisons    -------------------------
        head= "   ----time formated as---                           -Autosens-   -----target-----     insulin Req     -maxBolus-     ---SMB---     ---tmpBasal---   --5% range--    --lin.fit--\n" \
            + "id    UTC         UNIX       bg    cob   iob    act  orig  emul     orig     emul      orig   emul      orig emul     orig emul       orig    emul   dura    avg     dura    avg"
        #print('\n' + head)
        xyf.write(head + '\n')
        
        origBasalint = 0.0
        emulBasalint = 0.0
        origSMBsum = 0.0
        emulSMBsum = 0.0
        
        for i in range(loopCount) :
            tabz= f'{i:>2} {loop_label[i]} {loop_mills[i]:>13} {bg[i]:>4} ' \
                + f'{origcob[i]:>6} {round(origiob[i]/10,2):>5} {round(activity[i]/1000,3):>6} ' \
                + f'{round(origAs_ratio[i]/10,2):>5} {round(emulAs_ratio[i]/10,2):>5}' \
                + f'{origTarLow[i]:>6}-{origTarHig[i]:>3} {emulTarLow[i]:>4}-{emulTarHig[i]:>3} ' \
                + f'{origInsReq[i]:>8} {emulInsReq[i]:>6} ' \
                + f'{origMaxBolus[i]:>9} {emulMaxBolus[i]:>4} {origSMB[i]:>8} {emulSMB[i]:>4} ' \
                + f'{origBasal[i]:>10} {emulBasal[i]:>7}' \
                + f'{longDelta[i]:>7} {avgDelta[i]:>7}' \
                + f'{longSlope[i]:>8} {rateSlope[i]:>6}'
            #print(tabz)
            origSMBsum += origSMB[i]
            emulSMBsum += emulSMB[i]
            if i==loopCount-1:                    # last time step
                fraction = 5 / 60               # next 5 min per hour
            else:
                fraction = (loop_mills[i+1] - loop_mills[i]) / 3600
            #print (str(fraction*60))
            origBasalint += origBasal[i]*fraction
            emulBasalint += emulBasal[i]*fraction        
            xyf.write(tabz + '\n')
        
        sepLine = ''
        for i in range(176):
            sepLine += '-'
        tabz = 'Totals:'+f'{round(origSMBsum,1):>115} {round(emulSMBsum,1):>4} {round(origBasalint,2):>10} {round(emulBasalint,2):>7}'
        #print(sepLine + '\n' + tabz)
        xyf.write(sepLine + '\n' + tabz + '\n')
    xyf.close()
    
    if isAndroid :
        maxItems = 14           
    else:
        maxItems = len(loop_label)
        XYplots(loopCount)
    if len(entries) == 0:
        print('\nNo loop data yet in fresh logfile')
        return 'Z',0, '', '', 0
    else:                                               #  6
        head1 = '  UTC '
        head2 = ' time '
        if featured('bg'):                              #  5     
            head1 += '     '
            head2 += '   bg'
        if featured('target'):                          #  6
            head1 += '  avg.'
            head2 += '  targ'
        if featured('iob'):                             #  6
            head1 += '      '
            head2 += '   IOB'
        if featured('cob'):                             #  6 
            head1 += '      '
            head2 += '   COB'
        if featured('as_ratio'):                        #  6
            head1 += '  Auto'
            head2 += '  sens'
        if featured('range'):                           # 13
            head1 += '  --5% range-'
            head2 += '  dura   avg.'
        if featured('slope'):                           # 13
            head1 += '   --lin.fit-'
            head2 += '   dura  rate'
        if featured('ISF'):                             # 18
            head1 += '  ------ISFs------'
            head2 += '  orig  auto  emul'
        if featured('insReq'):                          # 13
            head1 += '  insulin Req'
            head2 += '   orig  emul'
        if featured('SMB'):                             # 11
            head1 += '  ---SMB---'
            head2 += '  orig emul'
        if featured('basal'):                           # 14
            head1 += '  --tmpBasal--'
            head2 += '   orig   emul'
    
        sorted_entries = sorted(entries)
        top10 = min(maxItems, len(entries) )
        tail = ''
        if isAndroid :
            os.system('clear')
            if len(head1) == 92:    tail = ' '                              # this is double of portrait width
        log_msg(head1+tail)
        log_msg(head2+tail)                                                 # 1 record per print for safe rotations
        for thisTime in sorted_entries[len(sorted_entries)-top10:]:         # last hour plus
            values = entries[thisTime]
            log_msg(values+tail)

        # erase outdated entries; the remainder is kept in case a new logfile is started
        old_entries = copy.deepcopy(sorted_entries)
        for oldTime in old_entries:
            if oldTime not in sorted_entries[len(sorted_entries)-top10:]:
                del entries[oldTime]                                        # no longer in last 14 entries
        if loopCount == 0:
            return 'Z', 0, '', '', 0
        else:
            extraSMB = emulSMB[loopCount-1] - origSMB[loopCount-1] 
            return loop_label[loopCount-1], round(extraSMB, 1), CarbReqGram, CarbReqTime, lastCOB
    
def set_tty(printframe, txtbox, channel):               # for GIU
    global how_to_print
    how_to_print = channel
    global runframe
    runframe = printframe
    global lfd
    lfd = txtbox
    
def log_msg(msg):                                       # for GUI
    if how_to_print == 'GUI':
        lfd['state'] = 'normal'
        lfd.insert('end', msg + '\n')
        lfd.see('end')
        lfd['state'] = 'disabled'
        runframe.update()                                                       # update frame display
    else:
        print(msg)
