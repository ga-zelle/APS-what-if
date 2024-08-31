import sys
import os
import glob
import json
import time
from datetime import datetime, timedelta

from emulator_core import parameters_known
from emulator_core import set_tty

from emulator_core import get_version_core
from determine_basal    import get_version_determine_basal

def get_version_batch(echo_msg):
    echo_msg['emulator_batch.py'] = '2024-05-24 23:25'
    return echo_msg

def mydialog(title,buttons=["OK"],items=[],multi=False,default_pick=[0,1]):
    # adapted from "https://stackoverflow.com/questions/51874555/qpython3-and-androidhelper-droid-dialogsetsinglechoiceitems"
    title = str(title)
    droid.dialogCreateAlert(title)
    if len(items) > 0:
        if multi:
            droid.dialogSetMultiChoiceItems(items, default_pick)   # incl. list of defaults
        else:
            droid.dialogSetSingleChoiceItems(items, default_pick[0])
    if len(buttons) >= 1:
        droid.dialogSetPositiveButtonText(buttons[0])
    if len(buttons) >= 2:
        droid.dialogSetNegativeButtonText(buttons[1])
    if len(buttons) == 3:
        droid.dialogSetNeutralButtonText(buttons[2])
    droid.dialogShow()
    res0 = droid.dialogGetResponse().result
    res = droid.dialogGetSelectedItems().result
    if "which" in res0.keys():
        res0={"positive":0,"neutral":2,"negative":1}[res0["which"]]
    else:
        res0=-1
    droid.dialogDismiss()                       # important for Android12
    return res0,res

def dialog1(Title, btns, default_btn, items, default_item):
    while True:
        os.system('clear')
        print('List of '+Title+':')
        for item in items:
            if item == default_item:
                trail = ' (default)'
            else:
                trail = ''
            print(item + '-' + items[item], trail)
        #print('default:', items[default_item])
        print('\nWhen done, list of actions:')
        for btn in btns:
            if btn == default_btn:
                trail = ' (default)'
            else:
                trail = ''
            print(btn +'-' + btns[btn], trail)
        #print('default:', btns[default_btn] )
        my_opt = input('Enter key for option or action: ')
        if my_opt in items:
            return default_btn, my_opt, False
        elif my_opt in btns:
            return my_opt, default_item, True
        elif my_opt == '':
            return default_btn, default_item, True
        else:
            #print(binascii.b2a_uu(7))          # bell() ?
            pass


def waitNextLoop(loopInterval, arg,varName):                  # arg = hh:mm:ss of last loop execution, optionally appended 'Z'
    #E started 05.Nov.2019
    if arg == 'Z':                              # no entry found for SMB loop
        waitSec = loopInterval + 10             # this shoud include at leat 1 loop
    else:
        loophh = eval('1'+arg[0:2]) - 100       # handle leading '0'
        loopmm = eval('1'+arg[3:5]) - 100       # handle leading '0'
        loopss = eval('1'+arg[6:8]) - 100       # handle leading '0'
        LoopSec= loophh*3600 + loopmm*60 + loopss
        now = time.gmtime()
        now_hh = now[3]                         # tm_hour
        now_mm = now[4]                         # tm_min
        now_ss = now[5]                         # tm_sec
        if now_hh<loophh:
            now_hh = 24                         # past midnight
        nowSec = now_hh*3600 + now_mm*60 + now_ss
        waitSec = LoopSec + loopInterval + 10 - nowSec   # until next loop including 10 secs spare
        if waitSec<10:
            waitSec = 60                        # was even negative sometimes
    then = datetime.now() + timedelta(seconds=waitSec)
    thenStr = format(then, '%H:%M')
    print ('\nWaiting ' + str(waitSec) + 'sec for next loop at '+ thenStr + ';   Variant "' + varName + '"')
    return waitSec

def alarmHours(titel):
    ###########################################################################
    #   the alarm hours dialog
    ###########################################################################
    btns = ["Next", "Exit"]
    items = ["00","01","02","03","04","05","06","07","08","09","10","11","12","13","14","15","16","17","18","19","20","21","22","23"]
    pick  = [                             7,  8,  9,  10,  11,  12,  13,  14,  15,  16,  17,  18,  19,  20,  21,  22      ]
    while True:
        default_pick = pick
        pressed_button, selected_items_indexes = mydialog("Pick alarm hours for\n"+titel, btns, items, True, default_pick)
        pick = selected_items_indexes
        if   pressed_button ==-1:           sys.exit()                      # external BREAK
        #lif selected_items_indexes == []:  sys.exit()                      # all declined
        elif pressed_button == 0:           break                           # NEXT
        elif pressed_button == 1:           sys.exit()                      # EXIT
    return pick

#def echo_version(mdl):
#    global echo_msg
#    #mdl= 'vary_settings_batch.py'
#    stamp = os.stat(varyHome + mdl)
#    stposx= datetime.fromtimestamp(stamp.st_mtime)
#    ststr = datetime.strftime(stposx, "%Y-%m-%d %H:%M:%S")
#    echo_msg[ststr] = mdl
#    return 

###############################################
###    start of main                        ###
###############################################

#how_to_print = 'GUI'
how_to_print = 'print'
#et_tty(runframe, lfd,  how_to_print)            # export print settings to main routine
set_tty(0,        0,    how_to_print)            # export print settings to main routine

global echo_msg

# try whether we are on Android:
IsAndroid = False
test_dir10= '/storage/emulated/0/Android/data/info.nightscout.androidaps/files/'    # always find it even when starting new logfile
test_file = 'AndroidAPS.log'
inh10     = glob.glob(test_dir10+'*')            # for Android10 or less using AAPS 2.8.2
if len(inh10) > 0:
    IsAndroid = True
    test_dir = test_dir10
    fn = test_dir + test_file

test_dir11= '/storage/emulated/0/AAPS/logs/info.nightscout.androidaps/'
inh11     = glob.glob(test_dir11+'*')            # for Android11+ using AAPS 3.0+
if len(inh11) > 0:
    IsAndroid = True
    test_dir = test_dir11
    fn = test_dir + test_file
    
if IsAndroid :
    #import androidhelper
    #droid=androidhelper.Android()
    from androidhelper import Android
    droid = Android()
    #ClearScreenCommand = 'clear'                                           # done in --core.py
    
    #inh = glob.glob(test_dir+'files/AndroidAPS.log')
    #fn = inh[0]
    myseek  = fn

    ###########################################################################
    #   the language dialog
    ###########################################################################
    btns  = {"N":"Next", "T":"Test", "E":"Exit"}
    items = {"1":"Dieses Smartphone spricht Deutsch", "2":"This smartphone speaks English"}
    pick = "1"
    pressed_button = "N"
    while True:                                                             # how the lady speaks ...
        pressed_button, pick, done = dialog1('Languages', btns, pressed_button, items, pick)
        #pick = selected_items_indexes[0]
        if done and pressed_button == "N":         break                           # NEXT
        elif        pressed_button == "E":         sys.exit()                      # EXIT
        elif        pressed_button == "T":         droid.ttsSpeak(items[pick])     # TEST
        
    if   pick == "1":
        textLessSMB = 'Die neuen Einstellungen hätten weniger Bolus vorgeschlagen, nämlich um '
        textMoreSMB = 'Die neuen Einstellungen schlagen einen extra Bolus vor, nämlich '
        textUnit= ' Einheiten'
        both_ansage  = 'Prüf doch Mal die Lage.'
        carb_ansage0 = 'Du brauchst eventuell Kohlenhydrate,'
        both_ansage1 = 'und zwar circa'
        carb_ansage2 = 'Gramm in den nächsten'
        carb_ansage3 = 'Minuten'
        Speak_items = ["Extra Kohlenhydrate", "Extra Bolus", "Zuviel Bolus"]
        Speak_Pick  = "Wähle Ansagen"
    elif pick == "2":
        textLessSMB = 'the new settings would have suggested less bolus by '
        textMoreSMB = 'the new settings suggest an extra bolus, namely '
        textUnit= ' units'
        both_ansage  = 'Houston, we may have a situation.'
        carb_ansage0 = 'You may need carbohydrates,'
        both_ansage1 = 'namely about'
        carb_ansage2 = 'grams during the next'
        carb_ansage3 = 'minutes'
        Speak_items = ["extra carbs", "extra bolus", "less bolus"]
        Speak_Pick  = "Pick Items"       


    ###########################################################################
    #   the  variant definition file dialog
    ###########################################################################
    btns  = {"N":"Next", "E":"Exit"}
    items = {}
    varD = glob.glob(test_dir+'/*.dat')                     # outdated naming
    fcount = 1
    for varFile in varD:
        items[str(fcount)] = os.path.basename(varFile)      # do not overwrite the calling arg value
        fcount += 1
    varF = glob.glob(test_dir+'/*.vdf')                     # preferred new naming
    for varFile in varF:
        items[str(fcount)] = os.path.basename(varFile)      # do not overwrite the calling arg value
        fcount += 1
    pick = "1"
    pressed_button = "N"
    while True:
        pressed_button, pick, done = dialog1('vdf-files', btns, pressed_button, items, pick)
        #pick = selected_items_indexes[0]
        if done and pressed_button == "N":         break                           # NEXT
        elif        pressed_button == "E":         sys.exit()                      # EXIT
        #lif        pressed_button == "S":         droid.ttsSpeak(items[pick])     # SHOW

    #if pressed_button != 0 or selected_items_indexes == []:
    #    sys.exit()    
    varFile = test_dir+items[pick]
    

    ###########################################################################
    #   the config file  dialog
    ###########################################################################
    btns  = {"N":"Next", "E":"Exit"}
    items = {}
    my_decimal = '.'
    cfgF = glob.glob(test_dir+'/*.config')
    fcount = 1
    for cfgFile in cfgF:
        items[str(fcount)] = os.path.basename(cfgFile)
        fcount += 1
    if fcount == 1:
        print('\nWARNING: config file is missing\nin logfile folder\nget config file and restart app')
        ans = input('\npress ENTER')
        sys.exit()
    pick = "1"
    pressed_button = "N"
    while True:
        pressed_button, pick, done = dialog1('config-files', btns, pressed_button, items, pick)
        #pick = selected_items_indexes[0]
        if done and pressed_button == "N":         break                           # NEXT
        elif        pressed_button == "E":         sys.exit()                      # EXIT
        #lif        pressed_button == "S":         droid.ttsSpeak(items[pick])     # SHOW

    #fnam= varLabel + '.dat'
    cfg = open(test_dir+items[pick], 'r')
    next_row= 'extraCarbs'
    for zeile in cfg:
        key = zeile[:1]
        #print (next_row, key, zeile)
        if key == '[' :
            List = []
            wo = zeile.find(']')
            eleList = zeile[1:wo].split(',')    
            if '' not in eleList :              # otherwise empty for no alarms at all
                for i in range(len(eleList)):
                    List.append(eval(eleList[i]))
        else:
            wo = zeile.find('}')
            zeile = zeile[:wo+1]
            
        if next_row == 'extraCarbs':
            pickExtraCarbs = List
            next_row = 'extraBolus'
        elif next_row == 'extraBolus':
            pickMoreSMB = List
            next_row = 'lessBolus'
        elif next_row == 'lessBolus':
            pickLessSMB = List
            next_row = 'outputs'
        elif next_row == 'outputs':
            arg2 = 'Android/'+my_decimal
            outputJson = json.loads(zeile)
            #print('vorher :', str(outputJson))
            total_width = 6                         # base time in hh:mmZ
            for ele in outputJson:
                width = outputJson[ele]
                if width>0:
                    arg2 += '/'+ele
                    total_width += width
            input('Total width of output table is '+str(total_width)+'\nPress Enter to continue')
            next_row = 'end'
    cfg.close()
        
        
    ###########################################################################
    #   the display items dialog
    ###########################################################################
    btns = ["Next", "Exit", "Test"]
    items = ["bg", "target", "iob", "cob", "range", "bestslope", "autosens", "acce_ISF", "bg_ISF", "pp_ISF", "delta_ISF", "dura_ISF", "ISFs", "insReq", "SMB", "basal"]
    width = [9,     6,        6,      6,      13,      13,             6,         6,        6,         6,         6,           6,       20,      13,      11,     12  ]
    pick  = [0,               2,                                       6,         7,        8,         9 ,                    10,       11,      12,      13,     14  ]
    while not True:
        default_pick = pick
        pressed_button, selected_items_indexes = mydialog("Pick outputs", btns, items, True, default_pick)
        pick = selected_items_indexes
        if   pressed_button ==-1:           sys.exit()                      # external BREAK
        elif selected_items_indexes == []:  sys.exit()                      # all declined
        elif pressed_button == 0:           break                           # NEXT
        elif pressed_button == 1:           sys.exit()                      # EXIT
        elif pressed_button == 2:                                           # TEST
            cols = 9                                                        # always: time column
            for i in selected_items_indexes:
                cols += width[i]                                            # add selected column width
            droid.ttsSpeak(str(cols))                                       # tell the sum

    #arg2 = 'Android/.'+''.join(['/'+items[i] for i in selected_items_indexes])# the feature list what to plot
    #arg2+= '/.'                                                            # always decimal "." on Android
    varyHome= '/storage/emulated/0/qpython/scripts3/'                       # command used to start this script
    #varyHome = os.path.dirname(varyHome) + '\\'
    m  = '='*66+'\nEcho of software versions used\n'+'-'*66
    m +='\n vary_settings home directory  ' + varyHome
    #global echo_msg
    echo_msg = {}
    echo_msg = get_version_batch(echo_msg)
    echo_msg = get_version_core(echo_msg)
    echo_msg = get_version_determine_basal(echo_msg)
    for ele in echo_msg:
        m += '\n dated: '+echo_msg[ele] + '       module name: '+ele
    m += '\n' + '='*66 + '\n'


    #print ('VDF file:', varFile)
    #print (str(arg2))
    #sys.exit()


    ###########################################################################
    #   no more dialogs; go ahead
    ###########################################################################            
    t_stoppLabel = '2099-00-00T00:00:00Z'           # defaults to end of centuary, i.e. open end
    t_startLabel = '2000-00-00T00:00:00Z'           # defaults to start of centuary, i.e. open start
else:                                                                               # we are not on Android
    #IsAndroid = False
    #Settings for development on Windows with SMB events:
    #test_dir  = 'L:\PID\ISF\Android/'
    #test_file = 'AndroidAPS._2020-07-13_00-00-00_.2.zip'
    #fn = test_dir + test_file
    #ClearScreenCommand = 'cls'                     # done in --core.py
    maxItem = '144'    # shows all

    varyHome= sys.argv[0]                           # command used to start this script
    whereColon = varyHome.find(':')
    if whereColon < 0:
        varyHome = os.getcwd()
    varyHome = os.path.dirname(varyHome) + os.sep   #'\\'
    m  = '='*66+'\nEcho of software versions used\n'+'-'*66
    m +='\n vary_settings home directory  ' + varyHome
    #global echo_msg
    echo_msg = {}
    echo_msg = get_version_batch(echo_msg)
    echo_msg = get_version_core(echo_msg)
    echo_msg = get_version_determine_basal(echo_msg)
    for ele in echo_msg:
        m += '\n dated: '+echo_msg[ele] + '       module name: '+ele
    m += '\n'+'-'*66+'\nEcho of execution parameters used\n'+'-'*66
    m += '\nLogfiles to scan      ' + sys.argv[1]
    m += '\nOutput options        ' + sys.argv[2]
    m_default = ''
    if sys.argv[2].find('.') >= 0 :
        my_decimal = '.'
    elif sys.argv[2].find(',') >= 0 :
        my_decimal = ',' 
    else:
        my_decimal = ','
        m_default = ' (default)'                   # the default
    m += '\nDecimal symbol        ' + my_decimal + m_default
    myseek  = sys.argv[1] #+ '\\'
    arg2    = 'Windows/' + sys.argv[2]              # the feature list of what to plot
    varFile = sys.argv[3]                           # the variant label
    if len(sys.argv)>=5:
        t_startLabel = sys.argv[4]                  # first loop time to evaluate#
        m_default = ''
    else:
        t_startLabel = '2000-00-00T00:00:00Z'       # defaults to start of centuary, i.e. open start
        m_default = ' (default)'
    m += '\nStart of time window  ' + t_startLabel + m_default
    if len(sys.argv)>=6:
        t_stoppLabel = sys.argv[5]                  # last loop time to evaluate
        m_default = ''
    else:
        t_stoppLabel = '2099-00-00T00:00:00Z'       # defaults to end of centuary, i.e. open end
        m_default = ' (default)'
    m += '\nEnd of time window    ' + t_stoppLabel + m_default
    if len(sys.argv)==7:
        # load the emulated bg history from dialog database
        m += '\nBG_emul data table    t_'+ sys.argv[6]
    m += '\n' + '='*66 + '\n'

#print ('evaluate from '+t_startLabel+' up to '+t_stoppLabel)

wdhl = 'yes'
entries = {}
lastTime = '0'
while wdhl[0]=='y':                                                                 # use CANCEL to stop/exit
    # All command line arguments known, go for main process
    loopInterval, thisTime, extraSMB, CarbReqGram, CarbReqTime, lastCOB, fn_first = parameters_known(myseek, arg2, varFile, t_startLabel, t_stoppLabel, entries, m, my_decimal)
    if thisTime == 'SYNTAX':        break                                           # problem in VDF file
    if thisTime == 'UTF8':          break                                           # PATHONUTF8 nor defined or incorrect
    #print('returned vary_ISF_batch:', CarbReqGram, ' minutes:',  CarbReqTime)
    if IsAndroid:
        thisHour = datetime.now()
        thisStr  = format(thisHour, '%H')
        if thisStr[0] == '0':       thisStr = thisStr[1]                            # could not EVAL('01', only '1')
        thisInt  = eval(thisStr)
        valGram = eval(CarbReqGram+'+0')
        val_lastCOB = eval(str(lastCOB)+'+0')
        #print("Zeitslot:", thisInt, str(pickExtraCarbs))
        #print("extra carbs", str(thisInt in pickExtraCarbs), valGram, str(lastCOB))
        if (thisInt in pickExtraCarbs) and valGram !=0 and valGram-val_lastCOB>6:  # only report if min 0,5 BE missing
            AlarmTime = CarbReqTime
            valTime = eval(AlarmTime)
            #valGram = eval(AlarmGram)
            signif  = valTime / valGram
            if signif<5 and thisTime>lastTime:                                      # above threshold of significance
                droid.ttsSpeak(both_ansage)
                droid.ttsSpeak(carb_ansage0)
                droid.ttsSpeak(both_ansage1 + str(valGram) + carb_ansage2 + AlarmTime + carb_ansage3)
        #print("extra bolus", str(thisInt in pickMoreSMB), str(extraSMB))
        if (thisInt in pickMoreSMB) and extraSMB>0 and thisTime>lastTime:
            droid.ttsSpeak(textMoreSMB+str(extraSMB)+textUnit)                      # wake up user, also during sleep?
        #print("less  bolus", str(thisInt in pickLessSMB), str(extraSMB))
        if (thisInt in pickLessSMB) and extraSMB<0 and thisTime>lastTime:
            droid.ttsSpeak(textLessSMB+str(extraSMB)+textUnit)                      # wake up user, also during sleep?
        howLong = waitNextLoop(loopInterval, thisTime, varFile[len(test_dir):-4])
        lastTime = thisTime        
        time.sleep(howLong)
    else:   break                                                                   # on Windows run only once

sys.exit()

