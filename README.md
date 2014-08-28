PyDebugShell
============

A python module which can be used to interrupt a script and inspect running objects or self destruct a run-away script

Strike Ctrl+\ during execution of any python script which utilizes this module to get to an interactive pythgon shell and inspect local/global objects:

```
===[ COMMANDS ]===

List Objects:
   report
   report more
   dir()
   locals()
   globals()
Inspect a specific object:
   debug.ObjSize.getSize( obj )
   debug.showObj( obj )
Process Information:
   proc
Test the self destruct:
   stress test

-----------------------------------------------------------------
Debug Shell.
>>> 

```

Import the debug module and add a specific try/except anywhere in your code:

```python
import debug
import time

def main():

  try:
  
    while True:
      ...
      ...

  except debug.DebugException:
    exec debug.normalHandler
        
  except debug.SelfDestructException, message:
      print message
      
  finally:
    debug.selfDestructThread.stop()
    debug.selfDestructThread.join()
```

Or use the given decorator on a long running method:

```python
@debug.DebugSession(globals())
def main():
  ...
  ...

main()
```

If the CPU utilization goes beyond 10% for a  long enough duration, or memory utilization spikes above 1024MB then 
the process will automatically killed and show this message:

```
Proc 19008 killed because it took up too many resources!
CPU Percent [Cur/Avg/Threshold]: 17.7  /  4.25  /  10.0
Mem KBytes  [Cur/Avg/Threshold]: 180612.0  /  102968.8  /  102400.0
```

This is not production worthy! Please only use this while developing.
