from collections import deque
import signal
import code
import sys
import subprocess
import os
import threading
import time
import ctypes
import cPickle
import traceback

try:
   # For interpreter arrow/history functionality
   import readline
except:
   pass

# Example usage...

"""
import debug
import time
def main():
   # Use Ctrl+\ in this loop to being up an interpreter to play with
   # variables in your code, or get reports regarding objects, memory,
   # and cpu utilization (CPU isn't useful since the main loop is paused)
   try:
      while True:
         try:
            time.sleep(1)
            print "zzz...", time.ctime()
            
         except debug.DebugException:
            # Catch & Release...
            # catch Ctrl+\ for debug mode, then release back into main loop!
            exec debug.normalHandler
      
   except debug.SelfDestructException, message:
      # get a report about why the process died
      print message
   finally:
      # remember to stop the thread! (or it'll live forever, keeping you program alive!)
      debug.selfDestructThread.stop()
      debug.selfDestructThread.join()

main()
"""

_signal = signal.SIGQUIT

hasSignaled = False

normalHandler ="""
print "===[ COMMANDS ]==="
print
print "List Objects:"
print "   report"
print "   report more"
print "   dir()"
print "   locals()"
print "   globals()"
print "Inspect a specific object:"
print "   debug.ObjSize.getSize( obj )"
print "   debug.showObj( obj )"
print "Process Information:"
print "   proc"
print "Test the self destruct:"
print "   stress test"
print 

banner  = "-----------------------------------------------------------------\\n"
banner += "Debug Shell."
shell = debug.Shell(dict(globals(), **locals()))
shell.interact(banner)
""" 


cursesHandler ="""
curses.def_prog_mode()
curses.endwin()
%s
curses.reset_prog_mode()
""" % normalHandler



############################################################################
# Signal Handling
############################################################################

class DebugException(Exception): pass

def handleSignal(signum, stack):
   global hasSignaled
   hasSignaled = True
   raise DebugException()



############################################################################
# General
############################################################################

def pretty(d, indent=0):
   for key, value in d.iteritems():
     if isinstance(value, dict):
       pretty(value, indent+1)
     else:
       print '   ' * (indent+1) + str(value)


class SimpleMovingAverage():
   def __init__(self, period):
      self.period = period
      self.stream = deque(maxlen=int(period))
   
   def __len__(self):
      return len(self.stream)
   
   def __call__(self, point):
      if isinstance(point, (int, long, float, complex)):
         self.stream.append(point)
      if len(self.stream) == 0:
         average = 0
      else:
         average = sum( self.stream ) / float(len(self.stream))
      
      return average



############################################################################
# Self Destruction Functionality
############################################################################

class SelfDestructException(Exception): pass

class SelfDestruct():
   """
   This class monitors the CPU/memory utilization of the current process and 
   raises an exception when a predetermined threshold is crossed.
   """
   # DEFAULT THRESHOLD:                   10%      or             100MB
   def __init__(self, percentCpuThreshold=10.0, rssBytesThreshold=102400, period=10):
      self.cpuThreshold = float(percentCpuThreshold)
      self.rssThreshold = float(rssBytesThreshold)
      self.avgCpuObj = SimpleMovingAverage(period=10)
      self.avgRssObj = SimpleMovingAverage(period=10)
      self.curCpu = 0.0
      self.curRss = 0.0
      self.cpuAvg = 0.0
      self.rssAvg = 0.0
   
   def _exit(self, error):
      raise SelfDestructException(error)
   
   def report(self):
      try:
         report  = "CPU Percent [Cur/Avg/Threshold]: %s  /  %s  /  %s\n" % ( str(self.curCpu), str(self.cpuAvg), str(self.cpuThreshold) )
         report += "Mem KBytes  [Cur/Avg/Threshold]: %s  /  %s  /  %s\n" % ( str(self.curRss), str(self.rssAvg), str(self.rssThreshold) )
      except:
         report = "CPU/Mem Status Unknown\n"
      return report
   
   def check(self):
      psPMEM, psRSSMemory, psPCPU, psTime = ProcMon.collect(os.getpid())
      self._checkThresholds(float(psPCPU), float(psRSSMemory))
   
   def _checkThresholds(self, percCpu, rssBytes):
      self.cpuAvg = float(self.avgCpuObj(percCpu))
      self.rssAvg = float(self.avgRssObj(rssBytes))
      
      self.curCpu = percCpu
      self.curRss = rssBytes
      
      if self.cpuAvg > self.cpuThreshold and len(self.avgCpuObj) == self.avgCpuObj.period:
         error  = "CPU Perc [Cur/Avg/Threshold]: %s  /  %s  /  %s\n" % ( str(self.curCpu), str(self.cpuAvg), str(self.cpuThreshold) )
         error += "CPU Perc Observations: %s\n" % str(self.avgCpuObj.stream)
         error += "Self-Destruct!\n"
         self._exit(error)
      if self.rssAvg > self.rssThreshold and len(self.avgRssObj) == self.avgRssObj.period:
         error  = "Mem KBytes [Cur/Avg/Threshold]: %s  /  %s  /  %s\n" % ( str(self.curRss), str(self.rssAvg), str(self.rssThreshold) )
         error += "Mem KBytes Observations: %s\n" % str(list(self.avgRssObj.stream))
         error += "Self-Destruct!\n"
         self._exit(error)


class SelfDestructThread(threading.Thread):
   
   """
   Facilitates process self destruction in another thread via the SelfDestruct object.
   """
   
   def __init__(self, interval= 0.2):
      threading.Thread.__init__(self)
      self.pid = os.getpid()
      self.sd = SelfDestruct(period=20) # keep longer than native Monitor
      self.stopped = False
      self.interval = interval
      self.start()
   
   def isStopped(self):
      return self.stopped
   
   def stop(self):
      self.stopped = True
   
   def report(self):
      return self.sd.report()
   
   def run(self):
      try:
         while not self.stopped:
            self.sd.check()
            start = time.time()
            while self.interval > time.time() - start:
               time.sleep(0.1)
      except:
         print "Monitor Thread is Dead!"
         traceback.print_exc()
      
         try:
            print self.sd.report()
         except:
            print "Reason not available."
         
         # call this script!
         os.system("python debug.py kill %s '%s' \"%s\"" % (str(self.pid), str(self.name), str(self.sd.report())) )
         
         # No matter what, always exit this process
         os._exit(0)



############################################################################
# Interpreter
############################################################################


class FileCacher:
   "Cache the stdout text so we can analyze it before returning it"
   def __init__(self): 
      self.reset()
   
   def reset(self): 
      self.out = []
   
   def write(self,line): 
      self.out.append(line)
   
   def flush(self):
      #output = '\n'.join(self.out)
      output = ''.join(self.out)
      self.reset()
      return output
      #return self.out



class Shell(code.InteractiveConsole):
   "Wrapper around Python that can filter input/output to the shell"
   
   scope = None
   
   def __init__(self, scope=None):
      self.stdout = sys.stdout
      self.cache = FileCacher()
      self.scope = scope
      if scope == None:
         code.InteractiveConsole.__init__(self)
      else:
         code.InteractiveConsole.__init__(self, scope)
      return

   def get_output(self): 
      sys.stdout = self.cache
   
   def return_output(self): 
      sys.stdout = self.stdout

   #Filter user input; do commands like 'version' and 'help'
   def checkForBuiltInCommands(self, line):
      if line == "exit":
         self.return_output()
         output = self.cache.flush()
         raise EOFError
      elif line == "report":
         report(self.scope)
      elif line == "report more":
         report(self.scope, True)
      elif line == "proc":
         ProcMon.report(os.getpid())
      elif line == "stress test":
         t = [[[],[],[],[],[]] for _ in xrange(3000000)]
      else:
         return False
      return True
         
   def push(self,line):
      self.get_output()
      
      #Filter user input; do commands like 'version' and 'help' 
      if self.checkForBuiltInCommands(line) == False:
         #Commit user input to python console
         code.InteractiveConsole.push(self,line)
      
      #Show output...
      self.return_output()
      output = self.cache.flush()
      # filter output example
      # output = filter(output)
      
      #Show Output before prompt
      if output != "":
         print output




###########################################################################
# Process Utilities
###########################################################################


class ProcMon(object):
   
   @staticmethod
   def report(pid):
      psPMEM, psRSSMemory, psPCPU, psTime = ProcMon.collect(pid)
      header = "Process Info (%s)" % str(pid)
      print header
      print "="*len(header)
      print "% Mem   :", psPMEM
      print "% CPU   :", psPCPU
      print "RSS Mem :", psRSSMemory
      print "CPU Time:", psTime
   
   # returns %MEM, psRSSMemory, %CPU, psCpuTime
   @staticmethod
   def collect(pid):
      process = subprocess.Popen("ps -p %s -o pmem,rss,pcpu,time " % str(pid),
                              shell=True,
                              stdout=subprocess.PIPE,
                              )
      stdout_list = process.communicate()[0].split('\n')
      
      # casting for validation
      try:
         fields = stdout_list[1].split()
         psPMEM = str(float(fields[0]))
         psRSSMemory = str(int(fields[1]))
         psPCPU = str(float(fields[2]))
         # convert hh:mm:ss to seconds
         psTime = str(sum(int(x) * 60 ** i for i,x in enumerate(reversed(fields[3].split(":")))))
      except:
         traceback.print_exc()
         psPMEM, psRSSMemory, psPCPU, psTime = ( "-1", "-1", "-1", "-1" )
      return psPMEM, psRSSMemory, psPCPU, psTime


###########################################################################
# Memory Utilities (ish)
###########################################################################


class ObjSize():
   
   @staticmethod
   def getSize(obj):
      try:
         return ctypes.sizeof(obj)
      except:
         return ObjSize._getPickleSize(obj)
   
   @staticmethod
   def _getPickleSize(obj):
      return sys.getsizeof(cPickle.dumps(obj, cPickle.HIGHEST_PROTOCOL))


# pass in globals() or locals()... or just a dictionary of objects
def report(scope, detailed=False):
   print ""
   print "%-20s : %-s" % ("OBJECT","SIZE (BYTES)")
   print "%-20s : %-s" % ("======","============")
   for name, obj in scope.items():
      if "at 0x" in str(obj):
         if detailed == True:
            try:
               print name
               showObj(obj, indent=3)
            except:
               try:
                  print "%-20s : %-s" % (str(name), ObjSize.getSize(obj))
               except:
                  print "%-20s : %-s" % (str(name), "No report!")
         else:
            try:
               print "%-20s : %-s" % (str(name), ObjSize.getSize(obj))
            except:
               print "%-20s : %-s" % (str(name), "No report!")


def showObj(obj, indent=0):
   
   def getShallowDistribution(obj):
      import inspect
      ret = {}
      
      for member, value in inspect.getmembers(obj):
         
         if member[-2:] != "__" and "method" not in str(type(value)):
            #print type(value), member
            ret[str(member)] = ObjSize.getSize(value)
         
      return ret
   
   # Entry Point
   
   dist = getShallowDistribution(obj)
   
   totalVal = sum(dist.values())
   maxVal = max(dist.values())
   minVal = min(dist.values())
   
   # chars across...
   showSize = 20
   
   showStr = "%s%-25s  %-8s [ %s%s ] %-20s" #% (indent, item, str(itemSize),"#"*itemSize, "."*(totalSize-itemSize), type )
   
   for member, size in dist.items():
      relSize = float(size) #float(size-minVal)
      percItem = relSize/float(maxVal)
      
      itemCharCount = int(showSize*percItem)
      itemType = str(type(eval("obj."+member)))
      
      print showStr % (" "*indent,member, str(size),"#"*itemCharCount, "."*(showSize-itemCharCount), itemType )
   
   print "%s%-25s  %-8s" % ( " "*indent,"Total Size", totalVal )
   print ""

###########################################################################
# Main / Import
###########################################################################


if __name__ == '__main__':
   # usage:
   #   python debug.py kill <pid> ['name'] ["reason"]
   #
   arg = str(sys.argv[1]).strip()
   if arg == "kill":
      pid = int(sys.argv[2])
      try:
         name = str(sys.argv[3])
      except:
         name = "???"
         
      try:
         reason = str(sys.argv[4])
      except:
         reason = ""
         
      os.kill(pid, signal.SIGKILL)
      os.system("reset; echo '\n\nProc %s killed because it took up too many resources!\n%s\n'" % (str(pid), str(reason)) )
   else:
      print "Nothing done!"
else:
   # Self Destruct Polling Obj (nicer reporting)
   selfDestructObj = SelfDestruct()
   
   # Self Destruct Thread (lags just behind the poller, but is an absolute)
   selfDestructThread = SelfDestructThread()
   
   # upon import, register the sigquit (Ctrl+\)
   signal.signal(_signal,handleSignal)



# Optional Usage
class DebugSession(object):
   
   def __init__ (self, globalVars):
      self.globals = globalVars

   def __call__ (self, func, *args):
   
      # Use Ctrl+\ in this loop to being up an interpreter to play with
      # variables in your code, or get reports regarding objects, memory,
      # and cpu utilization (CPU isn't useful since the main loop is paused)
      try:
         
         return func(*args)
         
      except DebugException:
         # Catch & Release...
         # catch Ctrl+\ for debug mode, then release back into main loop!
         exec normalHandler in self.globals
         
      except SelfDestructException, message:
         # get a report about why the process died
         print message
         
      finally:
         # remember to stop the thread! (or it'll live forever, keeping you program alive!)
         selfDestructThread.stop()
         selfDestructThread.join()

   
