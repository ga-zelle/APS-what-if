import sys
import os
import glob
import time
from datetime import datetime, timedelta

from vary_ISF_core import parameters_known
from vary_ISF_core import set_tty

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
    return res0,res

def waitNextLoop(arg):                      # arg = hh:mm:ss of last loop execution, optionally appended 'Z'
    #E started 05.Nov.2019
    if arg == 'Z':                              # no entry found for SMB loop
        waitSec = 310                           # this shoud include at leat 1 loop
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
        waitSec = LoopSec + 300 + 10 - nowSec   # until next loop including 10 secs spare
        if waitSec<10:
            waitSec = 60                        # was even negative sometimes
    then = datetime.now() + timedelta(seconds=waitSec)
    thenStr = format(then, '%H:%M')
    print ('\nwaiting ' + str(waitSec) + ' sec for next loop at '+thenStr)
    return waitSec


###############################################
###    start of main                        ###
###############################################

#how_to_print = 'GUI'
how_to_print = 'print'
#et_tty(runframe, lfd,  how_to_print)            # export print settings to main routine
set_tty(0,        0,    how_to_print)            # export print settings to main routine


# try whether we are on Android:
test_dir  = '/storage/emulated/0/Android/data/info.nightscout.androidaps/files/'
test_dir  = '/storage/emulated/0/Android/data/info.nightscout.androidaps/'          # always find it even when starting new logfile
test_file = 'AndroidAPS.log'
inh = glob.glob(test_dir+'*')
#print (str(inh))
if len(inh) > 0:
    IsAndroid = True
    import androidhelper
    droid=androidhelper.Android()
    
    inh = glob.glob(test_dir+'files/*.log')
    fn = inh[0]

    myseek  = fn

    btns = ["Next", "Exit", "Test"]
    items = ["Dieses Smartphon spricht Deutsch", "This smartphone speaks English"]
    pick = 0
    while True:                                                             # how the lady speaks ...
        default_pick = [pick]
        pressed_button, selected_items_indexes = mydialog("Pick Language", btns, items, False, default_pick)
        pick = selected_items_indexes[0]
        if   pressed_button ==-1:           sys.exit()                      # external BREAK
        if   pressed_button == 0:           break                           # NEXT
        elif pressed_button == 1:           sys.exit()                      # EXIT
        elif pressed_button == 2:           droid.ttsSpeak(items[pick])     # TEST
    if pick == 0:
        textSMB = 'Der neue I-S-F Algorithmus schlägt einen extra Bolus vor, nämlich '
        textUnit= ' Einheiten'
        both_ansage  = 'Prüf doch Mal die Lage.'
        carb_ansage0 = 'Du brauchst eventuell Kohlenhydrate,'
        both_ansage1 = 'und zwar circa'
        carb_ansage2 = 'Gramm in den nächsten'
        carb_ansage3 = 'Minuten'
        Speaker = 'Frau'
    else:
        textSMB = 'the new ISF algorithm suggests an extra bolus, namely '
        textUnit= ' units'
        both_ansage  = 'Houston, we may have a situation.'
        carb_ansage0 = 'You may need carbohydrates,'
        both_ansage1 = 'namely about'
        carb_ansage2 = 'grams during the next'
        carb_ansage3 = 'minutes'
        Speaker = 'Lady'
        
    btns = ["Next", "Exit"]
    items = ["bg", "target", 'as_ratio', "cob", "range", "slope", "ISF", "insReq", "SMB", "basal"]
    default_pick = [0,                              4,      5,      6,      7,      8,      9]
    pressed_button, selected_items_indexes = mydialog("Pick outputs", btns, items, True, default_pick)
    if pressed_button != 0 or selected_items_indexes == []:
        sys.exit()    
    arg2 = 'Android' + ''.join(['/'+items[i] for i in selected_items_indexes])       # the feature list what to plot
    
    varF = glob.glob(test_dir+'files/*.dat')
    lstF = []   #[i for i in varF]
    for varFile in varF:
        lstF.append(os.path.basename(varFile))      # do not overwrite the calling arg value
    pressed_button, selected_items_indexes = mydialog("Pick variant file", btns, lstF, False)
    if pressed_button != 0 or selected_items_indexes == []:
        sys.exit()    
    varFile = test_dir + 'files/' + ''.join([lstF[i] for i in selected_items_indexes])

    t_stoppLabel = '2099-00-00T00:00:00Z'           # defaults to end of centuary, i.e. open end
    t_startLabel = '2000-00-00T00:00:00Z'           # defaults to start of centuary, i.e. open start
else:                                                                               # we are not on Android
    IsAndroid = False
    #Settings for development on Windows with SMB events:
    #test_dir  = 'L:\PID\ISF\Android/'
    #test_file = 'AndroidAPS._2020-07-13_00-00-00_.2.zip'
    #fn = test_dir + test_file
    ClearScreenCommand = 'cls'
    maxItem = '144'    # shows all

    myseek  = sys.argv[1] #+ '\\'
    arg2    = 'Windows/' + sys.argv[2]              # the feature list what to plot
    varFile = sys.argv[3]                           # the variant label
    if len(sys.argv)>=6:
        t_stoppLabel = sys.argv[5]                  # last loop time to evaluate
    else:
        t_stoppLabel = '2099-00-00T00:00:00Z'       # defaults to end of centuary, i.e. open end
    if len(sys.argv)>=5:
        t_startLabel = sys.argv[4]                  # first loop time to evaluate
    else:
        t_startLabel = '2000-00-00T00:00:00Z'       # defaults to start of centuary, i.e. open start
#print ('evaluate from '+t_startLabel+' up to '+t_stoppLabel)

wdhl = 'yes'
entries = {}
lastTime = '0'
while wdhl[0]=='y':                                                                 # use CANCEL to stop/exit
    # All command line arguments known, go for main process
    thisTime, extraSMB, CarbReqGram, CarbReqTime, lastCOB = parameters_known(myseek, arg2, varFile, t_startLabel, t_stoppLabel, entries)

    #print('returned vary_ISF_batch:', CarbReqGram, ' minutes:',  CarbReqTime)
    if IsAndroid:
        AlarmGram = CarbReqGram
        if AlarmGram !='' and eval(AlarmGram)-lastCOB>6:                            # only report if min 0,5 BE missing
            AlarmTime = CarbReqTime
            valTime = eval(AlarmTime)
            valGram = eval(AlarmGram)
            signif  = valTime / valGram
            if signif<5 and thisTime>lastTime:                                      # above threshold of significance
                droid.ttsSpeak(both_ansage)
                droid.ttsSpeak(carb_ansage0)
                droid.ttsSpeak(both_ansage1 + AlarmGram + carb_ansage2 + AlarmTime + carb_ansage3)
        if extraSMB>0 and thisTime>lastTime:
            droid.ttsSpeak(textSMB+str(extraSMB)+textUnit)                          # wake up user, also during sleep?
        howLong = waitNextLoop(thisTime)
        lastTime = thisTime        
        time.sleep(howLong)
    else:   break                                                                   # on Windows run only once

sys.exit()

