from abc import ABC, abstractmethod


class TaskHandlerInterface(ABC):
    """Interface that defines the common methods for task handlers."""
    
    @abstractmethod
    def config(self):
        """Method to configure the task handler with the provided task definition.
        """
        pass
    
    @abstractmethod
    def run_task(self, **kwargs) -> bool:
        """Method to run the task.

        Args:
            kwargs: Optional keyword arguments passed to the task.

        Returns:
            bool: True if the task is launched successfully, False otherwise.
        """
        pass
    
