import sys

from vary_settings_core import parameters_known
from vary_settings_core import set_tty



###############################################
###    start of main                        ###
###############################################

#how_to_print = 'GUI'
how_to_print = 'print'
#et_tty(runframe, lfd,  how_to_print)            # export print settings to main routine
set_tty(0,        0,    how_to_print)            # export print settings to main routine


myseek  = sys.argv[1] #+ '\\'
arg2    = sys.argv[2]                           # the feature list what to plot
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

# All command line arguments known, go for main process
parameters_known(myseek, arg2, varFile, t_startLabel, t_stoppLabel)

sys.exit()

