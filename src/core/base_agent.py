"""Base agent class and workflow management for AI Scrum Master."""

from typing import Any, Callable, List, Optional, TypeVar, Generic
from abc import ABC, abstractmethod
import logging
from dataclasses import dataclass, field
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class StepResult:
    """Result of a workflow step execution."""
    success: bool
    data: Any
    error: Optional[Exception] = None
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class WorkflowStep(Generic[T, R]):
    """A single step in a workflow pipeline."""
    
    def __init__(self, 
                 name: str,
                 func: Callable[[T], R],
                 error_handler: Optional[Callable[[Exception, T], R]] = None):
        """
        Initialize a workflow step.
        
        Args:
            name: Step name for logging and debugging
            func: Function to execute
            error_handler: Optional error handler function
        """
        self.name = name
        self.func = func
        self.error_handler = error_handler
    
    def execute(self, input_data: T) -> StepResult:
        """
        Execute the step with error handling.
        
        Args:
            input_data: Input data for the step
            
        Returns:
            StepResult with execution details
        """
        start_time = datetime.utcnow()
        try:
            result = self.func(input_data)
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info(f"Step '{self.name}' completed successfully",
                       extra={"duration_ms": duration_ms})
            
            return StepResult(
                success=True,
                data=result,
                duration_ms=duration_ms
            )
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.error(f"Step '{self.name}' failed: {str(e)}",
                        extra={"duration_ms": duration_ms, 
                              "error": str(e),
                              "traceback": traceback.format_exc()})
            
            if self.error_handler:
                try:
                    fallback_result = self.error_handler(e, input_data)
                    return StepResult(
                        success=False,
                        data=fallback_result,
                        error=e,
                        duration_ms=duration_ms
                    )
                except Exception as handler_error:
                    logger.error(f"Error handler for step '{self.name}' also failed: {str(handler_error)}")
                    return StepResult(
                        success=False,
                        data=None,
                        error=handler_error,
                        duration_ms=duration_ms
                    )
            
            return StepResult(
                success=False,
                data=None,
                error=e,
                duration_ms=duration_ms
            )


class Workflow:
    """Manages a sequence of processing steps."""
    
    def __init__(self, name: str = "Workflow"):
        """Initialize an empty workflow."""
        self.name = name
        self.steps: List[WorkflowStep] = []
        self.execution_history: List[StepResult] = []
    
    def add_step(self, 
                 step: Callable,
                 name: Optional[str] = None,
                 error_handler: Optional[Callable] = None) -> 'Workflow':
        """
        Add a step to the workflow.
        
        Args:
            step: Callable function for the step
            name: Optional name for the step
            error_handler: Optional error handler
            
        Returns:
            Self for method chaining
        """
        step_name = name or step.__name__
        workflow_step = WorkflowStep(step_name, step, error_handler)
        self.steps.append(workflow_step)
        return self
    
    def execute(self, initial_input: Any) -> Any:
        """
        Execute the workflow on given input.
        
        Args:
            initial_input: Initial input data
            
        Returns:
            Final result after all steps
            
        Raises:
            Exception: If any step fails without error handler
        """
        logger.info(f"Starting workflow '{self.name}' with {len(self.steps)} steps")
        
        self.execution_history.clear()
        result = initial_input
        
        for i, step in enumerate(self.steps, 1):
            logger.info(f"Executing step {i}/{len(self.steps)}: {step.name}")
            
            step_result = step.execute(result)
            self.execution_history.append(step_result)
            
            if not step_result.success and step_result.data is None:
                # Step failed with no fallback
                logger.error(f"Workflow '{self.name}' failed at step '{step.name}'")
                raise step_result.error or Exception(f"Step '{step.name}' failed")
            
            result = step_result.data
            
        logger.info(f"Workflow '{self.name}' completed successfully")
        return result
    
    def get_execution_summary(self) -> dict:
        """Get summary of the last execution."""
        if not self.execution_history:
            return {"status": "not_executed"}
        
        total_duration = sum(step.duration_ms for step in self.execution_history)
        failed_steps = [step for step in self.execution_history if not step.success]
        
        return {
            "status": "failed" if failed_steps else "success",
            "total_duration_ms": total_duration,
            "steps_executed": len(self.execution_history),
            "steps_failed": len(failed_steps),
            "failed_step_names": [self.steps[i].name for i, step in enumerate(self.execution_history) if not step.success]
        }


class BaseAgent(ABC):
    """Base agent class for AI Scrum Master agents."""
    
    def __init__(self, name: str, **kwargs):
        """
        Initialize base agent.
        
        Args:
            name: Agent name
            **kwargs: Additional configuration
        """
        self.name = name
        self._workflow = Workflow(name=f"{name}_workflow")
        self.config = kwargs
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
        # Initialize the agent
        self._initialize()
        
    @abstractmethod
    def _initialize(self):
        """Initialize agent-specific components."""
        pass
    
    def add_step(self, 
                 step: Callable,
                 name: Optional[str] = None,
                 error_handler: Optional[Callable] = None) -> 'BaseAgent':
        """
        Add a step to the agent's workflow.
        
        Args:
            step: Callable function
            name: Optional step name
            error_handler: Optional error handler
            
        Returns:
            Self for method chaining
        """
        self._workflow.add_step(step, name, error_handler)
        return self
    
    def execute(self, task: Any) -> Any:
        """
        Execute the agent's workflow.
        
        Args:
            task: Input task
            
        Returns:
            Processed result
        """
        self.logger.info(f"Agent '{self.name}' starting execution")
        
        try:
            result = self._workflow.execute(task)
            
            # Log execution summary
            summary = self._workflow.get_execution_summary()
            self.logger.info(f"Agent '{self.name}' execution completed", 
                           extra={"summary": summary})
            
            return result
            
        except Exception as e:
            self.logger.error(f"Agent '{self.name}' execution failed: {str(e)}", 
                            exc_info=True)
            raise
    
    def get_info(self) -> dict:
        """Get agent information."""
        return {
            "name": self.name,
            "workflow_steps": [step.name for step in self._workflow.steps],
            "config": self.config
        }


class AgentRegistry:
    """Registry for agent discovery and management."""
    
    _agents = {}
    
    @classmethod
    def register(cls, agent_class: type) -> type:
        """
        Decorator to register an agent class.
        
        Args:
            agent_class: Agent class to register
            
        Returns:
            The agent class (for decorator chaining)
        """
        cls._agents[agent_class.__name__] = agent_class
        logger.info(f"Registered agent: {agent_class.__name__}")
        return agent_class
    
    @classmethod
    def get_agent(cls, name: str) -> Optional[type]:
        """
        Get registered agent class by name.
        
        Args:
            name: Agent class name
            
        Returns:
            Agent class or None
        """
        return cls._agents.get(name)
    
    @classmethod
    def list_agents(cls) -> List[str]:
        """List all registered agent names."""
        return list(cls._agents.keys())
    
    @classmethod
    def create_agent(cls, name: str, **kwargs) -> Optional[BaseAgent]:
        """
        Create an instance of a registered agent.
        
        Args:
            name: Agent class name
            **kwargs: Arguments for agent initialization
            
        Returns:
            Agent instance or None
        """
        agent_class = cls.get_agent(name)
        if agent_class:
            return agent_class(**kwargs)
        return None