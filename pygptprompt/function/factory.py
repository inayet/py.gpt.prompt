"""
pygptprompt/function/factory.py
"""
import copy
import json
from typing import Any, List, Optional

from llama_cpp import ChatCompletionMessage

from pygptprompt import logging
from pygptprompt.api.factory import ChatModel
from pygptprompt.api.types import ExtendedChatCompletionMessage
from pygptprompt.config.manager import ConfigurationManager
from pygptprompt.function.weather import get_current_weather


class FunctionFactory:
    def __init__(self, config: ConfigurationManager):
        """
        Initialize the FunctionFactory.

        Args:
            config (ConfigurationManager): The configuration manager instance.
        """
        self.config = config
        self.functions: dict[str, object] = {
            "get_current_weather": get_current_weather,
            # Add more functions here as needed
        }
        self.function_name: str = ""
        self.function_args: dict[str, Any] = {}
        self.function: Optional[object] = None

    def get_function_args(
        self, message: ExtendedChatCompletionMessage
    ) -> dict[str, Any]:
        """
        Extract and return the function arguments from the message.

        Args:
            message (ExtendedChatCompletionMessage): The chat completion message.

        Returns:
            dict[str, Any]: A dictionary containing the function arguments. If the function arguments in the message are not valid JSON, prints an error message and returns an empty dictionary.
        """
        function_args = message.get("function_args")
        if function_args is None:
            logging.error(f"Function arguments is None: {self.function_name}")
            return {}

        try:
            self.function_args = json.loads(function_args)
            return self.function_args
        except json.JSONDecodeError:
            logging.error(f"Invalid function arguments: {function_args}")
            return {}

    def get_function(self, message: ExtendedChatCompletionMessage) -> Optional[object]:
        """
        Get the function specified in the message.

        Args:
            message (ExtendedChatCompletionMessage): The chat completion message.

        Returns:
            Optional[object]: The function specified in the message or None if it doesn't exist.
        """
        self.function_name = message.get("function_call")
        self.function = self.functions.get(self.function_name)
        return self.function

    def register_function(self, function_name: str, function: object) -> None:
        """
        Register a new function with the FunctionFactory.

        Args:
            function_name (str): The name of the function to register.
            function (object): The function object to register.
        """
        self.functions[function_name] = function

    def execute_function(
        self, message: ExtendedChatCompletionMessage
    ) -> Optional[ChatCompletionMessage]:
        """
        Execute the specified function based on the given message.

        Args:
            message (ExtendedChatCompletionMessage): The chat completion message.

        Returns:
            Optional[ChatCompletionMessage]: The result of the function execution as a ChatCompletionMessage, or None if an error occurs.
        """
        # Get the function from the factory
        function = self.get_function(message)
        if function is None:
            logging.error(f"Function {message['function_call']} not found.")
            return None

        # Extract the function arguments
        function_args = self.get_function_args(message)
        if not function_args:
            logging.error(f"Invalid function arguments for {message['function_call']}.")
            return None

        try:
            # Call the function
            result = function(**function_args)
        except Exception as e:
            logging.error(f"Error executing function {message['function_call']}: {e}")
            return None

        # Return a new ChatCompletionMessage with the result
        return ChatCompletionMessage(role="assistant", content=result)

    def query_function(
        self,
        model: ChatModel,
        result: ChatCompletionMessage,
        messages: List[ChatCompletionMessage],
    ) -> Optional[ChatCompletionMessage]:
        """
        Query the language model with the results of the function execution.

        Args:
            model (ChatModel): The language model used for chat completions.
            result (ChatCompletionMessage): The result of the executed function.
            messages (List[ChatCompletionMessage]): List of chat completion messages.

        Returns:
            Optional[ChatCompletionMessage]: The generated chat completion message, or None if an error occurs.
        """
        if result is None:
            return None

        shadow_messages = copy.deepcopy(messages)
        shadow_messages.append(result)
        prompt_templates: list[dict[str, str]] = self.config.get_value(
            "function.templates", []
        )

        prompt_template: str = ""

        for template in prompt_templates:
            if template.get("name", "") == self.function_name:
                prompt_template = template.get("prompt", "")

        if not prompt_template:
            logging.error(
                f"Failed to retrieve prompt template for {self.function_name}"
            )
            return None

        prompt_message = ChatCompletionMessage(role="user", content=prompt_template)
        shadow_messages.append(prompt_message)
        message = model.get_chat_completions(messages=shadow_messages)
        return message