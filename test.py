# Start the self-destruct thread. Even a blocked process
# taking up too much resources will be killed & report
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
