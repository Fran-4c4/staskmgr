import logging
import inspect

class CustomLogger(logging.Logger):
    
    exclude_methods=None

    def set_exclude_methods(self,exclude_methods):
        self.exclude_methods=exclude_methods    
        
    def findCaller(self, stack_info=False, stacklevel=1):
        frame = inspect.currentframe()
        for _ in range(3):
            if frame:
                frame = frame.f_back

        # Recorremos la pila hasta encontrar un marco relevante (que no sea de BaseResource)
        if self.exclude_methods:
            while frame:
                # Si no estamos en las funciones de la clase base, devolvemos el marco actual
                if frame.f_code.co_name not in self.exclude_methods:
                    break
                frame = frame.f_back
        
        # Si frame es None (en caso de que todas las funciones se salten), volvemos al comportamiento predeterminado
        if not frame:
            frame = inspect.currentframe().f_back

        co = frame.f_code
        filename = co.co_filename
        lineno = frame.f_lineno
        func_name = co.co_name
        return (filename, lineno, func_name, None)

# Reemplazamos el logger por defecto con nuestro CustomLogger
# logging.setLoggerClass(CustomLogger)

# Configuramos el logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s -  %(levelname)s - %(name)s-%(funcName)s.%(lineno)d - %(message)s')
