#
"""
	Scan APS logfile and extract relevant items
    to compare original SMB analysis vs. the determine_basal.py
"""
#	Version INIT		Started	08.Dec.2019			Author	Gerhard Zellermann
#   - adapted from scanAPSlog.py

from email.utils import formatdate
from decimal import *
from datetime import timezone
import  datetime
import  os, subprocess, sys
import  glob
import  time
import  json
import  zipfile
import  binascii
import  copy
import  re

import determine_basal as detSMB
from determine_basal import my_ce_file 

def get_version_core(echo_msg):
    echo_msg['emulator_core.py'] = '2024-08-11 19:53'
    return echo_msg

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
    if 'reason' not in result:                                          # error like "could not calculate eventualBG"
        CarbReqTime = ''
        CarbReqGram = ''
        return                                
    if result['reason'][:10] == 'Error: CGM':                           # like no CGM while loading transmitter
        CarbReqTime = ''
        CarbReqGram = ''
        return                                
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
        #r_list['CarbReqGram'] = CarbReqGram
        #r_list['CarbReqTime'] = CarbReqTime
        #entries[thisTime] = r_list
    #print('leaving "check ..." with '+CarbReqGram+'g in', CarbReqTime+'min\n')
    pass

def basalFromReason(smb, lcount):
    #print('\nrow', str(lcount), str(smb))
    #suggest = smb['openaps']['suggested']
    if 'rate' in smb :
        rateReq = smb['rate']
    elif 'pump'in smb and 'extended' in smb['pump'] and 'TempBasalAbsoluteRate' in  smb['pump']['extended']:
        rateReq = smb['pump']['extended']['TempBasalAbsoluteRate']
    else:
        rateReq = currenttemp['rate']         # keep existing rate ?
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

def STAIR_scan(stmp, myVal, woSTAIR, type_len, STAIR_json):
    # times must be in Greenwich time i.e. UTC but sorted from 0-23
    stmp_day = stmp[:11]
    for STEP in STAIR_json:
        newVal = STAIR_json[STEP]
        break                                                           # use first entry to extrapolate backwards
    for STEP in STAIR_json:
        if stmp_day+STEP == stmp:
            newVal = STAIR_json[STEP]
            break
        elif stmp_day+STEP > stmp:
            break
        newVal = STAIR_json[STEP]
    myVal = myVal[:woSTAIR] + str(newVal) + myVal[woSTAIR+6+type_len:]
    return myVal

def setVariant(stmp):
    # set the what-if scenario
    #print('entered setVariant with stmp='+str(stmp))
    global autosens_data
    global glucose_status
    global bg
    global currenttemp
    global iob_data #, utcOffset
    global meal_data
    global profile
    global new_parameter, autoISF_version
    ####################################################################################################################################
    # additional parameters collected here
    # these need an according modification in "determine_basal.py"
    #rofile['use_autoisf'] = False                          ### not enabled in standard AAPS and not even available
    new_parameter = {}
    #print('\nin set_Variant', str(type('utcOffset')))
    #new_parameter['utcOffset'] = utcOffset                  ### for Activity Monitor sleeping hours
    temp          = {}                                      ### holds interim values in shorter notation
    if (stmp != '1900-01-01T00:00:00') :
        # first, do the AAPS standard assignments           ### variations are set in the <variant>.dat file
        new_parameter['maxDeltaRatio'] = 0.2                ### add'l parameter; AAPS is fix at 0.2
        new_parameter['SMBRatio'] = 0.5001                  ### add'l parameter; AAPS is fix at 0.5; I use 0.7 as no other rig interferes
        new_parameter['maxBolusIOBUsual'] = True            ### add'l parameter; AAPS is fix at True, but my basal is too low
        new_parameter['maxBolusIOBRatio'] = 1               ### add'l parameter; AAPS is fix at 1, but my basal is too low
        new_parameter['maxBolusTargetRatio'] = 1.001        ### add'l parameter; AAPS is fix at 1, bit i saw rounding problems otherwise
        new_parameter['CapFactor'] = 0                      ### add'l parameter; AAPS is fix at 0; recently I used 4, but try 5
        new_parameter['CheckLibreError'] = 'cgmFlatMinutes' in profile   ### add'l parameter: autoISF  2.2.8 is at True for the stupid Libre CGM error handler, but Emulator skips the error in original
        new_parameter['AAPS_Version'] = AAPS_Version        ### place it before so it could be modified later
        new_parameter['LessSMBatModerateBG'] = False        ### additional parameter; AAPS is fix at False; reduce SMB if ...
        new_parameter['LessSMBFactor'] = 2.0                ### eine alte Gewichtung ???
        new_parameter['LessSMBbelow'] = profile['max_bg']+10.0                 ### ... bg below this value
        
        gz_proto  = 'full_basal_exercise_target' in profile
        if gz_proto:
            if 'thresholdRatio' not in new_parameter:
                new_parameter['thresholdRatio'] = 0.6           ### add'l parameter; AAPS is fix at 0.5; I use 0.6 to lift the minimum 
            if 'insulinCapBelowTarget' not in new_parameter:
                new_parameter['insulinCapBelowTarget'] = True   ### add'l parameter; AAPS is fix at False; enable capping below
        if 'autoISF_version' not in profile:
            profile['autoISF_version'] = '(older version)'
        if 'enable_autoISF' not in profile:
            profile['enable_autoISF'] = False               ### not known before ai2.2.x
        if 'smb_delivery_ratio' not in profile:
            profile['smb_delivery_ratio'] = 0.5             ### not known before ai2.2.6
        if 'smb_delivery_ratio_min' not in profile:
            profile['smb_delivery_ratio_min'] = 0.5         ### not known before ai2.2.6; use recommendation
        if 'smb_delivery_ratio_max' not in profile:
            profile['smb_delivery_ratio_max'] = 0.9         ### not known before ai2.2.6; use recommendation
        if 'smb_delivery_ratio_bg_range' not in profile:
            profile['smb_delivery_ratio_bg_range'] = 0      ### not known before ai2.2.6; keep disabled
        if 'iobTHtolerance' not in new_parameter:
            new_parameter['iobTHtolerance'] = 130           ### not known before ai3.0
        if 'insulinCapBelowTarget' not in new_parameter:
            new_parameter['insulinCapBelowTarget'] = False  ### add'l parameter; AAPS is fix at False; enable capping below
        if 'meal_type_weight' not in profile:
            profile['meal_type_weight'] = 0                 ### not known before ai3.0
        if 'meal_addon' not in profile:
            profile['meal_addon'] = 0                       ### not known generally
        if 'iob_threshold_percent' not in profile:
            profile['iob_threshold_percent'] = 100          ### not known before ai3.0
        if 'thresholdRatio' not in new_parameter:
            new_parameter['thresholdRatio'] = 0.5           ### add'l parameter; AAPS is fix at 0.5; I use 0.6 to lift the minimum 
        if 'profile_percentage' not in profile:
            profile['profile_percentage'] = 100             ### not known before ai3.0
        if 'enableSMB_EvenOn_OddOff_always' not in profile:
            profile['enableSMB_EvenOn_OddOff_always'] = False  ### not known before ai2.2.8
        if 'enableSMB_EvenOn_OddOff' not in profile:
            profile['enableSMB_EvenOn_OddOff'] = profile['enableSMB_EvenOn_OddOff_always']  ### not known before ai2.2.7; default after 3.0.1
        if 'enable_pp_ISF_always' not in profile:
            profile['enable_pp_ISF_always'] = True          ### not known before ai2.2.7; default after 3.0.1
        if 'pp_ISF_hours' not in profile:
            profile['pp_ISF_hours'] = 0                     ### not known before ai2.2.7 or after 3.0.1
        if 'delta_ISFrange_weight' not in profile:
            profile['delta_ISFrange_weight'] = 0.0          ### not known                   after 3.0.1
        if 'enable_dura_ISF_with_COB' not in profile:
            profile['enable_dura_ISF_with_COB'] = False     ### not known before without ai
        #if 'activity_detection' not in profile and 'key_activity_detection' not in profile:
        #    profile['activity_detection'] = False       ### not known before without ai
        if 'activity_detection' in profile and profile['activity_detection']:
            if 'activity_weight' in profile:
                profile['activity_scale_factor'] = profile['activity_weight' ]
                profile['inactivity_scale_factor'] = profile['inactivity_weight' ]
            if 'nightly_inactivity_detection' in profile:
                profile['ignore_inactivity_overnight'] = profile['nightly_inactivity_detection']
            if 'ignore_inactivity_overnight' not in profile:
                profile['ignore_inactivity_overnight'] = False
            if 'activity_idle_start' in profile:
                profile['inactivity_idle_start'] = profile['activity_idle_start']
                profile['inactivity_idle_end'] = profile['activity_idle_end']
            if 'inactivity_idle_start' not in profile:
                profile['inactivity_idle_start'] = 0
                profile['inactivity_idle_end'] = 0
        if 'parabola_fit_source' not in profile:            ### predating A3.2.0.2 Libre3
            profile['parabola_fit_source'] = 5              ### standard CGMs at 5m interval
        if AAPS_Version == '<2.7':                          
            profile['maxUAMSMBBasalMinutes'] = 30           ### use the 2.7 default just in case
            profile['bolus_increment'] = 0.1                ### use the 2.7 default just in case
    ####################################################################################################################################
    STAIR    = {}                                                   # for general, profile like definitions
    STAIR_BAS= {}                                                   # for profile definition of basal rate
    STAIR_CR = {}                                                   # for profile definition of carb ratio
    STAIR_ISF= {}                                                   # for profile definition of ISF
    STAIR_LTG= {}                                                   # for profile definition of lower target
    STAIR_HTG= {}                                                   # for profile definition of higher target
    INTERPOL = []                                                   # for linear interpolation between times
    POLYGON  = []                                                   # for linear interpolation between numbers
    flag_staircase = False
    # read the variations and apply them
    fnam= varLabel + '.dat'
    var = open(varFile, 'r')
    syntax_error = False
    ocount = 0
    for orig_zeile in var:
        ocount+= 1
        try:
            zeile = orig_zeile.replace('\t', ' ')                                   # get rid of TAB characters
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
            if woEndVal<0 :                                                         # no trailing comment
                myVal   = zeile
            else:
                myVal   = zeile[:woEndVal]
            if myVal != '':
                while myVal[-1] == ' ' :    myVal = myVal[:-1]                      # truncate trailing BLANKS
            
            woSTAIR = myVal.find('STAIR_')
            if woSTAIR >= 0:                                                        # get value from last valid step
                if   myVal[woSTAIR+6:woSTAIR+9] == 'BAS':    myVal = STAIR_scan(stmp, myVal, woSTAIR, 3, STAIR_BAS)
                elif myVal[woSTAIR+6:woSTAIR+8] == 'CR' :    myVal = STAIR_scan(stmp, myVal, woSTAIR, 2, STAIR_CR)
                elif myVal[woSTAIR+6:woSTAIR+9] == 'ISF':    myVal = STAIR_scan(stmp, myVal, woSTAIR, 3, STAIR_ISF)
                elif myVal[woSTAIR+6:woSTAIR+9] == 'LTG':    myVal = STAIR_scan(stmp, myVal, woSTAIR, 3, STAIR_LTG)
                elif myVal[woSTAIR+6:woSTAIR+9] == 'HTG':    myVal = STAIR_scan(stmp, myVal, woSTAIR, 3, STAIR_HTG)
                else:                                        sub_issue('key', myVal[woSTAIR+6:woSTAIR+9], 'not found')

            woSTAIR = myVal.find('STAIR')
            if woSTAIR >= 0:                                                        # get value from last valid step
                for STEP in STAIR:
                    newVal = STAIR[STEP]
                    break                                                           # use first entry to extrapolate backwards
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

            woPOLYGON = myVal.find('POLYGON')
            if woPOLYGON>= 0:                                                       # get value from last valid step
                xstr = hole(myVal, woPOLYGON+7, '(', ')')                           # get the argument
                xdata = eval(xstr)
                #print('polygon', xstr, str(xdata), '\n'+str(POLYGON))
                (STEP,  sVal)  = POLYGON[0]                                         # low end tuple
                (STEPt, sValt) = POLYGON[len(POLYGON)-1]                            # high end tuple
                if STEP > xdata:                                                     # extrapolate backwards
                    (STEPt, sValt) = POLYGON[1]                                     # second tuple
                    lowVal = sVal
                    topVal = sValt
                    lowX= STEP
                    myX = xdata
                    topX= STEPt
                    newVal = lowVal + (topVal-lowVal)/(topX-lowX)*(myX-lowX)
                elif STEPt < xdata:                                                  # extrapolate forwards
                    (STEP, sVal) = POLYGON[len(POLYGON)-2]                        # last but 1 tuple
                    lowVal = sVal
                    topVal = sValt
                    lowX= STEP
                    myX = xdata
                    topX= STEPt
                    newVal = lowVal + (topVal-lowVal)/(topX-lowX)*(myX-lowX)
                else:                                                               # interpolate inside range
                    for i in range(len(POLYGON)):
                        (STEP, sVal) = POLYGON[i]
                        if STEP == xdata:
                            newVal = sVal   #POLYGON[STEP]
                            break
                        elif STEP > xdata:
                            topVal = sVal
                            lowX= lowLabl
                            myX = xdata
                            topX= STEP
                            newVal = lowVal + (topVal-lowVal)/(topX-lowX)*(myX-lowX)
                            break
                        lowVal = sVal 
                        lowLabl= STEP
                myVal = myVal[:woPOLYGON] + str(newVal) + myVal[woPOLYGON+7+len(xstr)+2:]

            logmsg = 'appended new entry to'
            validRow = True
            if   myArray == 'new_parameter' :                                         # allow also string type assignments like "<V2.7"
                if myItem in new_parameter :
                    logmsg = 'edited old value of '+str(new_parameter[myItem])+' in'
                if myVal[0] == '"' :
                    new_parameter[myItem] =      myVal[1:-1]                        # string variable
                else:
                    new_parameter[myItem] = eval(myVal)                             # normal case of numeric or booolean variable
                logres = str(new_parameter[myItem])
                
                #if myItem == 'FSL_min_dur' and stmp=='1900-01-01T00:00:00':
            if stmp=='1900-01-01T00:00:00':
                    return False                                                    # end of pre-scan
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
                logres = myVal
            elif myArray == 'STAIR_BAS' :
                STAIR_BAS[myItem] = eval(myVal)
                logres = myVal
            elif myArray == 'STAIR_CR' :
                STAIR_CR[myItem] = eval(myVal)
                logres = myVal
            elif myArray == 'STAIR_ISF' :
                STAIR_ISF[myItem] = eval(myVal)
                logres = myVal
            elif myArray == 'STAIR_LTG' :
                STAIR_LTG[myItem] = eval(myVal)
                logres = myVal
            elif myArray == 'STAIR_HTG' :
                STAIR_HTG[myItem] = eval(myVal)
                logres = myVal
            elif myArray == 'INTERPOL' :
                if len(myItem) < 24:                                          # incomplete UTC time label
                    oldLen = len(myItem)
                    if myItem[oldLen-1:] == 'Z':
                        oldLen += -1
                        myItem = myItem[:-1]
                    myItem = myItem + '00:00:00.000Z'[oldLen-11:]
                INTERPOL.append((myItem, eval(myVal)) )
                logres = myVal
            elif myArray == 'POLYGON' :
                POLYGON.append((eval(myItem), eval(myVal)) )
                logres = myVal
            elif myArray != 'new_parameter':
                validRow = False
                if myArray != '':   varlog.write(myArray + ' is an inrecognised array/json/keyword')
        
            if (stmp != '1900-01-01T00:00:00') :
                if validRow:    varlog.write(logmsg+' '+myArray+' with '+myItem+'='+logres+'\n')
                else:           varlog.write('not actioned: ['+myArray+'], ['+myItem+'], ['+myVal[:-1]+']'+'\n')
        except: # catch *all* exceptions
            e = sys.exc_info()[0]
            if (stmp == '1900-01-01T00:00:00') :
                print("*******\nProblem in VDF-file in row "+str(ocount)+" reading\n"+orig_zeile+"\nerror message is:"+str(e)+"\n*******\n")
            else:
                varlog.write("*******\nProblem in VDF-file in row "+str(ocount)+" reading\n"+orig_zeile+"\nerror message is:"+str(e)+"\n*******\n")
                sub_issue('error found while processing VDF file. For details, see file "*.'+varLabel+'.log"')
            syntax_error = True
                    
    ####################################################################################################################################
    # final clean up
    #ew_parameter['AAPS_Version'] = AAPS_Version                ### flag to handle differences in determine-basal
    if (stmp != '1900-01-01T00:00:00') :
        profile['new_parameter'] = new_parameter                ### use profile as piggyback to get parameters into determine_basal
        bg[-1] = glucose_status['glucose']                      ### just in case it got changed 
        global emulTarLow
        global emulTarHig
        emulTarLow[-1] = profile['min_bg']                      ### please do not touch
        emulTarHig[-1] = profile['max_bg']                      ### please do not touch
        global emulAs_ratio
        emulAs_ratio.append(autosens_data['ratio']*10)
    return syntax_error

def getOrigPred(predBGs):
    Fcasts = {}
    #for BGs in predBGs:
    #    Fcasts[BGs] = predBGs[BGs]
    #print ('orig preds --> '+str(Fcasts))
    return Fcasts

def extractResultComponent(st, key, keyStart, keyEnd):
    wo = st.find(key)
    Curly= hole(st, 1+wo, keyStart, keyEnd)
    wo_apo = Curly.find("\'")
    if wo_apo>0:
        Curly = Curly[:wo_apo-1]+Curly[wo_apo:]
    return Curly
   
def TreatLoop33(st, log, lcount, fn):
    if not newLoop: return
    global utcOffset
    utcOffset = extractResultComponent(st, 'utcOffset', '=', ',')
    get_currenttemp(  lcount, extractResultComponent(st, 'currentTempJson', '{', '}'))
    get_iob_data(     lcount, extractResultComponent(st, 'iobDataJson', '[', ']'), log, st[:8] )
    get_profile(      lcount, extractResultComponent(st, 'profileJson', '{', '}'))
    get_autosens_data(lcount, extractResultComponent(st, 'autosensDataJson', '{', '}'))
    get_meal_data(    lcount, extractResultComponent(st, 'mealDataJson', '{', '}'))
    Curly = extractResultComponent(st, 'resultJson', '{', '}')
    rt = json.loads(Curly)
    global SMBreason, origAI_ratio
    SMBreason = {}                                              # clear for first filtered debug list
    SMBreason['script'] = '---------- Script Debug --------------------\n'
    for ele in range(len(rt['consoleError'])):
        what = rt['consoleError'][ele]
        #print(what)
        SMBreason['script'] += what +'\n'
        if str(what).find('---')==0:
            pass
        elif what.find('SMB enabled')==0:
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
            #print('lastTempAge', str(SMBreason['lastTempAge']), 'found in row', str(lcount), 'from', what)
        elif what.find('ISF unchanged:')==0:                # first reference
            SMBreason['origISF'] = eval(what[16:-1])
            #print (str(lcount), str(origISF))
        elif what.find('ISF from ')==0:                     # here, insert the original autosens modified line handling
            isf_anf = what.find(' to ')
            SMBreason['origISF'] = eval(what[isf_anf+4:-1])
            #print (str(lcount), str(origISF))
        elif what.find('profile.sens:')==0:                 # redefine it
            isf_anf = what.find(' sens:')
            isf_end = what.find(' CSF:')
            SMBreason['origISF'] = eval(what[isf_anf+6:isf_end])
            #print (str(lcount), str(origISF))
        elif what.find('final ISF factor is') ==0:          # result of autoISF
            final_ISF_string = what[20:]
            wo = final_ISF_string.find(' ')                # origin sens can  be appended
            if wo<1:       wo = len(final_ISF_string)
            
            origAI_ratio.append(eval(final_ISF_string[:wo])*10)
    for ele in range(len(rt['consoleLog'])):
        #print(rt['consoleLog'][what])
        SMBreason['script'] += rt['consoleLog'][ele] +'\n'
    #print(rt['reason'])
    #SMBreason['script'] += rt['reason'] +'\n'
    SMBreason['origISF'] = rt['variable_sens']
    
    cont = TreatLoop(Curly, log, lcount, fn)
    return cont

def TreatLoop(Curly, log, lcount, fn):
    global SMBreason, newLoop
    global loop_mills, loop_label, bgTimeMap, bgTime, bg
    global origInsReq
    global emuliobTH, tolerance_iobTH
    global origSMB, emulSMB
    global origMaxBolus, emulMaxBolus
    global origBasal, lastBasal
    global longDelta, avgDelta, longSlope, rateSlope, glucose_status, origISF, BZ_ISF, Delta_BZ, emulISF, origAI_ratio, emulAI_ratio
    global Pred, FlowChart, Fits
    global  CarbReqGram, CarbReqTime, lastCOB
    #print('\nentered TreatLoop for row '+str(lcount)+' ending with  /'+Curly[-1]+'/ having '+Curly[780:800]+'\n'+Curly)
    wo_apo = Curly.find("\'")
    if wo_apo>0:
        Curly = Curly[:wo_apo-1]+Curly[wo_apo:]
        #print("found \' at position "+str(wo_apo)+"\n" +Curly)
    if not newLoop:                            # caught in the middle of a loop or repat of Result row
        SMBreason = {}                                              # clear for first filtered debug list
        SMBreason['script'] = '---------- Script Debug --------------------\n'
        return 'MORE'       
    #print('zeile', str(lcount), '\n'+(Curly))
    smb = json.loads(Curly)

    go_on = False
    if 'openaps' in smb and 'reason' in smb['openaps']['suggested']:# otherwise unknown source of entry
        suggest = smb['openaps']['suggested']
        go_on = True
    elif 'insulinReq' in smb:
        suggest = smb                                               # AAPS V3 does not have longer NS DBADD log
        go_on = True
    if go_on :
        newLoop = False
        #thisTime = int(round(time.time() * 1000))                  # use as now() or the emulated execution time
        if 'deliverAt' in suggest:
            stmp = suggest['deliverAt']                             # the SMB mode from oref1
        elif 'timestamp' in suggest:
            stmp = suggest['timestamp']                             # the AMA mode 
        else:
            log_msg('no time stamp found in\n' + str(suggest) )
            return 'STOP' 
        if t_startLabel > stmp :                                    # too early
            while len(origAI_ratio)>len(loop_mills):
                origAI_ratio.pop()                                  # erase foot print of loops to be skipped
            SMBreason = {}                                          # clear for first filtered debug list
            SMBreason['script'] = '---------- Script Debug --------------------\n'
            return 'MORE'       
        if t_stoppLabel < stmp :
            bgTime.pop()
            bg.pop()
            #bgTimeMap.pop()
            return 'STOP'           # too late; send quit signal
        thisTime = ConvertSTRINGooDate(stmp)
        reason = suggest['reason']
        if 'carbsReq' in suggest:
            CarbReqGram = str(suggest['carbsReq'])
            CarbReqTime = str(suggest['carbsReqWithin'])
            lastCOB = hole(reason, 1, ' ', ',')[:-1]                #drop trailing COMMA
        else:
            CarbReqGram = ' '
            CarbReqTime = ' '
            lastCOB = ' '
        #print(str(lcount), lastCOB, CarbReqGram, CarbReqTime)
        loop_mills.append(round(thisTime/1000, 1) )                 # from millis to secs
        loop_label.append(stmp[11:19] + stmp[-1])                   # include seconds to distinguish entries
        #print('len loop_mills='+str(len(loop_mills))+'; len labels='+str(len(loop_label))+'; mills='+str(bgTime[-1]))
        bgTimeMap[loop_mills[-1]] = bgTime[-1]                      # bgTime used by loop at thisTime
        if 'insulinReq' in suggest:
            key = 'insulinReq'
            ins_Req = suggest[key]
            #if str(ins_Req) == 'None':      ins_Req = 0
            #print('\n\n  ' + (key+'    ')[:6] + '=' + str(ins_Req) + '\n\n')
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
        log.write('\n========== loop in row ' + str(lcount) + ' ========== of logfile '+fn+'\n')
        log.write('  created at= ' + stmp + '\n')
        log.write(SMBreason['script'])                              # the script debug section
        #printVal(suggest, 'bg', log)
        log.write('---------- Reason --------------------------\n' + str(reason) + '\n')
        if reason.find('Error: CGM data is unchanged for the past ~45m.')>-1 \
        or reason.find('Error: CGM data was suspiciously flat for the past ~')>-1:
            # the insufficient FSL check corrupted the loop, skip it
            loop_mills.pop()
            loop_label.pop()
            origSMB.pop()
            origMaxBolus.pop()
            SMBreason = {}                                              # clear for first filtered debug list
            SMBreason['script'] = '---------- Script Debug --------------------\n'
            return 'MORE'       
        tempReq = basalFromReason(suggest, lcount)
        origBasal.append(round(eval(tempReq), 4))
        
        # now we can set the remaining iob data section
        #print(str(lcount), str(SMBreason))
        last_temp = {}
        last_temp['typeof'] = 'dummy'                                       # may be anything
        if 'lastTempAge' not in SMBreason:                                  # some Dexcom CGM error
            origcob.append(round(meal_data['mealCOB'], 1))
            SMBreason['lastTempAge'] = 0                                    # most frequent value as my best case
            if 'variable_sens' not in smb:
                SMBreason['origISF'] = profile['sens']                      # take from profile
            Fcasts = {}
            #Fcasts['BZ_ISF'] = profile['sens'] 
            #Fcasts['Delta__ISF'] = profile['sens'] 
            Fcasts['emulISF'] = profile['sens'] 
        else:
            origcob.append(round(suggest['COB'], 1))
            #log.write('  COB   =' + str(cob) + '\n')
            #iob.append(round(suggest['IOB']*10, 1))    # done in iob-data
        Fcasts = getOrigPred(suggest['predBGs'])
        last_temp['date']   = thisTime - SMBreason['lastTempAge'] *60*1000  # copy from original logfile
        last_temp['rate']   = currenttemp['rate']
        last_temp['duration'] = currenttemp['duration']
        iob_data['lastTemp']= last_temp
        lastBasal.append(currenttemp['rate'])
        
        log = open(ce_file, 'a')
        #og.write('\n========== '+varLabel+' loop in row ' + str(lcount) +' ========== of logfile '+fn+'\n')
        log.write('\n========== loop in row ' + str(lcount) +' ========== of logfile '+fn+'\n')
        log.write('  created at= ' + stmp +'\n')
        log.write('---------- Script Debug --------------------\n')
        log.close()
        #tempBasalFunctions = set_tempBasalFunctions()  # look up in profile
        reservoir = 47                                  # currently fixed
        tempBasalFunctionsDummy = ''                    # is handled inside determine_basal as import
        origInsReq.append(ins_Req)
        origISF.append(SMBreason['origISF'])
        varlog.write('\nloop execution in row='+str(lcount)+' of logfile '+fn+' at= ' + stmp + '\n')
        #longDelta.append(round(glucose_status['long_avgdelta'],2))
        if 'dura_ISF_minutes' not in glucose_status:        # calculate it in emulator
            delta05, avg05 = getHistBG(len(bg)-1, 0.05)
        else:                                               # use master results
            delta05 = glucose_status['dura_ISF_minutes']     # for the time being keep name from 1ast attempt
            avg05  = glucose_status['dura_ISF_average']
        glucose_status['dura05'] = delta05              # for the time being keep name from 1ast attempt
        glucose_status['avg05']  = avg05
        longDelta.append(round(delta05, 2))
        avgDelta.append(round(avg05, 2))
        if delta05<100 or True:                         # no risk of singularity, get linear regression; restriction not needed?
            dura70, slope70, slopes, iMax = getSlopeBG(len(bg)-1)
            #print('\n')
            for ele in slopes:
                a0 = slopes[ele]['a0']
                a1 = slopes[ele]['a1']
                #tx = time.strptime(stmp[11:19], '%H:%M:%S') - time.strptime('00:00:00', '%H:%M:%S')    #bgTime[-1]     # bgTime[bgFrame]    # no forecast: +5*60
                #t1 = tx
                #t2 = tx - 1/(slopes[ele]['dur'])    # *60 #bgTime[bgFrame]
                bg1= a0 + a1* 0/300
                bg2= a0 - a1* slopes[ele]['dur']*60/300
                #print(stmp[11:19], ele, str(slopes[ele]), str(slopes[ele]['dur']/3600/24), str(bg1), str(bg2))
                
            glucose_status['lin_fit_minutes'] = dura70
            glucose_status['lin_fit_a1'] = slope70
            if iMax == -1:
                glucose_status['lin_fit_correlation'] = 0
            else:
                #if iMax == 635:
                #    print (stmp, str(slopes))
                glucose_status['lin_fit_correlation'] = slopes[iMax]['corr']
            longSlope.append(round(dura70, 2))
            rateSlope.append(round(slope70, 2))
            glucose_status['delta05'] = getDeltaBG(slopes, 7.5)
            glucose_status['delta15'] = getDeltaBG(slopes,17.5)
            glucose_status['delta40'] = getDeltaBG(slopes,42.5)
            #
            #print(stmp, str(glucose_status))
            pass
        else:
            longSlope.append(0.0)
            rateSlope.append(0.0)
        #print('row', str(lcount), 'deltas', str(len(longDelta)), str(longDelta), '\nslopes', str(len(longSlope)), str(longSlope))
        #Fcasts = getOrigPred(suggest['predBGs'])
        Flows  = []
        #print('\n'+str(loop_label), '\n'+str(glucose_status))
        if setVariant(stmp):        return 'SYNTAX'     # syntax problem in VDF file
        
        #if profile['new_parameter']['bestParabola']:       dura_p, delta_p, parabs, iMax = getBestParabolaBG(len(bg)-1)
        if isAndroid:
            msgFile = 'Scanning active logfile'
        else:
            msgFile = 'Scanning logfile '+fn       
        log_msg(msgFile + ',  loop time stamp '+stmp,'\r')
        reT = detSMB.determine_basal(glucose_status, currenttemp, iob_data, profile, autosens_data, meal_data, tempBasalFunctionsDummy, MicroBolusAllowed, reservoir, thisTime, Fcasts, Flows, emulAI_ratio)
        #newLoop = False
        if len(origAI_ratio)<len(emulAI_ratio):
            origAI_ratio.append(10.0)                   # not found in original console_error
        reason = echo_rT(reT)                           # overwrite the original reason
        maxBolStr = getReason(reason, 'maxBolus', '. ', 1)
        if len(maxBolStr) > 5 :
            maxBolStr = getReason(reason, 'maxBolus',  '; ', 1)
        if maxBolStr == '' :     maxBolStr = '0'
        emulMaxBolus.append(eval(maxBolStr))
        mySMBstr = getReason(reason, 'Microbolusing', 'U',  1)
        if mySMBstr == '' :     mySMBstr = '0'
        emulSMB.append(round(eval(mySMBstr),2))         # allow <=0.1 as minimum dose
        BZ_ISF.append(Fcasts['BZ_ISF'])                 # was set in determine_basal.py
        Delta_ISF.append(Fcasts['Delta_ISF'])           # was set in determine_basal.py
        pp_ISF.append(Fcasts['pp_ISF'])                 # was set in determine_basal.py
        acceISF.append(Fcasts['acceISF'])               # was set in determine_basal.py
        dura_ISF.append(Fcasts['dura_ISF'])             # was set in determine_basal.py
        emulISF.append(Fcasts['emulISF'])               # was set in determine_basal.py
        emuliobTH.append(Fcasts['emuliobTH'])           # was set in determine_basal.py
        tolerance_iobTH.append(Fcasts['emuliobTH']*1.3) # 30% overrun tolerated

        if reason.find('COB: 0,') == 0: 
            Fcasts['COBpredBGs'] = []                   # clear array if COB=0
        Pred[round(thisTime/1000,1)] = Fcasts
        FlowChart[round(thisTime/1000,1)] = Flows
        #print("saved Fcast", str(len(Pred)), " for", stmp, str(thisTime), "with key", str(round(thisTime/1000,1)))
        #for ele in Fcasts:
        #    print("  ", str(ele))
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
    global SMBreason, origAI_ratio, autoISF_version
    key_str = ']:'
    what_anf = zeile.find(key_str)
    what = zeile[what_anf+len(key_str)+1:]
    if isZip:       what += '\n'
    #print('  entered prepSMB with'+zeile+'\n    from '+str(what_anf)+ ' appending '+what)
    SMBreason['script'] += what
    wo_colon = what.find(': ')
    if what.find('SMB enabled')==0:
        SMBreason['rowON'] = lcount
        SMBreason['whyON'] = what[:-1]
    elif what.find('start autoISF') >=0:                # version of autoISF
        #print('found version info in', what)
        wo = what.find('ISF ')
        autoISF_version = what[wo:]
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
        #print('lastTempAge', str(SMBreason['lastTempAge']), 'found in row', str(lcount), 'from', what)
    elif what.find('ISF unchanged:')==0:                # first reference
        SMBreason['origISF'] = eval(what[wo_colon+2:-1])
        #print (str(lcount), str(origISF))
    elif what.find('ISF from ')==0:                     # here, insert the original autosens modified line handling
        isf_anf = what.find(' to ')
        SMBreason['origISF'] = eval(what[isf_anf+4:-1])
        #print (str(lcount), str(origISF))
    elif what.find('profile.sens:')==0:                 # redefine it
        isf_anf = what.find(' sens:')
        isf_end = what.find(' CSF:')
        SMBreason['origISF'] = eval(what[isf_anf+6:isf_end])
        #print (str(lcount), str(origISF))
    elif what.find('final ISF factor is') ==0:          # result of autoISF
         final_ISF_string = what[20:]
         wo = final_ISF_string.find(' ')                # origin sens can  be appended
         if wo<1:       wo = len(final_ISF_string)
         if final_ISF_string[:wo] == "NaN":
            origAI_ratio.append(1.0*10)
         else:
            origAI_ratio.append(eval(final_ISF_string[:wo])*10)
    pass

def featured(Option):
    # check whethter this feature was in the option list passed from OO.odb
    # or if ALL option were enabled
    # otherwise FALSE
    OK = 'All' in doit  or Option in doit
    if '-'+Option in doit:        OK = False            # explicitly excluded
    return OK

def get_glucose_status(lcount, st) :                    # key = 80
    key = 'GlucoseStatus'
    wo = st.find(key)
    if wo>0:        # APS3.3-dev format
        Curly= st[wo+len(key):]
    else:
        Curly = st[16:]
    global glucose_status
    global bg, bgTime, deltas
    global newLoop
    newLoop = True
    #print('vorher: ', Curly+'/')
    if Curly[0]=='(':       # Milos new non-json format
        if Curly[-1] != ')':     Curly  = Curly[:-1]
        Curly = ' ' + Curly[1:-1].replace('=', '":')
        Curly = Curly.replace(' ', '"')
        Curly = Curly.replace('shortAvgDelta', 'short_avgdelta')
        Curly = Curly.replace('longAvgDelta', 'long_avgdelta')
        Curly = Curly.replace('duraISFminutes', 'dura_ISF_minutes')
        Curly = Curly.replace('duraISFaverage', 'dura_ISF_average')
        Curly = Curly.replace('parabolaMinutes', 'parabola_fit_minutes')
        Curly = Curly.replace('deltaPl', 'parabola_fit_last_delta')
        Curly = Curly.replace('deltaPn', 'parabola_fit_next_delta')
        Curly = Curly.replace('corrSqu', 'parabola_fit_correlation')
        Curly = Curly.replace('a0', 'parabola_fit_a0')
        Curly = Curly.replace('a1', 'parabola_fit_a1')
        Curly = Curly.replace('a2', 'parabola_fit_a2')
        Curly = Curly.replace('bgAcceleration', 'bg_acceleration')
        Curly = '{' + Curly + '}'
        #print('nachher:', Curly)
    glucose_status = json.loads(Curly)
    glucose_status['row'] = lcount
    #print('entered glucose_status for row='+str(lcount)+'  loop_mills='+'loop_mills[-1]' + '  total count='+str(len(bg))+' with\n '+Curly)
    #print('\n\n'+str(glucose_status))
    #print('entered glucose_status for row='+str(lcount)+'  total mills='+str(len(loop_mills))+ '  total BGs='+str(len(bg))+' with\n '+Curly)
    #print('='*20)
    #if len(bg)==len(loop_mills) :
    bg.append(glucose_status['glucose'])            # start next iteration
    mills = glucose_status['date']/1000             # time of bg value in seconds; was milliseconds
    for i in range(100):                            # in case the loop is executed 100 times before next CGM
        mills = round(mills+0.0001,4)
        if mills not in deltas:    break            # use bg_time with very small offset
    bgTime.append(mills)                            # time of bg value in seconds; was minutes
    #print('after append in glucose', str(bgTime))
    deltas[mills] = {'bg':glucose_status['glucose'], 'delta':glucose_status['delta'], 'short':glucose_status['short_avgdelta'], 'long':glucose_status['long_avgdelta']}
    if 'dura_ISF_minutes' not in glucose_status:
        mins, averg = getHistBG(len(bg)-1, 0.05)
        glucose_status['dura_ISF_minutes'] = mins
        glucose_status['dura_ISF_average'] = averg
    if 'parabola_fit_minutes' not in glucose_status or 'FSL_min_dur' in new_parameter:
        dura_p, delta_p, parabs, iMax = getBestParabolaBG(len(bg)-1)
        if iMax>= 0:
            glucose_status['parabola_fit_minutes']      = round(parabs[iMax]['dur'], 1)
            glucose_status['parabola_fit_correlation']  = parabs[iMax]['corr']
            glucose_status['bg_acceleration']           = parabs[iMax]['a2'] * 2
            glucose_status['parabola_fit_last_delta']   = parabs[iMax]['a1'] - parabs[iMax]['a2']
            glucose_status['parabola_fit_next_delta']   = parabs[iMax]['a1'] + parabs[iMax]['a2']
            glucose_status['parabola_fit_a0']           = parabs[iMax]['a0']
            glucose_status['parabola_fit_a1']           = parabs[iMax]['a1']
            glucose_status['parabola_fit_a2']           = parabs[iMax]['a2']
            #print('   fit set:', str(glucose_status))
        else:   # no fit
            glucose_status['parabola_fit_correlation']  = 0
            glucose_status['bg_acceleration']           = 0
            glucose_status['parabola_fit_a2']           = 0
            #print('no fit set:', str(glucose_status))
    if 'parabola_fit_minutes' in glucose_status:
        deltas[mills]['parabola_fit_minutes']    = glucose_status['parabola_fit_minutes']
        deltas[mills]['parabola_fit_correlation']= glucose_status['parabola_fit_correlation']
        deltas[mills]['parabola_fit_last_delta'] = glucose_status['parabola_fit_last_delta']
        deltas[mills]['parabola_fit_next_delta'] = glucose_status['parabola_fit_next_delta']
    #if len(bg)!=len(loop_mills) :
    #    #print('before overwrite:\n'+str(loop_mills) + '\n'+str(bg) + '\n'+str(bgTime))
    #    #bg[-1] = (glucose_status['glucose'])            # overwrite as last loop was not finished
    #    #bgTime[-1] = (glucose_status['date']/1000)      # time of bg value in seconds; was minutes
    #    #print('after overwrite:\n'+str(loop_mills) + '\n'+str(bg) + '\n'+str(bgTime))
    #    #print ('\nbg data found in row '+str(lcount)+', total count='+str(len(bg)))
    #    if mills>=1684843012 and mills<=1684843013:
    #        print('deltas at '+str(mills), str(deltas[mills]))
    pass

def get_iob_data(lcount, st, log, stampStr) :                     # key = 81
    if not newLoop: return
    global iob_data, utcOffset
    global activity
    global AAPS_Version
    if AAPS_Version != '3.3' and st.find('netbasalinsulin')>0:
        AAPS_Version = '3.3'    # missed other sings
        return                  # wait for DATABASE RECORD
    if AAPS_Version == '3.3':     
        Curly = st
    else:        
        key = 'CurrentTemp'
        wo = st.find(key)
        if wo>0:        # APS3.3-dev format
            Curly= st[wo+len(key):]
        else:
            Curly = st[16:]
        if not isZip:
            st = st[:-1]                               # drop the <CRLF>
        key = 'IobTotal'
        wo = st.find(key)
        if wo>0:        # older APS3.3-dev format
            Curly= st[wo+len(key):]
        else:
            Curly = st[16:]
        #print('\nvorher: ', Curly[:165])
        if Curly[0]=='(':       # Milos new non-json format
            Curly = ' ' + Curly[1:-1].replace('=', '":')
            Curly = Curly.replace('), ', '},"')
            Curly = Curly.replace(' ', '"')
            Curly = Curly.replace('IobTotal', '')
            Curly = Curly.replace('(', '{"')
            #Curly = Curly.replace('duraISFaverage', 'dura_ISF_average')
            #Curly = Curly.replace('parabolaMinutes', 'parabola_fit_minutes')
            #Curly = Curly.replace('deltaPl', 'parabola_fit_last_delta')
            #Curly = Curly.replace('deltaPn', 'parabola_fit_next_delta')
            Curly = Curly.replace('"{', '{')
            Curly = '[{' + Curly + '}]'
            #print('nachher:', Curly[:170])
            #print('400-420:/'+ Curly[:420] +'/')
    iob_array = json.loads(Curly)
    iob_data = {}
    iob_data['typeof']  = 'dummy'                       # may be anything
    # get first record as current iob
    rec_0 = iob_array[0]
    if 'iob' not in rec_0:                  rec_0['iob'] = 0.0
    if 'activity' not in rec_0:             rec_0['activity'] = 0.0
    if 'lastBolusTime' not in rec_0:        rec_0['lastBolusTime'] = 0
    for ele in rec_0 :
        if ele != 'iobWithZeroTemp':        iob_data[ele] = rec_0[ele]
        if ele == 'iob':
            act = rec_0[ele]
            if len(origiob) ==len(loop_mills):
                origiob.append(act*10)
                #print('  appended', str(origiob[-1]), 'to iorigiob')
            else:
                origiob[-1] = (act*10)
                #print('  overwritten', str(origiob[-1]), 'to iorigiob')
        elif ele == 'activity':
            act = rec_0[ele]
            if len(activity) ==len(loop_mills):
                activity.append(act*1000)
            else:
                activity[-1] = (act*1000)
        elif ele == 'time':
            if AAPS_Version != '3.3':
                #print('\niob time: '+ rec_0[ele][11:19], ' loop time:'+ stampStr)
                hourOffset = eval('1' + stampStr[0:2]+ '-1' + rec_0[ele][11:13])
                minuteOffset = eval('1' + stampStr[3:5] + '-1' + rec_0[ele][14:16])
                utcOffset = round(hourOffset + minuteOffset/60, 0)
                if   utcOffset >13:     utcOffset -= 24
                elif utcOffset<-12:     utcOffset += 24
                #print('\niob time: '+ rec_0[ele][11:19], ' loop time:'+ stampStr, ' UTC offset: '+str(utcOffset))
                #print('in get_iob_data', str(type('utcOffset')))
                pass
    iob_data['iobArray']= iob_array
    iob_data['utcOffset'] = utcOffset
    #print ('preliminary iob data json -->       '+str(lcount) +' : '+ str(iob_data))
    #for ele in iob_array:
    #    log.write(str(ele)+':'+'\n')
    #print ('iob data found in row '+str(lcount)+', total count='+str(len(iob_data)), str(len(origiob)))
    pass

def get_currenttemp(lcount, st) :                       # key = 82
    if not newLoop: return
    if AAPS_Version == '3.3':  
        Curly = st
    else:        
        key = 'CurrentTemp'
        wo = st.find(key)
        if wo>0:        # APS3.3-dev format
            Curly= st[wo+len(key):]
        else:
            Curly = st[16:]
    global currenttemp
    #print('vorher: ', Curly)
    if Curly[0]=='(':       # Milos new non-json format
        #print('step 0:', Curly[len(Curly)-1:])
        if Curly[-1] != ')':     Curly  = Curly[:-1]
        #print('step 1:', Curly)
        Curly = ' ' + Curly[1:-1].replace('=', '":')
        #print('step 2:', Curly)
        Curly = Curly.replace(' ', '"')
        #print('step 3:', Curly)
        Curly = '{' + Curly + '}'
        #print('nachher:', Curly)
    currenttemp = json.loads(Curly)
    currenttemp["typeof"] ="dummy"                      # may be anything
    currenttemp["row"] = lcount
    #print ('currenttemp json -->    '+str(currenttemp))
    pass

def get_profile(lcount, st) :                           # key = 83
    global newLoop
    if not newLoop : return
    if AAPS_Version == '3.3':
        Curly = st
    else:
        key = 'OapsProfileAutoIsf'
        wo = st.find(key)
        if wo>0:        # APS3.3-dev format
            Curly= st[wo+len(key):]
        else:
            Curly = st[16:]
    global profile, profISF
    global origTarLow, origTarHig, emulTarLow, emulTarHig
    #print('\nvorher: ', Curly)
    if Curly[0]=='(':       # Milos new non-json format
        if Curly[-1] != ')':     Curly  = Curly[:-1]
        Curly = ' ' + Curly[1:-1].replace('=', '":')
        Curly = Curly.replace(' ', '"')
        Curly = Curly.replace('out_units":', 'out_units":"')
        Curly = Curly.replace('mmol/L,', 'mmol/L",')
        Curly = Curly.replace('"autoISF_version":,', '"autoISF_version":"",')       # other mode or plugin
        Curly = Curly.replace('dl,"lgsThreshold', 'dl","lgsThreshold')
        Curly = '{' + Curly + '}'
        #print('\nnachher:', Curly)
        #print('char 5:', Curly[.10])  #, str(chr(Curly[948])))
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
        profISF.append(profile['sens'])
    else:                                               # overwrite as last loop was not finished
        origTarLow[-1] = profile['min_bg']
        emulTarLow[-1] = origTarLow[-1]
        origTarHig[-1] = profile['max_bg']
        emulTarHig[-1] = origTarHig[-1]
        profISF[-1]    = profile['sens']
    #print ('master profile json in row '+str(lcount)+' --> '+str(profile))
    #print ('target data found in row '+str(lcount)+', total count loop/origTarLow='+str(len(loop_mills))+'/'+str(len(origTarLow)))
    #print ('target data', str(origTarLow), 'found in row '+str(lcount)+', total count emulTarLow='+str(len(origTarLow)))
    pass

def get_meal_data(lcount, st) :                         # key = 84
    if not newLoop: return
    if AAPS_Version == '3.3':     
        Curly = st
    else:
        key = 'MealData'
        wo = st.find(key)
        if wo>0:        # APS3.3-dev format
            Curly= st[wo+len(key):]
        else:
            Curly = st[16:]
    global meal_data
    #print('vorher: ', Curly)
    if Curly[0]=='(':       # Milos new non-json format
        if Curly[-1] != ')':     Curly  = Curly[:-1]
        Curly = ' ' + Curly[1:-1].replace('=', '":')
        Curly = Curly.replace(' ', '"')
        Curly = '{' + Curly + '}'
        #print('nachher:', Curly)
    meal_data = json.loads(Curly)
    meal_data['row'] = lcount
    # use fixed settings for the time being ...
    meal_data['bwCarbs'] = False                        # bolus wizzard carbs
    meal_data['bwFound'] = False                        # bolus wizzard used ?
    if 'mealCOB' not in meal_data:                      meal_data['mealCOB'] = 0
    if 'carbs' not in meal_data:                        meal_data['carbs'] = 0
    if 'slopeFromMinDeviation' not in meal_data:        meal_data['slopeFromMinDeviation'] = 999
    if 'slopeFromMaxDeviation' not in meal_data:        meal_data['slopeFromMaxDeviation'] = 0
    #print ('meal data json -->      '+str(meal_data))
    pass

def get_autoISF_extras(lcount, Curly):
    Curly = Curly.replace('autoISF_min".0.', 'autoISF_min":0.')     # initial formatting bug
    #print('entered get_autoISF_extras in row',str(lcount), Curly+ '/\n'+Curly[645:655])
    if not newLoop: return
    autoISF_extras = json.loads(Curly)
    global profile
    for ele in autoISF_extras:
        profile[ele] = autoISF_extras[ele]
    #print (str(profile))
    pass

def get_autosens_data(lcount, st) :                     # key = 86
    if not newLoop: return
    if AAPS_Version == '3.3':     
        Curly = st
    else:
        key = 'AutosensResult'
        wo = st.find(key)
        if wo>0:        # APS3.3-dev format
            Curly= st[wo+len(key):]
        else:
            Curly = st[16:]
    global autosens_data, profile
    global origAs_ratio, autoISF
    #print('zeile:'+str(lcount),' vorher:\n', Curly)
    if Curly[0]=='(':       # Milos new non-json format
        ratio_str = hole(Curly, 0, '=', ',')
        autosens_data = {}
        autosens_data['ratio'] = eval(ratio_str[1:-1])
        #if Curly[-1] != ')':     Curly  = Curly[:-1]
        #Curly = '"' + Curly[1:-1].replace('=', '":')
        #Curly = Curly.replace(', ', ', "')
        #Curly = Curly.replace('sensResult":', 'sensResult":"')
        #Curly = Curly.replace(', "pastSensitivity":', '", "pastSensitivity":"')
        #Curly = Curly.replace(', "ratioLimit":', '", "ratioLimit":"')
        #Curly = Curly.replace(', "ratioFromTdd', '", "ratioFromTdd')
        #Curly = '{' + Curly + '}'
        #print('nachher:\n', Curly)
    else:
        autosens_data = json.loads(Curly)
    autosens_data['typeof'] = 'dummy'                   # may be anything
    autosens_data['row'] = lcount
    if 'ratio' not in autosens_data:            autosens_data['ratio'] = 1.0
    if len(origAs_ratio) ==len(loop_mills) :
        origAs_ratio.append(autosens_data['ratio']*10)
        autoISF.append(profile['sens'] / autosens_data['ratio'])    # ISF assigned now as autoense is the last data block
    else:
        origAs_ratio[-1] = (autosens_data['ratio']*10)
        autoISF[-1] = (profile['sens'] / autosens_data['ratio'])    # ISF assigned now as autosense is the last data block
    pass

def get_AutoIsfMode(lcount, st) :
    if not newLoop: return
    global AutoIsfMode
    AutoIsfMode = (st.find('true') > 16)
    pass

def get_flatBGsDetected(lcount, st) :
    if not newLoop: return
    global flatBGsDetected
    flatBGsDetected = (st.find('true') > 16)
    pass

def get_MicroBolusAllowed(lcount, st) :                 # key = 90
    if not newLoop: return
    global MicroBolusAllowed
    #Curly = st[16:]
    MicroBolusAllowed = (st.find('true') > 16)
    pass

def ConvertSTRINGooDate(stmp) :
    # stmp is datetime string incl millis, i.e. like "2019-05-22T12:06:48.091Z"
    if   stmp < "2019-10-27T03:00:00.000Z":
         dlst = 3600                                 #    dlst period summer 2019
    elif stmp < "2020-03-29T02:00:00.000Z":
         dlst =    0                                 # no dlst period winter 2019/20
    elif stmp < "2020-10-25T03:00:00.000Z":
         dlst = 3600                                 #    dlst period summer 2020
    elif stmp < "2021-03-28T02:00:00.000Z":
         dlst =    0                                 # no dlst period winter 2020/21
    elif stmp < "2021-10-31T03:00:00.000Z":
         dlst = 3600                                 #    dlst period summer 2021
    elif stmp < "2022-03-27T02:00:00.000Z":
         dlst =    0                                 # no dlst period winter 2021/22
    elif stmp < "2022-10-30T03:00:00.000Z":
         dlst = 3600                                 #    dlst period summer 2022
    elif stmp < "2023-03-26T02:00:00.000Z":
         dlst =    0                                 # no dlst period winter 2022/23
    elif stmp < "2023-10-26T03:00:00.000Z":
         dlst = 3600                                 #    dlst period summer 2023
    elif stmp < "2024-03-31T02:00:00.000Z":
         dlst =    0                                 # no dlst period winter 2023/24
    else:
         dlst = 3600                                 #    dlst period summer 2024
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
    NumericDate= datetime.datetime(MSJahr, MSMonat, MSTag, MSStunde, MSMinute, MSSekunde, MSmillis*1000, timezone.utc)  # keep it in UTC
    #imestamp = NumericDate.replace(tzinfo=timezone.utc).timestamp() + 3600 # 1h MEZ offset
    #print('entered Convert.. with stmp='+stmp+'\n  NumericDate='+str(NumericDate))
    timestamp = int( (NumericDate.timestamp() + 3600*0 + dlst*0) * 1000 )       # keep it in UTC; was 1h MEZ offset
    #print("Eingang: " + stmp + "\nAusgang: " + str(timestamp) )
    return timestamp

def scanLogfile(fn, entries):
    global SMBreason
    global xyf
    global fn_base                              # keep first match in case of wild card file list
    global log
    global varlog
    global newLoop
    global dataType_offset, AAPS_Version
    global CarbReqGram,  CarbReqTime, lastCOB
    
    if not newLoop:                             # otherwise continued from provious logfile
        SMBreason = {}
        SMBreason['script'] = '---------- Script Debug --------------------\n'
        #dataType_offset = 1                    #################### used for V2.6.1
    if filecount == 0 :                         # initalize file loop
        dataType_offset = -999                  # AAPS version not yet known
        AAPS_Version = '<2.7'
        #fn_base=      fn + '.' + varLabel
        pdfCleared = False
        while True:                                                                 # wait if old pdf is still loaded in pdf viewer
            try:
                os.remove(fn_first + '.' + varLabel + '.csv')
                if pdfCleared:    log_msg('continuing ...')
                break
            except PermissionError:
                asleep = 10
                log_msg('\nYour CSV-file seems blocked by other process. Checking again in '+str(asleep)+' sec.'+chr(7)) # sometimes I can hear that BELL
                time.sleep(asleep)
                pdfCleared=True
            except FileNotFoundError:
                break
        xyf     = open(fn_first + '.' + varLabel + '.csv', 'w')
        log     = open(fn_first + '.orig.txt', 'w')
        varlog  = open(fn_first + '.' + varLabel + '.log', 'w')
        varlog.write(echo_msg)
    varlog.write('\n========== Echo of what-if definitions actioned for variant '+varLabel+'\n========== created on '+formatdate(localtime=True) + '\n========== for loop events found in logfile '+fn+'\n')
    log.write('AAPS scan from AAPS Logfile for SMB comparison created on ' + formatdate(localtime=True) + '\n')
    log.write('FILE='+fn + '\n')
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
    sequenceBLANK = 0                           # needed for AIMI
    while notEOF:                               # needed because "for zeile in lf" does not work with AAPS 2.5
        try:                                    # needed because "for zeile in lf" does not work with AAPS 2.5
            while True:
                try:
                    zeile = lf.readline()       # needed because "for zeile in lf" does not work with AAPS 2.5
                    break
                except FileNotFoundError:
                    if isAndroid:               # assume old logfile is recycled; wait for new one
                        try:
                            lf.Close()
                        except:
                            pass                # was already closed / had disappeared
                        log_msg('\nwaiting 10s for logfile housekeeping')
                        time.sleep(10)
                        lf = open(fn, 'r')
            if isZip:   zeile = str(zeile)[2:-3]# strip off the "'b....'\n" remaining from the bytes to str conversion
            #if zeile == '':                     # needed because "for zeile in lf" does not work with AAPS 2.5
            #    notEOF = False                  # needed because "for zeile in lf" does not work with AAPS 2.5
            #    break                           # needed because "for zeile in lf" does not work with AAPS 2.5
            if zeile == '':                     # needed for AIMI
                sequenceBLANK +=1               # needed for AIMI
                if sequenceBLANK >10:           # needed for AIMI
                    notEOF = False              # needed for AIMI
                    break                       # needed for AIMI
            else:                               # needed for AIMI
                sequenceBLANK = 0               # needed for AIMI
                
            lcount +=  1
            #print(zeile)
            if lcount>100000:  
                sub_issue('no end found at row '+str(lcount)+ ' reading /'+zeile+'/')
                return 'STOP'
            if len(zeile)>13:
                headerKey = zeile[2] + zeile[5] + zeile[8] + zeile[12]
                if headerKey == '::. ':
                    sLine = zeile[13:]
                    Action = hole(sLine, 0, '[', ']')
                    sOffset = len(Action)
                    Block2 = hole(sLine, 1+sOffset, '[', ']')
                    if Block2 == '[DataService.onHandleIntent():54]' \
                    or Block2 == '[DataService.onHandleIntent():55]' \
                    or Block2 == '[DataService.onHandleIntent():69]':               # token :54 added for AAPS versions <2.7, :69 for V2.7
                        pass
                    elif Block2[:-3] == '[DetermineBasalAdapterAMAJS.invoke():':                                                   # various input items for loop
                        log_msg('\nSorry, this tool is currently only available for oref1 with SMB\n')
                        return 'STOP'
                    elif re.match(r"\[DetermineBasalAdapter[A-Za-z]+\.invoke\(\)", Block2) \
                      or re.match(r"\[OpenAPSAutoISFPlugin\.invoke\(\)", Block2) \
                      or re.match(r"\[OpenAPSSMBPlugin.invoke\(\)", Block2):  # loop inputs or result record
                        key_anf = Block2.find('):')
                        key_end = Block2.find(']:')
                        dataType= eval(Block2[key_anf+2:key_end])
                        dataStr = sLine[sLine.find(']: ')+3:]
                        dataTxt = dataStr[:17]                              # make it dataTxt based rather than dataType (more robust)
                        if dataType_offset <-99 and newLoop:                            # not yet initialized for known AAPS version
                            if   dataType == 75 \
                            and newLoop :                                   # V 2.3 ?
                                log_msg('\nSorry, cannot extract required data from logfiles before AAPS version 2.5\n')
                                return 'STOP'
                            dataType_offset = dataType-79                   # "0" was lowest in V2.5.1
                            if dataType_offset >= 15:                       AAPS_Version = '2.7'    # same as 2.8
                            elif dataType_offset < 0:                       AAPS_Version = '2.7'    # same as 3.0
                            elif dataType_offset >=2:                       AAPS_Version = '2.7'    # v 3.2
                            #elif dataType == 79:    dataType_offset =  0    # V 2.5.1
                            #elif dataType == 80:    dataType_offset =  1    # V 2.6.1
                            #elif dataType == 94:    dataType_offset = 15    # V 2.8.0    >>> Invoking detemine_basal <<< / Wolfgang Spänle
                            #elif dataType == 98:    dataType_offset = 19    # V 2.8.0    >>> Invoking detemine_basal <<< / Phillip
                            #elif dataType == 97:
                            #                        dataType_offset = 18    # V 2.7
                            #                        AAPS_Version = '2.7'
                            #elif dataType == 108:   pass                    # V 2 7:     MicroBolusAllowed:  true
                            #elif dataType == 109:   pass                    # V 2 7:     SMBAlwaysAllowed:  true
                            #elif dataType == 110:   pass                    # V 2 7:     CurrentTime: 1604776609511
                            #elif dataType != 163:   print('unhandled dataType:', str(dataType), 'row', str(lcount), 'of file',fn) # any but 2.7 RESULT
                            #version_set = True                              # keep until next logfile is loaded
                            pass
                        if Block2.find('AutoISF')>0:                         AAPS_Version = '3.3'    # during dev only?
                        #print('AAPS versoin:', AAPS_Version, '   found:', dataTxt)
                        if   dataTxt[:16] == 'RhinoException: ' :           code_error(lcount, dataStr)
                        elif dataTxt[:16] == 'Glucose status: ' :           get_glucose_status(lcount, dataStr)
                        elif dataTxt[:16] == 'IOB data:       ' and AAPS_Version!='3.3':     get_iob_data(lcount, dataStr, log, zeile[:8])
                        elif dataTxt[:16] == 'Current temp:   ' and AAPS_Version!='3.3':     get_currenttemp(lcount, dataStr)
                        elif dataTxt[:16] == 'Profile:        ' and AAPS_Version!='3.3':     get_profile(lcount, dataStr)
                        elif dataTxt[:16] == 'Meal data:      ' and AAPS_Version!='3.3':     get_meal_data(lcount, dataStr)
                        elif dataTxt[:16] == 'Autosens data:  ' and AAPS_Version!='3.3':     get_autosens_data(lcount, dataStr)
                        elif dataTxt      == 'AutoIsfMode:     ' :          get_AutoIsfMode(lcount, dataStr)
                        elif dataTxt      == 'flatBGsDetected: ' :          get_flatBGsDetected(lcount, dataStr)
                        elif dataTxt      == 'MicroBolusAllowed' :          get_MicroBolusAllowed(lcount, dataStr)
                        #elif dataTxt     == 'Result: RT(algori' :          cont = TreatLooop33(dataStr, log, lcount, fn)
                        elif dataTxt[:16] == 'AutoISF extras: ' :           get_autoISF_extras(lcount, hole(sLine, 1+sOffset+len(Block2), '{', '}'))
                        elif dataTxt      == 'Result: {"temp":"' :
                                                                            checkCarbsNeeded(dataStr[8:], lcount)   # result record in AAPS2.6.1
                                                                            cont = TreatLoop(dataStr[8:], log, lcount, fn)
                                                                            if cont=='STOP' or cont=='SYNTAX':     return cont
                        #elif dataType == dataType_offset+145:               checkCarbsNeeded(dataStr[8:], lcount)   # result record in AAPS2.7
                        #elif dataType == dataType_offset+147:               checkCarbsNeeded(dataStr[8:], lcount)   # result record in AAPS2.8 Wolfgang Spänle
                        #elif dataType == dataType_offset+146:               checkCarbsNeeded(dataStr[8:], lcount)   # result record in AAPS2.8 / Phillip
                        #else:   print('unknown', dataTxt)
                        #else:   print (str(lcount), str(dataType), str(dataType_offset), '/'+dataTxt+'/' + dataStr[17:60])
                        pass
                    elif Block2 == '[LoggerCallback.jsFunction_log():39]' \
                    or   Block2 == '[LoggerCallback.jsFunction_log():42]' \
                    or   Block2 == '[LoggerCallback.jsFunction_log():21]':          # from console.error; '42' is for >= V2.7, '21' for V3
                        PrepareSMB(sLine, log, lcount)   
                    elif Block2 == '[DbLogger.dbAdd():29]':                             ################## flag for V2.5.1
                        Curly =  hole(sLine, 1+sOffset+len(Block2), '{', '}')
                        #print('calling TreatLoop in row '+str(lcount)+' with\n'+Curly)
                        if Curly.find('{"device":"openaps:')==0:   
                            cont = TreatLoop(Curly, log, lcount, fn)
                            if cont=='STOP' or cont=='SYNTAX':     return cont
                    elif zeile.find('[NSClientPlugin.onStart$lambda-5():124]') > 0 :    ################## flag for V3.0dev
                        Curly =  hole(zeile, 5, '{', '}')
                        #print('calling TreatLoop in row '+str(lcount)+' with\n'+Curly)
                        #if  Curly.find('{"device":"openaps:')==0 \
                        #and Curly.find('"openaps":{"suggested":{')>0 :
                        if  Curly.find('"openaps":{"suggested":{')>0 :
                            #and 'lastTempAge' in SMBreason :   
                            cont = TreatLoop(Curly, log, lcount, fn)
                            if cont=='STOP' or cont=='SYNTAX':     return cont
                    elif zeile.find('[PersistenceLayerImpl$insertOrUpdateApsResult$2.apply():') > 0:
                                                                            cont = TreatLoop33(zeile, log, lcount,fn)
                                                                            if cont=='STOP' or cont=='SYNTAX':     return cont
                    #elif lcount>1400 and lcount<2000:   print('no match in row'+str(lcount)+':', Block2)
                elif zeile.find('data:{"device":"openaps:') == 0 :                      ################## flag for V2.6.1 ff
                    Curly =  hole(zeile, 5, '{', '}')
                    #print('calling TreatLoop in row '+str(lcount)+' with\n'+Curly)
                    if  Curly.find('{"device":"openaps:')==0 \
                    and Curly.find('"openaps":{"suggested":{')>0 :
                        #and 'lastTempAge' in SMBreason :   
                        cont = TreatLoop(Curly, log, lcount, fn)
                        if cont=='STOP' or cont=='SYNTAX':     return cont

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
        if not 'insulinReq' in reT:     reT['insulinReq'] = 0       # case of Dexcon CGM error
        emulInsReq.append(reT['insulinReq'])
        tempReq = basalFromEmulation(reT, lcount)
        emulBasal.append(eval(tempReq))
    else :
        log_msg ('returned "unexpected content" with ...\n  ' + str(reT))
        reason = str(reT)

    log.close()
    return reason

def BGValPlot(ax, BGcount, BGtype, BGlevel, BGedge, BGcol):
    if BGlevel+len(BGtype)/2 > 30:                                                  # otherwise BG axis scale gets funny
        BGarrow = dict(arrowstyle='-', fc=BGcol, ec=BGcol, linestyle='dotted')
        posBG   = (BGlevel, BGedge+(9+BGcount)*yRange*0.012)                        # vertical position of BG name
        posLine = (BGlevel, BGedge+thickness*2)                                     # vertical pos of fcast block end
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
    oldavg= bg[iFrame]
    sumBG = 0
    #bw = 0.05
    duramins = 0
    for i in range(iFrame, -1, -1):
        if (bgTime[iFrame] - bgTime[i])/60 - duramins > 13:   break # at least 13 mins without CGM
        if bg[i]>oldavg*(1-bw) and bg[i]<oldavg*(1+bw) :            # still in previous bw ratio range
            sumBG += bg[i]
            oldavg = sumBG / (iFrame-i+1)
            duramins = ( bgTime[iFrame] - bgTime[i] ) / 60
            #if iFrame<5:        print ('use', loop_label[i], str(oldavg), str(bg[i]))
        else:
            #if iFrame<5:        print ('break at step', str(i))
            i += 1
            break
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
            slop = slopes[use]['a1'] * 5*60 # BG increment per 5 minutes
            return round(slop, 2)
    if len(slopes)>0:
        slop = slopes[i]['a1'] * 5*60       # BG increment per 5 minutes
        return round(slop, 2)               # use last fit from record i
    else:
        return 0                            # e.g. less than 3 BG values; same as in GlucoseStatus.java

def getSlopeBG(iFrame):
    # linerar regression analysis after 
    # https://goodcalculators.com/linear-regression-calculator/ wie von der Parabel
    #bgTime = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] # test data for x
    #bg= [-3.624, -2.783, 4.299, 4.041, 9.759, 5.013, 10.187, 5.475, 6.46, 11.307] # test data for y=a + x*b
    if iFrame < 2:         return 0,0, {}, -1   # first 2 points make a trivial line

    corrMin = 0.85                          # skip correlation coefficient below
    corrMax = 0.0
    sumBG   = 0                             # y
    sumt    = 0                             # x
    sumBG2  = 0                             # y^2
    sumt2   = 0                             # x^2
    sumxy   = 0                             # x*y-axis
    slopes  = {}
    scaleTime =   1                         # in sec; values are 0, 300, 600, 900, 1200, ... while testing
    scaleTime = 300                         # in 5m; values are  0,   1,   2,   3,    4, ...
    scaleBg   =   1                         # TIR range is now  70 - 180                 ... while testing
    scaleBg   =  50                         # TIR range is now 1.4 - 3.6

    for i in range(iFrame, -1, -1):
        ti       = (bgTime[i] -bgTime[iFrame])/scaleTime      # time offset to make the numbers smaller for numerical accuracy
        bgi      = bg[i]/scaleBg
        sumt    += ti
        sumt2   += pow(ti, 2)
        sumBG   += bgi
        sumBG2  += pow(bgi, 2)
        sumxy   += ti * bgi
        n = iFrame - i + 1
        #print(str(sumt), str(sumt2), str(sumBG), str(sumBG2), str(sumxy))
        dividend = n*sumxy - sumt*sumBG
        divisor  = (n*sumt2 - pow(sumt,2)) * (n*sumBG2 - pow(sumBG,2))
        if divisor != 0:    # otherwise DIV ZERO in r_sq
            r_sq    = pow(dividend,2) / abs(divisor)
            dur     = -ti*scaleTime/60    #(bgTime[iFrame]-bgTime[i])/60
            if r_sq < corrMin or dur>120:      break  # correlation deteriorating and window too long

            b       = dividend / (n*sumt2 - pow(sumt,2))
            a       = ( sumBG - b*sumt) / n 
            if i<iFrame-1:      
                if r_sq>=corrMin:
                    slopePar = dict(n=n-1, a0=a*scaleBg, a1=b*scaleBg, corr=r_sq, dur=dur)
                    slopes[i] = slopePar
                if r_sq>corrMax:
                    corrMax = r_sq
                    iMax = i
                    dura70  = dur                       #( bgTime[iFrame] - bgTime[i] ) / 60
                    slope70 = b * scaleBg               # 5 minute slope at best correlation
            #print ('some fit', str(n-1), str(b* scaleBg), str(a* scaleBg), str((a-b)* scaleBg), str(r_sq))
            pass
    if corrMax == 0:         return 0,0, slopes, -1   # no good correlation found
    #print('found these deltas')
    #for i in slopes:    print(str(i), str(slopes[i]))
    #print('selected deltas are', str(getDeltaBG(slopes,7.5)), str(getDeltaBG(slopes,17.5)), str(getDeltaBG(slopes,42.5)))
    return round(dura70,0), round(slope70,1), slopes, iMax

def getBestParabolaBG(iFrame):
## nach https://goodcalculators.com/quadratic-regression-calculator/
##  und zur Eingabe von Beispieldaten
##
## bzw. fehlerfrei die D.. Variante
## nach https://www.codeproject.com/Articles/63170/Least-Squares-Regression-for-Quadratic-Curve-Fitti
##
##  y = a2*x^2 + a1*x + a0      or      
##  y = a*x^2  + b*x  + c       respectively

    if 'FSL_min_dur' in new_parameter:
        FSL_min_dur = new_parameter['FSL_min_dur']
    else:
        FSL_min_dur = 10                    # duration must be longer if BG measured by the minute
    if iFrame<3 or bgTime[iFrame]-bgTime[0] <= FSL_min_dur*60:  return 0,0, {}, -1    # first 3 points make a trivial parabola
    
    corrMin = 0.90                          # go backwards until the correlation coefficient goes below
    sy    = 0                               # y
    sx    = 0                               # x
    sx2   = 0                               # x^2
    sx3   = 0                               # x^3
    sx4   = 0                               # x^4
    sxy   = 0                               # x*y
    sx2y  = 0                               # x^2*y
    parabs  = {}
    corrMax = 0
    sum_of_squares = 0
    # for best numerical accurarcy time and bg must be of same order of magnitude
    global scaleTime, scaleBg
    scaleTime =   1                         # in sec; values are 0, 300, 600, 900, 1200, ... while testing
    scaleTime = 300                         # in 5m; values are  0,   1,   2,   3,    4, ...
    scaleBg   =   1                         # TIR range is now  70 - 180                 ... while testing
    scaleBg   =  50                         # TIR range is now 1.4 - 3.6
    #print(str(bg), '\n', str(bgTime))

    for i in range(iFrame, -1, -1):
        #if bgTime[iFrame] - bgTime[i] > 45*60:      break              # range not longer than 45m
        ti     = (bgTime[i] -bgTime[iFrame])/scaleTime      # time offset to make the numbers smaller for numerical accuracy
        if -ti*scaleTime > 47*60:      break                # range not longer than 47m

        sx    += ti
        sx2   += pow(ti, 2)
        sx3   += pow(ti, 3)
        sx4   += pow(ti, 4)
        sy    +=              bg[i]/scaleBg
        sxy   += ti         * bg[i]/scaleBg
        sx2y  += pow(ti, 2) * bg[i]/scaleBg
        n = iFrame - i + 1
        #print (str(sx), str(sy), str(sxy), str(sx2), str(sx3), str(sx4), str(sx2y))
        if n<=3 or bgTime[iFrame]-bgTime[i] <= FSL_min_dur*60:
            D=0.0                               # no fits for less than 4 points or less than 10 minutes
        else:
            #D = sx4*(sx2*n-sx*sx) -  sx3*(sx3*n -sx*sx2) + sx2*(sx3*sx-sx2*sx2)
            D  = sx4*(sx2*n-sx*sx) -  sx3*(sx3*n -sx*sx2) + sx2*(sx3*sx-sx2*sx2)
            #a = sx2y*(sx2*n-sx*sx) - sxy*(sx3*n -sx*sx2) + sy* (sx3*sx-sx2*sx2)
            Da = sx2y*(sx2*n-sx*sx) - sxy*(sx3*n -sx*sx2) + sy* (sx3*sx-sx2*sx2)
            #b = sx4* (sxy*n-sy*sx) - sx3*(sx2y*n-sy*sx2) + sx2*(sx2y*sx-sxy*sx2)
            Db = sx4* (sxy*n-sy*sx) - sx3*(sx2y*n-sy*sx2) + sx2*(sx2y*sx-sxy*sx2)
            #c = sx4*(sx2*sy-sx*sxy)- sx3*(sx3*sy-sx*sx2y)+ sx2*(sx3*sxy-sx2*sx2y)
            Dc = sx4*(sx2*sy-sx*sxy)- sx3*(sx3*sy-sx*sx2y)+ sx2*(sx3*sxy-sx2*sx2y)
        if D != 0.0:  
            a = Da/D
            b = Db/D
            c = Dc/D

            # ---   get the correlation coefficient -----------------------------
            y_mean = sy / n
            s_squares = 0
            s_residual_squares = 0
            for j in range(i, iFrame+1):
                s_squares          += (bg[j]/scaleBg - y_mean)**2
                bg_j                = a*((bgTime[j]-bgTime[iFrame])/scaleTime)**2 + b*(bgTime[j]-bgTime[iFrame])/scaleTime + c
                s_residual_squares += (bg[j]/scaleBg - bg_j)**2
                #print('a='+str(a), 'b='+str(b), 'c='+str(c), 'bg_j='+str(bg_j))

            if s_squares == 0.0:
                #print (loop_label[iFrame], 'has', str(s_residual_squares), 'in subloop', str(i))
                r_sq = 0.64
            else:
                r_sq = 1 - s_residual_squares/s_squares
                #print('y_mean='+str(y_mean), ' squ='+str(s_squares), ' res='+str(s_residual_squares), ' R2='+str(r_sq))
            
            dur     = -ti*scaleTime/60    #(bgTime[iFrame]-bgTime[i])/60
            #print(loop_label[i], 'with', str(n), 'elements has   a =', str(a),' b=', str(b), ' c=', str(c))
            #print (i, loop_label[i], str(bgTime[i]), str(bg[i]), str(dur))
            #if r_sq < corrMin :      break  # correlation too bad 

            if i<=iFrame-2:      
                if r_sq>0:   parabs[i] = dict(n=n-1, a2=a*scaleBg, a1=b*scaleBg, a0=c*scaleBg, corr=r_sq, dur=dur)
                if r_sq>corrMax:
                    corrMax = r_sq
                    iMax = i
                    dura_p  = dur   #( loop_mills[iFrame] - loop_mills[i] ) / 60
                    delta_p = scaleBg*( a*(pow(5*60/scaleTime,2)) + b*(5*60/scaleTime) )    # 5 minute slope to next forecast
            #print ('some fit', str(n-1), str(b), str(a),str(r_sq))
    if corrMax == 0:         return 0,0, parabs, -1   # no good correlation found
    #print('found these parabolas for time', loop_label[iFrame])
    #for i in parabs:    print(str(i), str(parabs[i]))
    #print('selected parabola', str(iMax), 'has forecast', str(dura_p), str(round(delta_p,1)))
    return dura_p, delta_p, parabs, iMax

def populateColumn(tLast, array, weight, iFirst, loopCount):
    # e.g.  tLast = f'target      {emulTarHig[iLast]:>6}'
    for col in range(loopCount-2, iFirst, -1) :
        val = array[col] * weight
        if weight != 1:     val = round(val,2)          # was autosense
        tLast += f'{val:>10}'
    return tLast

def getBgTimeIndex(iFrame):
    # for a given loop index return the related index in bgTime
    #for bgIndex in range(iFrame, -1, -1):
    glucTime = bgTimeMap[loop_mills[iFrame]]
    LoopTime = loop_mills[iFrame]
    #print('Loop time is'+str(LoopTime), '  glucose Time is', str(glucTime))
    bgIndex = 0
    for ele in bgTime:
        if glucTime == ele: 
            break
        bgIndex += 1
    #print(str(bgTime))
    #for bgFrame in bgTime
    #print(' bgIndex is: '+str(bgIndex), ' bgTime is: '+str(bgTime[bgIndex]), str(ele))
    return bgIndex

def XYplots(loopCount, head1, head2, entries) :
    import matplotlib.pyplot as plt
    from matplotlib.animation import FFMpegWriter
    from matplotlib.backends.backend_pdf import PdfPages
    global yStep, yRange, thickness
    # ---   ensure that last loop was finished  -------------
    #f len(loop_mills) < len(bg)            :   bg.pop()            # bg  has its own vectors
    if len(loop_mills) < len(origTarLow)    :   origTarLow.pop()
    if len(loop_mills) < len(origTarHig)    :   origTarHig.pop()
    if len(loop_mills) < len(origInsReq)    :   origInsReq.pop()
    if len(loop_mills) < len(origMaxBolus)  :   origMaxBolus.pop()
    if len(loop_mills) < len(origSMB)       :   origSMB.pop()
    if len(loop_mills) < len(origBasal)     :   origBasal.pop()
    if len(loop_mills) < len(origISF)       :   origISF.pop()
    if len(loop_mills) < len(profISF)       :   profISF.pop()
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
    if len(loop_mills) < len(emuliobTH)     :   emuliobTH.pop()
    if len(loop_mills) < len(origAs_ratio)  :   origAs_ratio.pop()
    if len(loop_mills) < len(emulAs_ratio)  :   emulAs_ratio.pop()
    if len(loop_mills) < len(origAI_ratio)  :   origAI_ratio.pop()
    if len(loop_mills) < len(emulAI_ratio)  :   emulAI_ratio.pop()
    if len(loop_mills) < len(activity)      :   activity.pop()

    # ---   complete the curves to close the polygon for area fill
    cob_area = []
    iob_area = []
    i_iobTH  = []
    t_iobTH  = []
    looparea = []
    cob_area.append(0)                      # top left corner
    iob_area.append(0)                      # top left corner
    looparea.append(loop_mills[0])
    i = 0
    for lopmil in loop_mills:
        cob_area.append(origcob[i])             # the regular data
        iob_area.append(origiob[i])             # the regular data
        looparea.append(lopmil)
        t_iobTH.append(lopmil)
        i_iobTH.append(emuliobTH[i])
        i += 1
    cob_area.append(0)                      # bottom left corner
    iob_area.append(0)                      # bottom left corner
    looparea.append(loop_mills[-1])
    cob_area.append(0)                      #  close polygon at top left corner
    iob_area.append(0)                      #  close polygon at top left corner
    looparea.append(loop_mills[0])

    # ---   plot the comparisons    -------------------------
    if loopCount   <= 30 :                                                                # step size for y-axis (time)
        yStep =  3      # every 15 minutes
    elif loopCount <= 60:
        yStep =  6      # every 30 minutes
    elif loopCount <=120:
        yStep = 12      # every 60 minutes
    elif loopCount <=480:
        yStep = 48      # every 4 hours
    else :
        yStep = 96      # every 8 hours
    yTicks = []
    yLabels= []
    
    for i in range(0, loopCount, yStep) :                                               # the time labels
        yTicks.append(loop_mills[i])
        yLabels.append(loop_label[i])
    if loop_mills[-1] != yTicks[-1]:
        yTicks.append(loop_mills[-1])                                                   # last tick could be missed out
        yLabels.append(loop_label[-1])
    yRange = loop_mills[-1]-loop_mills[0]
    if featured('pred'):                                                                # extend time axis for predictions
        for i in range(30, 241, 30):
            yTicks.append(loop_mills[-1]+i*60)                                          # append 4 hours
            yLabels.append('+'+str(i)+'mins')
        maxframes = len(loop_mills)
        yRange = (yRange + 48*5*60) * 1.05                                              # add pred range plus 50% for BG labels
        thickness = yRange/(loopCount+48)/4
    else:
        maxframes = 1
        thickness = yRange/loopCount/4

    maxPlots = 0
    frameIns = featured('insReq') or featured('maxBolus') or featured('SMB') or featured('basal')
    if frameIns :                                                                       # we need frame for insulin type graph(s)
        maxPlots += 1
    frameBG = featured('bg') or featured('target') or featured('pred') or featured('as ratio') or featured('autoISF') or featured('ISF') or featured ('cob') or featured('iob') or featured('activity')
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
    flowForward = dict(arrowstyle='<|-')                                                # points to current box

    if featured('LIST') and maxPlots>0:    log_msg('\nEmulation finished; generating graphics pages')
    log_msg('\n')
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
    if featured('LIST') and maxPlots>0:
        log_msg(head1)                                                                  # header row 1
        log_msg(head2)                                                                  # header row 2

    with PdfPages(pdfFile) as pdf:
        for iFrame in range(0, maxframes):                                              # the loop instances
            if featured('LIST') and maxPlots>0:
                log_msg(entries[loop_mills[iFrame]].replace('.', my_decimal))           # print short table as heart beat
            if maxPlots == 0:
                log_msg('\nno plot options active')
            else:
                log_msg('Emulation finished; generating graphics page at '+loop_label[iFrame], '\r')
                #fig, axes = plt.subplots(1, maxPlots, constrained_layout=True, figsize=(9, 15)) #6*maxPlots)  )          
                fig = plt.figure(constrained_layout=True, figsize=(2.2*max(6,maxPlots), 11))# w, h paper size in inches; double width if no flowchart
                gs  = fig.add_gridspec(1,maxPlots)                                          # 1 horizontal; 1+2+6 vertical strips
                fig.set_constrained_layout_pads(w_pad=0., h_pad=0., hspace=0., wspace=0.)   # space to edge and between frames
                fig.suptitle('\nCompare original "' + fn + '" vs emulation case "' + varLabel + '"\n', weight='bold')    # incl. <CR> for space below Header
                if frameIns :                                                               # anything related to insulin
                    axin = fig.add_subplot(gs[0,0])                                         # 1 strip wide
                    axin.xaxis.label.set_color('blue')
                    axin.tick_params(axis='x', colors='blue')
                    axin.set_xlabel('Insulin', weight='bold')
                    if featured('pred'):
                        axin.set_ylim(loop_mills[0]+thickness*2+yRange*1.1, loop_mills[0]-thickness*2)    # add thickness*2 so markers fit into plot frame + 10% (45min) space for BG labels
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
                        axin.barh(y=loop_mills, height=thickness*2.0, width=emulBasal,   color='white', label='tempBasal, emulated', edgecolor='blue')
                        axin.barh(y=loop_mills, height=thickness*0.8 , width=origBasal,  color='blue',  label='tempBasal, original')

                    #axin.plot([0,0], [loop_mills[0],loop_mills[-1]], linestyle='dotted', color='black')  # grid line for insulin=0                
                    axin.legend(loc='lower right')
                    
                if frameBG :                                                                # anything related to glucose
                    axbg = fig.add_subplot(gs[0, bgOffset:bgOffset+2])                      # 2 strips wide
                    axbg.xaxis.label.set_color('red')
                    axbg.tick_params(axis='x', colors='red')
                    axbg.set_xlabel('...IOB...COB...Activity...Autosense...ISF...Targets...Glucose...', weight='bold')
                    if frameIns:                                                            # already annotated in insulin frame
                        #axbg.set_yticklabels(['',''])                                      # dummy axis labels; lately problems
                        axbg.set_yticks([-1,9e99])                                          # off scale to suppress ticks
                    else:                                                                   # not yet annotated in insulin frame
                        axbg.set_yticks(yTicks)
                        axbg.set_yticklabels(yLabels)
                    axbg.set_ylim(loop_mills[-1]+thickness*2, loop_mills[0]-thickness*2)
                    #axbg.set_xlim(0, 250)                                                  # no effect on squeezing for bg>250 !!

                    if featured('target') :                                                 # plot targets
                        axbg.plot(emulTarHig, loop_mills, linestyle='None',   marker='o', color='black',  label='target high, emulated')
                        axbg.plot(emulTarLow, loop_mills, linestyle='None',   marker='o', color='black',  label='target  low, emulated')
                        axbg.plot(origTarHig, loop_mills, linestyle='dashed', marker='.', color='yellow', label='target high, original')
                        axbg.plot(origTarLow, loop_mills, linestyle='dashed', marker='.', color='yellow', label='target  low, original')

                    if featured('bg') :                                                     # plot bg
                        axbg.plot(bg,         bgTime,     linestyle='solid',  marker='o', color='red',    label='blood glucose')
                        bgFrame = getBgTimeIndex(iFrame)
                        dura05, avg05 = getHistBG(bgFrame, 0.05)                             # mins in 5% band
                        if dura05>1 and featured('range'):
                            bg_min = avg05 * (1-0.05)
                            bg_max = avg05 * (1+0.05)
                            bg_mills = bgTime[bgFrame]
                            minmills = bg_mills - dura05 * 60
                            axbg.fill_between([bg_min,bg_max], minmills-2*thickness, bg_mills+2*thickness, fc='red', alpha=0.25)
                        if iFrame>1 and ( featured('fitsslope') or featured('bestslope')):  # show all fits
                            dura70, slope70, slopes, iMax = getSlopeBG(bgFrame)
                            first_linear_fit = True
                            keepMax = -1
                            for i in slopes:
                                #print ('iFrame', str(iFrame), ' mit', str(i), 'hat', str(slopes[i]))
                                a0 = slopes[i]['a0']
                                a1 = slopes[i]['a1']
                                tx = bgTime[bgFrame]    # no forecast: +5*60
                                t1 = tx
                                t2 = tx - slopes[i]['dur']*60 #bgTime[bgFrame]
                                bg1= a0 + a1* 0/300
                                bg2= a0 - a1* slopes[i]['dur']*60/300
                                fitcolor = ['#a0a0a0',  'black']                            # dark grey, black
                                isBest = ( i==iMax)
                                if not isBest and featured('fitsslope'):
                                    if first_linear_fit:
                                        axbg.plot([bg1,bg2], [t1,t2], linestyle='dotted', marker='*', color='#a0a0a0', label='any linear fit')#all the fits
                                        first_linear_fit = False
                                    else:
                                        axbg.plot([bg1,bg2], [t1,t2], linestyle='dotted', marker='*', color=fitcolor[isBest])                     #all the fits
                                if isBest and featured('bestslope'):
                                    keepMax = iMax
                                    #print(str(a0), str(a1), str(slopes[i]['dur']*60), str(bg1)+'/'+str(t1), str(bg2)+'/'+str(t2))
                                    best_bg1 = bg1
                                    best_bg2 = bg2
                                    best_t1 = t1
                                    best_t2 = t2
                            if keepMax>=0:
                                axbg.plot([best_bg1,best_bg2], [best_t1,best_t2], linestyle='dotted', marker='*', color='black', label='best linear fit')   #best fit
                        if iFrame>2 and (featured('bestParabola') or featured('fitsParabola')): # show parabolas
                            dura_p, delta_p, parabs, iMax = getBestParabolaBG(bgFrame)
                            first_parabola_fit = True
                            for i in parabs:
                                #print('  plotting', str(parabs[i]))
                                a2 = parabs[i]['a2']
                                a1 = parabs[i]['a1']
                                a0 = parabs[i]['a0']
                                dur= parabs[i]['dur']
                                bfit = []
                                tfit = []
                                fitcolor = ['#ff00ff',  '#900090']                          # faint violett = magenta, dark violett
                                isBest = ( i==iMax)
                                tx = bgTime[bgFrame] +5*60                                   # window end time = +5min from last glucose
                                while tx >= bgTime[bgFrame]-dur*60:
                                    ti = (tx - bgTime[bgFrame])/300
                                    bfit.append(a2*pow(ti,2) + a1*ti + a0)
                                    tfit.append(tx)
                                    #print(str(iFrame),'interim', str(i), str(tfit), str((bfit)))
                                    tx += -2.5*60                                           # go  backwards in fit window
                                if not isBest and featured('fitsParabola'):
                                    axbg.plot(bfit, tfit, linestyle='dotted', color=fitcolor[isBest])   # some Parabola
                                    if first_parabola_fit:
                                        axbg.plot([bfit[ 0],bfit[ 0]], [tfit[ 0],tfit[ 0]], marker='o', color=fitcolor[isBest], label='any parabola fit')     # some other Parabola
                                        first_parabola_fit = False
                                    else:
                                        axbg.plot([bfit[ 0],bfit[ 0]], [tfit[ 0],tfit[ 0]], marker='o', color=fitcolor[isBest])     # some other Parabola
                                    axbg.plot([bfit[-1],bfit[-1]], [tfit[-1],tfit[-1]], marker='o', color=fitcolor[isBest])     # some other Parabola
                                if isBest and featured('bestParabola'):
                                    #print('p-tfit:', str(tfit), '\np-bfit', str(bfit))
                                    axbg.plot(bfit, tfit, linestyle='dotted', color=fitcolor[isBest])    #  best Parabola
                                    axbg.plot([bfit[ 0],bfit[ 0]], [tfit[ 0],tfit[ 0]], marker='o', color=fitcolor[isBest], label='best parabola fit') #  bulls eye of newest forecast
                                    axbg.plot([bfit[-1],bfit[-1]], [tfit[-1],tfit[-1]], marker='o', color=fitcolor[isBest]) #  bulls eye of oldest forecast
                            
                    if featured('as ratio') :                                               # plot autosense ratio
                        axbg.plot([10,10],[loop_mills[0],loop_mills[-1]],linestyle='dotted',color='black',label='Autosense(x10) OFF')
                        axbg.plot(origAs_ratio,loop_mills,linestyle='solid',  marker='.',   color='black',label='Autosense(x10), original')
                        axbg.plot(emulAs_ratio,loop_mills,linestyle='none',   marker='o',   color='black',label='Autosense(x10), emulated')
                    if featured('autoISF') :                                                # plot autoISF ratio on top of darker autosense
                        #xbg.plot([10,10],[loop_mills[0],loop_mills[-1]],linestyle='dotted',color='black',label='AutoISF(x10) OFF')
                        axbg.plot(emulAI_ratio,loop_mills,linestyle='none',   marker='o',   color='#606060', label='AutoISF(x10), emulated')
                        axbg.plot(origAI_ratio,loop_mills,linestyle='solid',  marker='.',   color='#C0C0C0', label='AutoISF(x10), original')
                    if featured('ISF') :                                                    # plot ISF
                        axbg.plot(emulISF,loop_mills,linestyle='none',   marker='o',    color='#007000',label='ISF, emulated')
                        axbg.plot(autoISF,loop_mills,linestyle='dashed', marker='.',    color='#009000',label='ISF, autosensed')
                        axbg.plot(origISF,loop_mills,linestyle='dotted', marker='.',    color='#00FF00',label='ISF, original')
                    if featured('activity') :                                               # plot activity
                        axbg.plot(activity, loop_mills, linestyle='solid',              color='yellow', label='Activity(x1000)')
                    if featured('iob') :                                                    # plot IOB
                        axbg.plot(origiob,  loop_mills, linestyle='solid',              color='blue',   label='IOB(x10)')
                        axbg.fill(iob_area, looparea, c='blue',   alpha=0.2)
                        #axbg.plot(emuliobTH,loop_mills, linestyle='dashed',             color='blue',   label='eff. iobTH(x10), emulated')
                        #axbg.plot(tolerance_iobTH,loop_mills, linestyle='dotted',       color='blue',   label='tol. iobTH(x10), emulated')
                        #i_iobTH = emuliobTH
                        #t_iobTH = loop_mills
                        for i in range(len(emuliobTH)-1, 0, -1):
                            i_iobTH.append(tolerance_iobTH[i])
                            t_iobTH.append(loop_mills[i])
                        i_iobTH.append(tolerance_iobTH[0])
                        t_iobTH.append(t_iobTH[0])                        
                        axbg.fill(i_iobTH, t_iobTH,              alpha=0.4,              color='cyan',   label='iobTH tolerance band(x10), emulated')           
                    if featured('cob') :                                                    # plot COB
                        axbg.plot(origcob,  loop_mills, linestyle='solid',              color='orange', label='COB')
                        axbg.fill(cob_area, looparea, c='orange', alpha=0.4)
                    if featured('pred') :                                                   # plot the predictions
                        thisTime = loop_mills[iFrame]
                        loopCount = 48+1
                        fcastmills = []
                        for lp in range(loopCount):
                            fcastmills.append(round(thisTime/1.000 + lp*5*60, 1 ))          # from millis to secs
                        bbox_props = dict(boxstyle='larrow', fc='#f0f0f0', alpha=0.7)       # slider with time label
                        axbg.set_ylim(loop_mills[0]+thickness*2+yRange*1.1, loop_mills[0]-thickness*2)    # add thickness*2 so markers fit into plot frame + 10% space for BG labels
                        axbg.set_xlim(0,250)                                                # otherwise we need to find scale over all time steps
                        bg_min, bg_max = axbg.get_xlim()
                        axbg.text(bg_min+3, fcastmills[0], loop_label[iFrame], va='center', size=8, bbox=bbox_props)
                        axbg.fill_between([bg_min,bg_max], fcastmills[0]-2*thickness, fcastmills[-1]+2*thickness, fc='#e0e0e0', alpha=0.6)  # time window
                        if frameIns:
                            in_min, in_max = axin.get_xlim()
                            axin.plot([in_min,in_max], [fcastmills[0],fcastmills[0]], linestyle='dotted', color='grey', lw=0.5)          # time line

                        Fcasts = Pred[thisTime]
                        Levels = Fcasts['Levels']

                        #print (str(loop_label[iFrame]), str(Levels))
                        #for ele in Fcasts:
                        #    print (ele)
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
                            BGValPlot(axbg,-3, 'eventualBG',   Levels['eventualBG'],   fcastmills[-1], 'green')
                        
                        if 'SMBoff' in Levels:
                            SMBmsg = 'SMB disabled:\n' + Levels['SMBoff']
                            threshold = Levels['value']
                            label = Levels['type']
                            SMBsource = Levels['source']
                            couleur = colFav[SMBsource]
                            if 'minGuardBG1' not in Levels:    sub_issue(str(Levels))
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
                                if minGuardBG2 == minGuardBG:
                                    share2 = 0
                                else:
                                    share2 = (minGuardBG2-hub_bg)/(minGuardBG2-minGuardBG)      # fraction of BG2
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
                        
                        if 'UAM' in Fcasts :                                                # same logic as in original or minGuard source
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
                            axbg.plot(predZT,  fcastmills[:len(predZT)],  linestyle='None', marker='.', color=colFav['ZT'],  label='predZT, emulated')
                        else:
                            axbg.plot([0,0], [0,0],                       linestyle='none',             color=colFav['ZT'],  label='no ZT  active') # inactive
                        
                    axbg.legend(loc='lower right')
                
                if frameFlow :                                                              # anything related to flow chart
                    axfl = fig.add_subplot(gs[0, flowOffset:])
                    axfl.set_xticks([-99,99999])                                            # off scale to suppress ticks
                    axfl.set_xlim(10, 200)
                    axfl.set_xticklabels(['',''])                                           # dummy axis labels
                    axfl.set_yticks([-99999,99])                                            # off scale to suppress ticks
                    axfl.set_ylim(-700, 0)
                    axfl.set_yticklabels(['',''])                                           # dummy axis labels
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
            if not featured('pred') and featured('LIST') and maxPlots>0:                        # only 1 frame
                for i in range(iFrame+1,  len(entries)):
                    log_msg(entries[loop_mills[i]].replace('.', my_decimal))
            if how_to_print!='GUI' and featured('PDF') and not featured('pred') and maxPlots>0:
                #print('batch mode with PDF')
                plt.show()     # otherwise conflict with root.mainloop() in tkinter
            plt.close()                                     # end of current page
        #pdf.close()                                        # not needed due to "with ..." method triggered above
    pass

def parameters_known(myseek, arg2, variantFile, startLabel, stoppLabel, entries, msg, my_dec):
    #log_msg('entered parameters_known mit\nmyseek='+myseek+'\narg2='+arg2+'\nvariantFile='+variantFile+'\nstartLabel='+startLabel+'\nstoppLabel='+stoppLabel)
    #   start of top level analysis
    
    global  fn
    global  ce_file
    global  varLabel, echo_msg, my_decimal
    global  doit
    global  fn_first

    global  loop_mills, loop_label
    global  bg, bgTime, bgTimeMap
    global  origTarLow, emulTarLow, origTarHig, emulTarHig
    global  origAs_ratio, emulAs_ratio              # Autosense
    global  origAI_ratio, emulAI_ratio              # autoISF
    global  origiob, origcob, origiobTH, emuliobTH, tolerance_iobTH
    global  activity
    global  origInsReq, emulInsReq
    global  origSMB, emulSMB, origMaxBolus, emulMaxBolus
    global  origBasal, emulBasal, lastBasal
    global  profISF, origISF, autoISF, BZ_ISF, Delta_ISF, pp_ISF, acceISF, dura_ISF, emulISF, longDelta, avgDelta, longSlope, rateSlope
    global  Pred, FlowChart, Fits
    global  filecount
    global  t_startLabel, t_stoppLabel
    global  varFile
    global  CarbReqGram, CarbReqTime, lastCOB
    
    global  isAndroid                               # flag for running on Android
    global  isZip                                   # flag for input file type
    global  newLoop                                 # flag whether data collection for new loop started
    #global  entries
    global   deltas, linFit, cubFit, new_parameter

    deltas      = {}
    linFit      = {}
    cubFit      = {}
    bgTimeMap   = {}
    
    loop_mills  = []
    loop_label  = []
    bg          = []
    bgTime      = []
    origTarLow  = []
    emulTarLow  = []
    origTarHig  = []
    emulTarHig  = []
    
    origAs_ratio= []
    emulAs_ratio= []
    origAI_ratio= []
    emulAI_ratio= []
    origiob     = []
    origiobTH   = []
    emuliobTH   = []
    tolerance_iobTH = []
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
    Fits        = {}                                # holds range, slope, parabola data
    longDelta   = []                                # holds the duration of recent 5% range
    avgDelta    = []                                # holds the average BG of recent 5% range
    longSlope   = []                                # holds the duration of regression fit
    rateSlope   = []                                # holds the fitted rate (mg/dl/5mins)
    origISF     = []                                # holds the final ISF used in the original run
    profISF     = []                                # holds the ISF defined in the profile of the emulated run
    autoISF     = []                                # holds the ISF after checking the autosense impact, emulation run
    BZ_ISF      = []                                # holds the ISF after strengthening due to high glucse level
    Delta_ISF   = []                                # holds the ISF after strengthening due to high delta
    pp_ISF      = []                                # holds the ISF after strengthening due to high delta after meals
    acceISF     = []                                # holds the ISF after strengthening due to high acceleration
    dura_ISF    = []                                # holds the ISF after strengthening due to high acceleration
    emulISF     = []                                # holds the final ISF after strengthening due to long lasting highs
    
    Pred        = {}                                # holds all loop predictions
    FlowChart   = {}                                # holds all loop decisions for flow chart
    
    t_startLabel= startLabel
    t_stoppLabel= stoppLabel
    filecount   = 0
    newLoop     = False
        
    my_decimal = my_dec
    echo_msg = msg    
    myfile = ''
    arg2 = arg2.replace('_', ' ')                   # get rid of the UNDERSCOREs
    doit = arg2.split('/')
    varFile = variantFile                           # on Windows
    varLabel = os.path.basename(varFile)            # do not overwrite the calling arg value
    if varLabel[len(varLabel)-4:]=='.dat' or  varLabel[len(varLabel)-4:]=='.vdf' :  # drop the tail coming from DOS type ahead
        varLabel = varLabel[:-4]
    else:
        varFile = varFile + '.vdf'
    if setVariant('1900-01-01T00:00:00'):
        return  60, 'Z', 0, '', '', 0, ''               # prescan to get parabola fit length

    #log_msg('inside all_parameters_known -->\nvarFile='+varFile+'\nvarLabel='+varLabel)#   
    logListe = glob.glob(myseek+myfile, recursive=False)
    #print ('logListe:', str(logListe))
    if arg2[:7] == 'Android' :
        isAndroid = True
    else:
        isAndroid = False
        utf8 = os.getenv('PYTHONUTF8', 'undefined')
        if utf8 == 'undefined':
            sub_issue('You need to set the environment variable PYTHONUTF8 first and assign the value 1')
            return 0, 'UTF8', 0, '', '', 0, ''        # not defined at all
        if utf8 != '1':
            sub_issue('Environment variable PYTHONUTF8 has wrong value '+utf8+', must be value 1')
            return 0, 'UTF8', 0, '', '', 0, ''        # wrong value
        
    # ---   add sorting info    -----------------------------------
    sorted_fn = {}
    if isAndroid:
        sorted_fn[myseek] = myseek
    else:
        for fn in logListe:
            lenfn = len(fn)
            basefn= os.path.basename(fn)
            basefn= basefn.replace('AndroidAPS._', '')          # default starting with YYYY-MM-TT
            if basefn[4]+basefn[7]+basefn[10] == '--_' :        # assume regular date sting
                #print('checking for fit of '+ basefn)
                if (basefn[:10]>=t_startLabel[:10]):    # undo: and (basefn[:10]<=t_stoppLabel[:10]):   # otherwise date outside window
                    ftype = fn[lenfn-3:]
                    if ftype=='zip' or ftype=='log' or ftype.find(".")>=0:
                        if fn[lenfn-6:lenfn-5] == '.':
                            #print('pseud ist einstellig')
                            fnpseudo = fn[:lenfn-5] + '0' + fn[lenfn-5:]
                        else:
                            #print('pseud ist zweistellig')
                            fnpseudo = fn
                        fcounter = fn[lenfn-6:-4]
                        sorted_fn[fnpseudo] = fn    #os.path.basename(fn)
                    #print(str(sorted_fn))
                    pass
        if len(sorted_fn) == 0:
            sorted_fn[myseek] = myseek              # in case of special naming use just that file
 

    """
 
    # --- check for external bg_emul source ----------
    global use_bg_emul
    use_bg_emul = False
    print('echo of calling parameters:\n' + msg)
    wo = msg.find('BG_emul data table    t_') + len('BG_emul data table    t_')
    if wo>0:
        use_bg_emul = True
        tableau = msg[wo:(wo+msg[wo:].find('\n'))]
        print('get bg emul from', tableau)
       inpStart = max(tstart.get(), selectedFirst)
        inpStopp = min(tstopp.get(), selectedLast)
        useStart = getTriggerDate(inpStart)
        useStopp = getTriggerDate(inpStopp)
        if useStart==timedelta(0) or useStopp==timedelta(0):
            print('wrong time window '+ tstart.get() + ' or ' + tstop.get() )
            return
        sql = "select "+tableau+" from t_"+tableau+" where "+tableau+">="+str(bg_threshold) \
            + " and STAMP>='"+useStart+"' and STAMP<='"+useStopp+"'"
        cur.execute(sql)
        for rec in cur:
            bg = rec[0]
            n_bg = np.append(n_bg, [bg])
    """


    filecount = 0
    wd = os.path.dirname(varFile)
    if isAndroid:       wd = wd + '/'
    elif wd !='':       wd = wd + '/'               # needed for GUI method
    #if wd == '':        wd = os.getcwd()
    for ps in sorted(sorted_fn):
        fn = sorted_fn[ps]
        #print('Try file ['+fn+'] in folder ['+wd+'] of ['+varFile+']')
        ftype = fn[len(fn)-3:]
        useFile = False
        if isAndroid and ftype=='log':                                                  useFile = True
        elif not isAndroid and (ftype=='zip' or ftype=='log' or ftype.find('.')>0) :    useFile = True      # valid logfiles should end with "_.0" thru "_.99" or "zip"
        #print(ftype, str(useFile))
        if useFile:
            isZip = ( ftype == 'zip')
            if filecount == 0 :                     # initalize file loop
                #wd = os.path.dirname(varFile)
                if startLabel.find('2000')==0 :
                    fnLabel = os.path.basename(fn)  # only one logfile to scan: use its name
                else:
                    fnLabel = startLabel            # series of logfiles to scan: use start date/time
                    fnLabel = fnLabel.replace(':','-')  # get close to original time format
                #log_msg('inside all_parameters_known, file loop -->\nwd='+wd+'\nfnLabel='+fnLabel)
                ce_file = wd + fnLabel + '.' + varLabel + '.txt'
                cel = open(ce_file, 'w')
                cel.write('AAPS scan from ' + varLabel + ' for SMB comparison created on ' + formatdate(localtime=True) + '\n')
                cel.write('FILE='+fn + '\n')
                cel.close()
                my_ce_file(ce_file)                 # exports name to determine_basal.py
                fn_first = wd + fnLabel
                #print('fn_first =', wd + fnLabel)
                #if how_to_print=='GUI':
                #    fn_first_used.set(fn)
                if not isAndroid:        log_msg ('\n')
            cont = scanLogfile(fn, entries)
            #print('returned to parameters_known:', CarbReqGram, 'when:', CarbReqTime)
            filecount += 1
            if cont == 'SYNTAX':
                varlog.close()
                return 0, 'SYNTAX', 0, '', '', 0, ''    # problem in VDF file
            if cont == 'STOP':
                break                                   # end of time window reached
    
    if filecount == 0 :
        log_msg ('no such logfile: "'+myseek+'"')
        return 0, 'Z', 0, '', '', 0, ''
    loopCount = len(loop_mills)
    if loopCount == 0 :
        log_msg ('\nno entries found in logfile: "'+myseek+'"')
        #return     #sys.exit()
    log.write('END\n')
    log.close()
    varlog.write('END\n')
    varlog.close()
    
    #print(str(loopCount),'\n', str(origTarLow), '\n', str(origTarHig))    
    if loopCount > 0 :   # ---   save the results from current logfile   --------------
        for iFrame in range(len(loop_label)):
            thisTime = loop_mills[iFrame]
            if thisTime not in entries:                 # holds the rows to be printed on Android or windows
                if featured('seconds'):
                    r_list = loop_label[iFrame][:8]+'Z'
                else:
                    r_list = loop_label[iFrame][:5]+'Z'
                if featured('bg'):
                    thisBZ = bg[getBgTimeIndex(iFrame)]
                    if thisBZ>40:
                        strBZ = str(round(thisBZ, 0)).replace('.0', '')    # mg
                    else:
                        strBZ = str(round(thisBZ, 1))                      # mmol
                    r_list += f'{strBZ:>6}'
                if featured('target'):

                    r_list += f'{round((origTarLow[iFrame] + origTarHig[iFrame])/2,0):>8}'.replace(".0","")
                if featured('iob'):     
                    r_list += f'{round(origiob[iFrame]/10,2):>6}{round(emuliobTH[iFrame]/10,2):>6}'   # scaled up for plotting
                if featured('cob'):     
                    r_list += f'{round(origcob[iFrame],2):>6}'
                #if featured('as ratio'):
                #    r_list += f'{round(origAs_ratio[iFrame]/10,2):>6}'     # was scaled up for plotting
                #if featured('autoISF'):
                #    #_list += f'{round(origAI_ratio[iFrame]/10,2):>6} {round(emulAI_ratio[iFrame]/10,2):>4}'     # scaled up for plotting
                #    r_list += f'{round(emulAI_ratio[iFrame]/10,2):>4}'     # was scaled up for plotting
                if featured('range'):
                    r_list += f'{longDelta[iFrame]:>6}{avgDelta[iFrame]:>7}'
                if featured('fitsslope') or featured('bestslope'):
                    r_list += f'{longSlope[iFrame]:>7}{rateSlope[iFrame]:>6}'
                if featured('fitsParabola') or featured('bestParabola'):
                    this_List = 23*' '
                    #print('\n\n'+str(thisTime), str(bgTimeMap))
                    if thisTime in bgTimeMap:
                        deltaTime = bgTimeMap[thisTime]
                        #print('  '+str(deltaTime))
                        #for ele in deltas:
                        #    print('--> '+str(ele))
                        if deltaTime in deltas:
                            thisDelta = deltas[deltaTime]
                            #print('    '+str(thisDelta))
                            if 'parabola_fit_minutes' in thisDelta:
                                this_List = f'{thisDelta["parabola_fit_minutes"]:>7}{round(thisDelta["parabola_fit_last_delta"],2):>8}'
                                this_List+= f'{round(thisDelta["parabola_fit_next_delta"],2):>8}'
                    r_list += this_List
                #if featured('autosens) or featured('auto'): 
                #    r_list += f'{round(emulAs_ratio[iFrame]/10,2):>7}{round(acceISF[iFrame],2):>6}{round(BZ_ISF[iFrame],2):>6}{round(pp_ISF[iFrame],2):>6}{round(Delta_ISF[iFrame],2):>6}{round(dura_ISF[iFrame],2):>6}'
                if featured('autosens') or featured('auto'): 
                    r_list += f'{round(emulAs_ratio[iFrame]/10,2):>6}'
                if featured('acce ISF') or featured('acce'): 
                    r_list += f'{round(acceISF[iFrame],2):>6}'
                if featured('bg ISF'): 
                    r_list += f'{round(BZ_ISF[iFrame],2):>6}'
                if featured('pp ISF') or featured('pp'): 
                    r_list += f'{round(pp_ISF[iFrame],2):>6}'
                if featured('delta ISF') or featured('delta'): 
                    r_list += f'{round(Delta_ISF[iFrame],2):>6}'
                if featured('dura ISF') or featured('dura'): 
                    r_list += f'{round(dura_ISF[iFrame],2):>6}'
                if featured('ISF') or featured('ISFs'):         # 21
                    r_list += f'{round(origISF[iFrame],1):>8}{round(profISF[iFrame],1):>6}{round(emulISF[iFrame],1):>6}'
                if featured('insReq'):
                    r_list += f'{origInsReq[iFrame]:>7}{emulInsReq[iFrame]:>6}'
                if featured('SMB'):
                    r_list += f'{origSMB[iFrame]:>6}{emulSMB[iFrame]:>5}'
                if featured('basal'):
                    r_list += f'{round(origBasal[iFrame],2):>7}{round(emulBasal[iFrame],2):>7}'
                entries[thisTime] = r_list
                    
        # ---   print the comparisons    -------------------------
        head1  = "  ;    ; ;     ;  bg ;  bg ; target; target; target; target;       ;      ;  eff.;  tol.;    "
        head2  = "  ; UTC; ; UNIX;accel;brake;   low ;  high ;  low  ;  high ;       ;      ; iobTH; iobTH;    "
        head3  = "id;time;Z; time;     ;     ;  orig ;  orig ;  emul ;  emul ;  cob  ; iob  ; emul ; emul ; act"
        
        head1 += "; auto; final; dura;     ; lin.fit; "
        head2 += "; sens;  ISF; min-; dura ;  min-  ; lin.fit"
        head3 += "; orig; orig; utes; avg. ;  utes  ; delta"
        
        head1 += ";  parab; parab;  parab; parab"
        head2 += ";   fit ;  fit ;  fit ;   fit"
        head3 += "; correl; durat; last-Δ; next-Δ"

        head1 += "; auto; acce;  bg ;  pp ; delta; dura; final;     ;     ;    "
        head2 += "; sens ; ISF;  ISF;  ISF; ISF;  ISF;  ISF ;  ISF ;  ISF ; ISF"
        head3 += "; emul; emul; emul; emul; emul; emul ; emul ; orig;  prof; emul"

        head1 += "; Ins.; Ins.; max ; max ;     ;     ;     ; "
        head2 += "; Req.; Req.;bolus;bolus; SMB  ; SMB  ; TBR  ; TBR "
        head3 += "; orig; emul; orig; emul; orig ; emul ; orig ; emul "
        #print('\n' + head)
        xyf.write(head1+'\n' + head2+'\n' + head3+'\n')
        
        origBasalint = 0.0
        emulBasalint = 0.0
        origSMBsum = 0.0
        emulSMBsum = 0.0
        min_bg     = 999
        max_bg     = 0
        min_origAS = 10.0       # incl. scaling up
        max_origAS = 10.0       # incl. scaling up
        min_emulAS = 10.0       # incl. scaling up
        max_emulAS = 10.0       # incl. scaling up
        min_origAI = 10.0       # incl. scaling up
        max_origAI = 10.0       # incl. scaling up
        min_emulAI = 10.0       # incl. scaling up
        max_emulAI = 10.0       # incl. scaling up
        min_origISF= 999
        max_origISF= 0.0
        min_profISF= 999
        max_profISF= 0.0
        min_autoISF= 999
        max_autoISF= 0.0
        min_dura_ISF= 999
        max_dura_ISF= 0.0
        min_BZ_ISF = 999
        max_BZ_ISF = 0.0
        min_Delta_ISF= 999
        max_Delta_ISF= 0.0
        min_pp_ISF = 999
        max_pp_ISF = 0.0
        min_acceISF= 999
        max_acceISF= 0.0
        min_emulISF= 999
        max_emulISF= 0.0
        min_origSMB= 999
        max_origSMB= 0.0
        min_emulSMB= 999
        max_emulSMB= 0.0
        
        hour_offset = 0                                     # overflow into next day
        for i in range(loopCount) :
            time_UTC = loop_label[i][:-1]
            if i>0 and time_UTC<loop_label[i-1][:-1]:
                hour_offset += 24
            hour_new = eval(str(hour_offset)+"+1"+time_UTC[:2]) # e.g. 24+102=126
            time_new = str(hour_new)[1:3] + time_UTC[2:]        # e.g. '26'+':mm:ss'
            tabz = f'{i:>3};{time_new};Z; {loop_mills[i]:>13}; {bg[getBgTimeIndex(i)]:>4}; ' 
            if acceISF[i] < 1:
                tabz += f'{bg[getBgTimeIndex(i)]:>4}; '         # negative acceleration
            else:                tabz += '    ; '               # positive acceleration
            tabz += f'{origTarLow[i]:>4};{origTarHig[i]:>3};{emulTarLow[i]:>4};{emulTarHig[i]:>3}; ' 
            tabz += f'{origcob[i]:>5}; {round(origiob[i]/10,2):>5}; {round(emuliobTH[i]*0.1,2):>5}; {round(emuliobTH[i]*0.13,2):>5}; {round(activity[i]/1000,3):>6}; ' 
            tabz += f'{round(origAs_ratio[i]/10,2):>5};'                # {round(emulAs_ratio[i]/10,2):>5};' 
            tabz += f'{round(origAI_ratio[i]/10,2):>6}; ' 
            tabz += f'{longDelta[i]:>7}; {avgDelta[i]:>7};' 
            tabz += f'{longSlope[i]:>8}; {rateSlope[i]:>6};' 
            this_List = 31*' '
            thisTime = loop_mills[i]
            skip_parab = True
            if thisTime in bgTimeMap:
                deltaTime = bgTimeMap[thisTime]
                if deltaTime in deltas:
                    thisDelta = deltas[deltaTime]
                    if 'parabola_fit_minutes' in thisDelta:
                        this_List = f'{round(thisDelta["parabola_fit_correlation"],4):>9};{round(thisDelta["parabola_fit_minutes"],1):>6};'
                        this_List+= f'{round(thisDelta["parabola_fit_last_delta"],2):>8};{round(thisDelta["parabola_fit_next_delta"],2):>8};'
                        skip_parab = False
            if skip_parab: this_List = '; ; ; ;'
            tabz += this_List
            #abz += f'{round(emulAs_ratio[i]/10,2):>5};{round(acceISF[i],2):>6};{round(BZ_ISF[i],2):>6};{round(pp_ISF[i],2):>6};{round(Delta_ISF[i],2):>6};{round(emulAI_ratio[i]/10,2):>4};'
            tabz += f'{round(emulAs_ratio[i]/10,2):>5};{round(acceISF[i],2):>6};{round(BZ_ISF[i],2):>6};{round(pp_ISF[i],2):>6};{round(Delta_ISF[i],2):>6};{round(dura_ISF[i],2):>4};'
            #abz += f'{round(profISF[i]/emulISF[i],2):>4};{round(origISF[i],1):>8};{round(profISF[i],1):>6};{round(emulISF[i],1):>6};' 
            tabz += f'{round(emulAI_ratio[i]/10,2):>4};{round(origISF[i],1):>8};{round(profISF[i],1):>6};{round(emulISF[i],1):>6};' 
            tabz += f'{origInsReq[i]:>8}; {emulInsReq[i]:>6}; ' 
            tabz += f'{origMaxBolus[i]:>7}; {emulMaxBolus[i]:>4}; {origSMB[i]:>6}; {emulSMB[i]:>4}; ' 
            tabz += f'{origBasal[i]:>9}; {emulBasal[i]:>6}'
            #print(tabz)
            origSMBsum += origSMB[i]
            emulSMBsum += emulSMB[i]
            if i==loopCount-1:                  # last time step
                fraction = 5 / 60               # next 5 min per hour
            else:
                fraction = (loop_mills[i+1] - loop_mills[i]) / 3600
            #print (str(fraction*60))
            origBasalint += origBasal[i]*fraction
            emulBasalint += emulBasal[i]*fraction
            if min_bg>bg[getBgTimeIndex(i)]:    min_bg = bg[getBgTimeIndex(i)]
            if max_bg<bg[getBgTimeIndex(i)]:    max_bg = bg[getBgTimeIndex(i)]
            if min_origAS>origAs_ratio[i]:      min_origAS = origAs_ratio[i]
            if max_origAS<origAs_ratio[i]:      max_origAS = origAs_ratio[i]
            if min_emulAS>emulAs_ratio[i]:      min_emulAS = emulAs_ratio[i]
            if max_emulAS<emulAs_ratio[i]:      max_emulAS = emulAs_ratio[i]
            if min_origAI>origAI_ratio[i]:      min_origAI = origAI_ratio[i]
            if max_origAI<origAI_ratio[i]:      max_origAI = origAI_ratio[i]
            if min_emulAI>emulAI_ratio[i]:      min_emulAI = emulAI_ratio[i]
            if max_emulAI<emulAI_ratio[i]:      max_emulAI = emulAI_ratio[i]
            if min_origISF>origISF[i]:          min_origISF = origISF[i]
            if max_origISF<origISF[i]:          max_origISF = origISF[i]
            if min_profISF>profISF[i]:          min_profISF = profISF[i]
            if max_profISF<profISF[i]:          max_profISF = profISF[i]
            if min_autoISF>autoISF[i]:          min_autoISF = autoISF[i]
            if max_autoISF<autoISF[i]:          max_autoISF = autoISF[i]
            if min_dura_ISF>dura_ISF[i]:        min_dura_ISF = dura_ISF[i]
            if max_dura_ISF<dura_ISF[i]:        max_dura_ISF = dura_ISF[i]
            if min_BZ_ISF >BZ_ISF[i]:           min_BZ_ISF  = BZ_ISF[i]
            if max_BZ_ISF <BZ_ISF[i]:           max_BZ_ISF  = BZ_ISF[i]
            if min_Delta_ISF>Delta_ISF[i]:      min_Delta_ISF = Delta_ISF[i]
            if max_Delta_ISF<Delta_ISF[i]:      max_Delta_ISF = Delta_ISF[i]
            if min_pp_ISF >pp_ISF[i]:           min_pp_ISF  = pp_ISF[i]
            if max_pp_ISF <pp_ISF[i]:           max_pp_ISF  = pp_ISF[i]
            if min_acceISF>acceISF[i]:          min_acceISF = acceISF[i]
            if max_acceISF<acceISF[i]:          max_acceISF = acceISF[i]
            if min_emulISF>emulISF[i]:          min_emulISF = emulISF[i]
            if max_emulISF<emulISF[i]:          max_emulISF = emulISF[i]
            if min_origSMB>origSMB[i]:          min_origSMB = origSMB[i]
            if max_origSMB<origSMB[i]:          max_origSMB = origSMB[i]
            if min_emulSMB>emulSMB[i]:          min_emulSMB = emulSMB[i]
            if max_emulSMB<emulSMB[i]:          max_emulSMB = emulSMB[i]
            xyf.write(tabz.replace('.', my_decimal) + '\n')
        
        sepLine = ''
        sepLine += 271 * '-'
        sepLine += '\n'
        tabz = ';Minimum:;;; '+ f'{min_bg:>22}' \
             + f';;;;;;;;;;;{round(min_origAS/10,2):>57}; {round(min_origAI/10,2):>5}' \
             + f';;;;;;;;;{round(min_emulAS/10,2):>67}' \
             + f';{round(min_acceISF,2):>6};{round(min_BZ_ISF,2):>6};{round(min_pp_ISF,2):>6};{round(min_Delta_ISF,2):>6};{round(min_dura_ISF,2):>5}' \
             + f';;{round(min_origISF,1):>11};{round(min_profISF,1):>6};{round(min_emulISF,1):>6}' \
             + f';;;;;{round(min_origSMB,1):>35}; {round(min_emulSMB,1):>4}'
        xyf.write(tabz.replace('.', my_decimal) + '\n')
        tabz = ';Maximum:;;; '+ f'{max_bg:>22}' \
             + f';;;;;;;;;;;{round(max_origAS/10,2):>57}; {round(max_origAI/10,2):>5}' \
             + f';;;;;;;;;{round(max_emulAS/10,2):>67}' \
             + f';{round(max_acceISF,2):>6};{round(max_BZ_ISF,2):>6};{round(max_pp_ISF,2):>6};{round(max_Delta_ISF,2):>6};{round(max_dura_ISF,2):>5}' \
             + f';;{round(max_origISF,1):>11};{round(max_profISF,1):>6};{round(max_emulISF,1):>6}' \
             + f';;;;;{round(max_origSMB,1):>35}; {round(max_emulSMB,1):>4}'
        xyf.write(tabz.replace('.', my_decimal) + '\n')
        tabz = ';Totals:'+ ';'*38+f'{round(origSMBsum,1):>241}; {round(emulSMBsum,1):>4}; {round(origBasalint,2):>9}; {round(emulBasalint,2):>6}'
        xyf.write(tabz.replace('.', my_decimal) + '\n')

        # ---   list all types of delta information    -----------
        #pro = os.system("SET PYTHONUTF8=1")
        #print(str(pro))
        delta_file = wd + fnLabel + '.' + varLabel + '.delta'
        delta = open(delta_file, 'w')
        delta.write('   time        time    [mg/dl]   5min    other-deltas    linear-fit    -----orig parabola fit-----    emul.par.fit\n' \
                  + '    UTC        UNIX       bg     delta  short    long    dura slope     corr  dura  last-Δ  next-Δ    dura  next-Δ\n')
        i = 0
        for mills in deltas:
            #mills = loop_mills[i]
            i_label = loop_label[i]
            ll  = f'{i_label:>9}  {round(bgTime[i],0):>10} {bg[i]:>4}'
            ll += f'{round(deltas[mills]["delta"],2):>9} {round(deltas[mills]["short"],2):>7} {round(deltas[mills]["long"],2):>7}'
            ll += f'{longSlope[i]:>8}{rateSlope[i]:>6}'
            if 'parabola_fit_minutes' in deltas[mills]:
                ll += f'{round(deltas[mills]["parabola_fit_correlation"],4):>9}{round(deltas[mills]["parabola_fit_minutes"],1):>6}'
                ll += f'{round(deltas[mills]["parabola_fit_last_delta"],2):>8}{round(deltas[mills]["parabola_fit_next_delta"],2):>8}'
            else:
                ll += 31 * ' '
            dura_p, delta_p, parabs, iMax = getBestParabolaBG(i)
            ll += f'{round(dura_p,1):>8}{round(delta_p,2):>7}'
            if iMax >=0:    ll += '  '+str(parabs[iMax]) 
            delta.write(ll.replace('.', my_decimal) + '\n')
            i += 1
            if i >= len(loop_label):        break
        delta.close()

    xyf.close()
    
    if len(entries) == 0:
        sub_issue('\nNo loop data yet in fresh logfile')
        return 60, 'Z',0, '', '', 0, ''
    else:
        if featured ('seconds'):
            head1 = '    UTC  '                         # 9
            head2 = '   time  '
        else:
            head1 = '  UTC '                            # 6
            head2 = ' time '
        if featured('bg'):                              #  6     
            head1 += '      '
            head2 += '    bg'
        if featured('target'):                          #  6
            head1 += '  avg.'
            head2 += '  targ'
        if featured('iob'):                             #  12
            head1 += '        eff.'
            head2 += '   IOB iobTH'
        if featured('cob'):                             #  6 
            head1 += '      '
            head2 += '   COB'
        #if featured('as ratio'):                       #  6
        #    head1 += '  Auto'
        #    head2 += '  sens'
        #if featured('autoISF'):                         # 11
        #    head1 += '  -AutoISF-'
        #    head2 += '  orig emul'
        if featured('range'):                           # 13
            head1 += '  --5% range-'
            head2 += '  dura   avg.'
        if featured('fitsslope') or featured('bestslope'):                           # 13
            head1 += '   --lin.fit-'
            head2 += '   dura  rate'
        if featured('fitsParabola') or featured('bestParabola'):                     # 21
            head1 += '   ----parabola fit----'
            head2 += '   dura  last-Δ  next-Δ'
        showISFfactors = False
        ISFhead1 = ''
        ISFhead2 = ''
        if featured('autosens'):                        # 6
            head1 += '  auto'
            head2 += '  sens'
            showISFfactors = True
        if featured('acce ISF') or featured('acce'):    # 6
            ISFhead1 += '  acce'
            ISFhead2 += '   ISF'
            showISFfactors = True
        if featured('bg ISF'):                          # 6
            ISFhead1 += '    bg'
            ISFhead2 += '   ISF'
            showISFfactors = True
        if featured('pp ISF') or featured('pp'):        # 6
            ISFhead1 += '    pp'
            ISFhead2 += '   ISF'
            showISFfactors = True
        if featured('delta ISF') or featured('delta'):  # 6
            ISFhead1 += ' delta'
            ISFhead2 += '   ISF'
            showISFfactors = True
        if featured('dura ISF') or featured('dura'):    # 6
            ISFhead1 += '  dura'
            ISFhead2 += '   ISF'
            showISFfactors = True
        if showISFfactors:                              # 1
            head1 += '' + ISFhead1
            head2 += '' + ISFhead2
        if featured('ISF') or featured('ISFs'):         # 20
            head1 += '    ------ISFs------' 
            head2 += '    orig  prof  emul'
        if featured('insReq'):                          # 13
            head1 += '  insulin Req'
            head2 += '   orig  emul'
        if featured('SMB'):                             # 11
            head1 += '  ---SMB---'
            head2 += '  orig emul'
        if featured('basal'):                           # 14
            head1 += '  --tmpBasal--'
            head2 += '   orig   emul'
    
    if isAndroid :
        maxItems = 15          
    else:
        maxItems = len(loop_label)
        if loopCount > 0 :          XYplots(loopCount, head1, head2, entries)
    sorted_entries = sorted(entries)
    top10 = min(maxItems, len(entries) )
    tail = ''
    if isAndroid :
        os.system('clear')
        if len(head1) == 92:    tail = ' '                              # this is double of portrait width
        log_msg('\n'+head1+tail)
        log_msg(head2+tail)                                             # 1 record per print for safe rotations
        for thisTime in sorted_entries[len(sorted_entries)-top10:]:     # last hour plus
            values = entries[thisTime]
            log_msg(values.replace('.', my_decimal)+tail)

    # erase outdated entries; the remainder is kept in case a new logfile is started
    old_entries = copy.deepcopy(sorted_entries)
    for oldTime in old_entries:
        if oldTime not in sorted_entries[len(sorted_entries)-top10:]:
            del entries[oldTime]                                        # no longer in last 14 entries
    if loopCount == 0:
        return 60, 'Z', 0, '', '', 0, ''
    else:
        extraSMB = emulSMB[loopCount-1] - origSMB[loopCount-1] 
        #print("origSMB="+str(origSMB)+"\nemulSMB="+str(emulSMB))
        loopInterval = 60
        if loopCount>1:
            loopInterval = (loop_mills[-1] - loop_mills[0]) / (loopCount-1) / 1000     # avg. sec per loop
        return loopInterval, loop_label[loopCount-1], round(extraSMB, 1), CarbReqGram, CarbReqTime, lastCOB, fn_first

def set_tty(printframe, txtbox, channel):                   # for GIU
    global how_to_print
    how_to_print = channel
    global runframe
    runframe = printframe
    global lfd
    lfd = txtbox

def log_msg(msg, eol='\n'):                                 # for GUI
    if how_to_print == 'GUI':
        lfd['state'] = 'normal'
        if eol == '\n':
            lfd.insert('end', msg + '\n')
        else:
            lfd.delete('end-2c linestart', 'end-2c lineend+1c')   # cannot overwrite
            lfd.insert('end', msg + '\n')     
        lfd.see('end')
        lfd['state'] = 'disabled'
        runframe.update()                                   # update frame display
    else:
        print(msg, end=eol)

def sub_issue(msg):
    if how_to_print == 'GUI':
        lfd['state'] = 'normal'
        lfd.insert('end', msg + '\n', ('issue'))
        lfd.see('end')
    else:
        print (msg)

#