import threading
import time

class PeriodicTask:
    """generic class to start threads
    """    
    def __init__(self, interval, task_function,task_name=None):
        """initializes the class

        Args:
            interval (int): interval seconds
            task_function (any): task function to execute
        """        
        self.task_name=task_name
        self.interval = interval
        self.task_function = task_function
        self._stop_event = threading.Event()

        
        # self.thread = threading.Thread(target=self._run)
        self.thread = threading.Timer(interval=self.interval,function=self._run)
        
    
    def start(self):
        if self.task_name:
            print(f"Starting thread {self.task_name}")
        self.thread.start() 

    def _run(self):
        while not self._stop_event.is_set():
            self.task_function()  
            self._stop_event.wait(timeout=self.interval)

    def stop(self):
        self._stop_event.set()
        self.thread.join()

# test function
def my_task():
    print("Tarea periódica ejecutada", time.strftime("%Y-%m-%d %H:%M:%S"))

# Uso
if __name__ == "__main__":
    task = PeriodicTask(interval=5, task_function=my_task)  # Ejecutar `my_task` cada 5 segundos

    try:
        while True:
            time.sleep(1)  # Mantener el programa principal en ejecución
    except KeyboardInterrupt:
        task.stop()  # Detener el hilo cuando se interrumpa el programa
