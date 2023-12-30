import base64
from abc import ABC, abstractmethod
from typing import (Any, Awaitable, Callable, Dict, Generator, Generic, List,
                    Optional, Sequence, Tuple, TypeVar, Union, cast)

import pandas as pd
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

T = TypeVar('T')


async def awaitable_none(a: 'AstNode') -> None:
    pass


def none(a: 'AstNode') -> None:
    pass


class Visitor(ABC):
    @abstractmethod
    def visit(self, node: 'AstNode') -> 'AstNode':
        pass


class Executor(ABC):
    @abstractmethod
    async def aexecute(
        self,
        messages: List['Message'],
        max_completion_tokens: int = 2048,
        temperature: float = 1.0,
        stream_handler: Optional[Callable[['AstNode'], Awaitable[None]]] = None,
        model: Optional[str] = None,
        template_args: Optional[Dict[str, Any]] = None,
    ) -> 'Assistant':
        pass

    @abstractmethod
    def execute(
        self,
        messages: List['Message'],
        max_completion_tokens: int = 2048,
        temperature: float = 1.0,
        stream_handler: Optional[Callable[['AstNode'], None]] = None,
        model: Optional[str] = None,
        template_args: Optional[Dict[str, Any]] = None,
    ) -> 'Assistant':
        pass

    @abstractmethod
    def set_default_max_tokens(
        self,
        default_max_tokens: int,
    ):
        pass

    @abstractmethod
    def set_default_model(
        self,
        default_model: str,
    ):
        pass

    @abstractmethod
    def get_default_model(
        self,
    ) -> str:
        pass

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def max_tokens(self, model: Optional[str]) -> int:
        pass

    @abstractmethod
    def max_prompt_tokens(
        self,
        completion_token_count: int = 2048,
        model: Optional[str] = None,
    ) -> int:
        pass

    @abstractmethod
    def calculate_tokens(
        self,
        messages: List['Message'] | str,
        extra_str: str = '',
        model: Optional[str] = None,
    ) -> int:
        pass

    @abstractmethod
    def user_token(
        self
    ) -> str:
        pass

    @abstractmethod
    def assistant_token(
        self
    ) -> str:
        pass

    @abstractmethod
    def append_token(
        self
    ) -> str:
        pass

def coerce_types(a, b):
    # Function to check if a string can be converted to an integer or a float
    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    # If either operand is a string and represents a number, convert it
    if isinstance(a, str) and is_number(a):
        a = int(a) if '.' not in a else float(a)
    if isinstance(b, str) and is_number(b):
        b = int(b) if '.' not in b else float(b)

    # If either operand is a string now, convert both to strings
    if isinstance(a, str) or isinstance(b, str):
        return str(a), str(b)

    # If they are of the same type, return them as-is
    if type(a) is type(b):
        return a, b

    # If one is a float and the other an int, convert the int to float
    if isinstance(a, float) and isinstance(b, int):
        return a, float(b)
    if isinstance(b, float) and isinstance(a, int):
        return float(a), b

    raise TypeError(f"Cannot coerce types {type(a)} and {type(b)} to a common type")


class Controller():
    def __init__(
        self,
    ):
        pass

    @abstractmethod
    def aexecute_llm_call(
        self,
        message: 'Message',
        context_messages: List['Message'],
        query: str,
        original_query: str,
        prompt_filename: Optional[str] = None,
        completion_tokens: int = 2048,
        temperature: float = 0.0,
        lifo: bool = False,
        stream_handler: Optional[Callable[['AstNode'], Awaitable[None]]] = awaitable_none,
        model: Optional[str] = None,
    ) -> 'Assistant':
        pass

    @abstractmethod
    def execute_llm_call(
        self,
        message: 'Message',
        context_messages: List['Message'],
        query: str,
        original_query: str,
        prompt_filename: Optional[str] = None,
        completion_tokens: int = 2048,
        temperature: float = 0.0,
        lifo: bool = False,
        stream_handler: Optional[Callable[['AstNode'], Awaitable[None]]] = awaitable_none,
        model: Optional[str] = None,
    ) -> 'Assistant':
        pass

    @abstractmethod
    def get_executor() -> Executor:
        pass


class AstNode(ABC):
    def __init__(
        self
    ):
        pass

    def accept(self, visitor: Visitor) -> 'AstNode':
        return visitor.visit(self)


class TokenStopNode(AstNode):
    def __init__(
        self,
    ):
        super().__init__()

    def __str__(self):
        return '\n'

    def __repr__(self):
        return 'TokenStopNode()'


class StopNode(AstNode):
    def __init__(
        self,
    ):
        super().__init__()

    def __str__(self):
        return 'StopNode'

    def __repr__(self):
        return 'StopNode()'


class StreamNode(AstNode):
    def __init__(
        self,
        obj: object,
        type: str,
        metadata: object = None,
    ):
        super().__init__()
        self.obj = obj
        self.type = type
        self.metadata = metadata

    def __str__(self):
        return 'StreamNode'

    def __repr__(self):
        return 'StreamNode()'


class DebugNode(AstNode):
    def __init__(
        self,
        debug_str: str,
    ):
        super().__init__()
        self.debug_str = debug_str

    def __str__(self):
        return 'DebugNode'

    def __repr__(self):
        return 'DebugNode()'


class Content(AstNode):
    def __init__(
        self,
        sequence: Optional[AstNode | List[AstNode] | str | bytes | Any] = None,
        content_type: str = 'text',
        url: str = '',
    ):
        if sequence is None:
            self.sequence = ''
            return

        self.content_type = content_type
        self.url = url

        if isinstance(sequence, str):
            self.sequence = [sequence]
        elif isinstance(sequence, bytes):
            self.sequence = sequence
        elif isinstance(sequence, Content):
            self.sequence = sequence.sequence  # type: ignore
        elif isinstance(sequence, AstNode):
            self.sequence = [sequence]
        elif isinstance(sequence, list) and len(sequence) > 0 and isinstance(sequence[0], AstNode):
            self.sequence = sequence
        elif (
            isinstance(sequence, list)
            and len(sequence) > 0
            and isinstance(sequence[0], dict)
            and 'type' in sequence[0]
            and sequence[0]['type'] == 'image_url'
        ):
            base = sequence[0]['image_url']['url'].split(',')[1]
            self.sequence = base64.b64decode(base)  # bytes
        else:
            raise ValueError(f'type {type(sequence)} is not supported')

    def __str__(self):
        if isinstance(self.sequence, list):
            return ' '.join([str(n) for n in self.sequence])
        else:
            return str(self.sequence)

    def __repr__(self):
        return f'Content({self.sequence})'

    def b64encode(self) -> str:
        if isinstance(self.sequence, bytes):
            return base64.b64encode(self.sequence).decode('utf-8')
        raise ValueError('sequence is not bytes')

    @staticmethod
    def decode(base64_str: str):
        return base64.b64decode(base64_str)


class ImageContent(Content):
    def __init__(
        self,
        sequence: bytes,
        url: str = '',
    ):
        super().__init__(sequence, 'image', url)
        self.sequence = sequence


class PdfContent(Content):
    def __init__(
        self,
        sequence: bytes,
        url: str = '',
    ):
        super().__init__(sequence, 'pdf', url)
        self.sequence = sequence


class FileContent(Content):
    def __init__(
        self,
        sequence: bytes,
        url: str = '',
    ):
        super().__init__(sequence, 'file', url)
        self.sequence = sequence


class Message(AstNode):
    def __init__(
        self,
        message: Content,
    ):
        self.message: Content = message

    @abstractmethod
    def role(self) -> str:
        pass

    @staticmethod
    def from_dict(message: Dict[str, Any]) -> 'Message':
        role = message['role']
        message_content = message['content']

        # this can be from a MessageModel, which has a url and content_type
        # or from the LLM, which doesn't.
        url = message['url'] if 'url' in message else ''
        content_type = message['content_type'] if 'content_type' in message else ''

        content = Content(message_content)

        # when converting from MessageModel, there can be an embedded image
        # in the content parameter that needs to be converted back to bytes
        if (
            isinstance(message_content, list)
            and len(message_content) > 0
            and 'type' in message_content[0]
            and message_content[0]['type'] == 'image_url'
            and 'image_url' in message_content[0]
            and 'url' in message_content[0]['image_url']
        ):
            byte_content = base64.b64decode(message_content[0]['image_url']['url'].split(',')[1])
            content = ImageContent(byte_content, message_content[0]['image_url']['url'])

        # todo: pdf parsing here
        if role == 'user' and content_type == 'file':
            return User(FileContent(FileContent.decode(str(message_content)), url))
        if role == 'user':
            return User(content)
        elif role == 'system':
            return System(content)
        elif role == 'assistant':
            return Assistant(content)
        raise ValueError('role not found supported')

    def __getitem__(self, key):
        return {'role': self.role(), 'content': self.message}

    @staticmethod
    def to_dict(message: 'Message', add_metadata: bool = False) -> Dict[str, Any]:
        # primarily to pass to Anthropic or OpenAI api
        if isinstance(message, User) and isinstance(message.message, ImageContent):
            return {
                'role': message.role(),
                'content': [{
                    'type': 'image_url',
                    'image_url': {
                        'url': f"data:image/jpeg;base64,{base64.b64encode(message.message.sequence).decode('utf-8')}",
                        'detail': 'high'
                    }
                }],
                **({'url': message.message.url} if add_metadata else {}),
                **({'content_type': 'image'} if add_metadata else {})
            }
        elif isinstance(message, User) and isinstance(message.message, PdfContent):
            raise ValueError('pdf not supported')
        elif isinstance(message, User) and isinstance(message.message, FileContent):
            return {
                'role': message.role(),
                'content': message.message.b64encode(),
                **({'url': message.message.url} if add_metadata else {}),
                **({'content_type': 'file'} if add_metadata else {})
            }
        else:
            return {
                'role': message.role(),
                'content': str(message.message),
                **({'url': message.message.url} if add_metadata else {}),
                **({'content_type': ''} if add_metadata else {})
            }


class User(Message):
    def __init__(
        self,
        message: Content
    ):
        super().__init__(message)

    def role(self) -> str:
        return 'user'

    def __str__(self):
        return str(self.message)

    def __repr__(self):
        return f'Message({self.message})'


class System(Message):
    def __init__(
        self,
        message: Content = Content('''
            You are a helpful assistant.
            Dont make assumptions about what values to plug into functions.
            Ask for clarification if a user request is ambiguous.
        ''')
    ):
        super().__init__(Content(message))

    def role(self) -> str:
        return 'system'

    def __str__(self):
        return str(self.message)

    def __repr__(self):
        return f'SystemPrompt({self.message})'


class Assistant(Message):
    def __init__(
        self,
        message: Content,
        error: bool = False,
        messages_context: List[Message] = [],
        system_context: object = None,
        llm_call_context: object = None,
    ):
        super().__init__(message)
        self.error = error
        self._llm_call_context: object = llm_call_context
        self._system_context = system_context,
        self._messages_context: List[Message] = messages_context

    def role(self) -> str:
        return 'assistant'

    def __str__(self):
        return f'{self.message}'

    def __add__(self, other):
        other_message = str(other)

        assistant = Assistant(
            message=Content(str(self.message) + other_message),
            messages_context=self._messages_context,
            system_context=self._system_context,
            llm_call_context=self._llm_call_context,
        )
        return assistant

    def __repr__(self):
        return f'Assistant({self.message} {self.error})'


class Statement(AstNode):
    def __init__(
        self,
        ast_text: Optional[str] = None,
    ):
        self._result: object = None
        self._ast_text: Optional[str] = ast_text

    def __str__(self):
        if self._result:
            return str(self._result)
        else:
            return str(type(self))

    def result(self):
        return self._result

    def token(self):
        return 'statement'


class DataFrame(Statement):
    def __init__(
        self,
        elements: List,
        ast_text: Optional[str] = None,
    ):
        super().__init__(ast_text)
        self.elements = elements

    def token(self):
        return 'dataframe'


class Call(Statement):
    def __init__(
        self,
        ast_text: Optional[str] = None,
    ):
        super().__init__(ast_text)


class FunctionCallMeta(Call):
    def __init__(
        self,
        callsite: str,
        func: Callable,
        result: object,
        lineno: Optional[int],
    ):
        self.callsite = callsite
        self.func = func
        self._result = result
        self.lineno = lineno

    def result(self) -> object:
        return self._result

    def token(self):
        return 'functioncallmeta'

    def __getattr__(self, name):
        return getattr(self._result, name)

    def __str__(self):
        return str(self._result)

    def __add__(self, other):
        a, b = coerce_types(self._result, other)
        return a + b  # type: ignore

    def __sub__(self, other):
        a, b = coerce_types(self._result, other)
        return a - b  # type: ignore

    def __mul__(self, other):
        a, b = coerce_types(self._result, other)
        return a * b  # type: ignore

    def __div__(self, other):
        a, b = coerce_types(self._result, other)
        return a / b  # type: ignore

    def __truediv__(self, other):
        a, b = coerce_types(self._result, other)
        return a / b  # type: ignore

    def __rtruediv__(self, other):
        a, b = coerce_types(other, self._result)
        return a / b  # type: ignore

    def __radd__(self, other):
        a, b = coerce_types(other, self._result)
        return a + b  # type: ignore

    def __rsub__(self, other):
        a, b = coerce_types(other, self._result)
        return a - b  # type: ignore

    def __rmul__(self, other):
        a, b = coerce_types(other, self._result)
        return a * b  # type: ignore

    def __rdiv__(self, other):
        a, b = coerce_types(other, self._result)
        return a / b  # type: ignore

    def __gt__(self, other):
        a, b = coerce_types(self._result, other)
        return a > b  # type: ignore

    def __lt__(self, other):
        a, b = coerce_types(self._result, other)
        return a < b  # type: ignore

    def __ge__(self, other):
        a, b = coerce_types(self._result, other)
        return a >= b  # type: ignore

    def __le__(self, other):
        a, b = coerce_types(self._result, other)
        return a <= b  # type: ignore

    def __rgt__(self, other):
        # Note the order in coerce_types is reversed
        a, b = coerce_types(other, self._result)
        return a > b  # type: ignore

    def __rlt__(self, other):
        a, b = coerce_types(other, self._result)
        return a < b  # type: ignore

    def __rge__(self, other):
        a, b = coerce_types(other, self._result)
        return a >= b  # type: ignore

    def __rle__(self, other):
        a, b = coerce_types(other, self._result)
        return a <= b  # type: ignore

    def __format__(self, format_spec):
        return format(self._result, format_spec)

class PandasMeta(Call):
    def __init__(
        self,
        expr_str: str,
        pandas_df: pd.DataFrame,
    ):
        self.expr_str = expr_str
        self.df = pandas_df

    def result(self) -> object:
        return self._result

    def token(self):
        return 'pandasmeta'

    def __str__(self):
        return str(self.df)

    def ask(self, *args, **kwargs) -> object:
        self._result = self.df.ask(*args, **kwargs)  # type: ignore
        return self._result


class FunctionCall(Call):
    def __init__(
        self,
        name: str,
        args: List[Dict[str, object]],
        types: List[Dict[str, object]],
        context: Content = Content(),
        func: Optional[Callable] = None,
        ast_text: Optional[str] = None,
    ):
        super().__init__(ast_text)
        self.name = name
        self.args = args
        self.types = types
        self.context = context
        self._result: Optional[Content] = None
        self.func: Optional[Callable] = func

    def to_code_call(self):
        arguments = []
        for arg in self.args:
            for k, v in arg.items():
                arguments.append(v)

        str_args = ', '.join([str(arg) for arg in arguments])
        return f'{self.name}({str_args})'

    def to_definition(self):
        definitions = []
        for arg in self.types:
            for k, v in arg.items():
                definitions.append(f'{k}: {v}')

        str_args = ', '.join([str(t) for t in definitions])
        return f'{self.name}({str_args})'

    def token(self):
        return 'function_call'

class Answer(Statement):
    def __init__(
        self,
        conversation: List[Message] = [],
        result: object = None,
        error: object = None,
        ast_text: Optional[str] = None,
    ):
        super().__init__(ast_text)
        self.conversation: List[Message] = conversation
        self._result = result
        self.error = error

    def __str__(self):
        ret_result = f'Answer({self.result})\n'
        ret_result = f'Error: {self.error}\n'
        ret_result += '  Conversation:\n'
        ret_result += '\n  '.join([str(n) for n in self.conversation])
        return ret_result

    def token(self):
        return 'answer'


class UncertainOrError(Statement):
    def __init__(
        self,
        error_message: Content,
        supporting_conversation: List[AstNode] = [],
        supporting_result: object = None,
        supporting_error: object = None,
    ):
        super().__init__()
        self.error_message = error_message,
        self.supporting_conversation = supporting_conversation
        self._result = supporting_result
        self.supporting_error = supporting_error

    def __str__(self):
        ret_result = f'UncertainOrError({str(self.error_message)} {self.supporting_error}, {self.result})\n'
        ret_result += '  Conversation:\n'
        ret_result += '\n  '.join([str(n) for n in self.supporting_conversation])
        return ret_result

    def token(self):
        return 'uncertain_or_error'


class DownloadItem(BaseModel):
    id: int
    url: str


class MessageModel(BaseModel):
    role: str
    content_type: Optional[str] = None
    content: str | List[Dict[str, Any]]
    url: Optional[str] = None

    def to_message(self) -> Message:
        return Message.from_dict(self.model_dump())

    @staticmethod
    def from_message(message: Message) -> 'MessageModel':
        return MessageModel(**Message.to_dict(message, True))


class SessionThread(BaseModel):
    id: int = -1
    executor: str = ''
    model: str = ''
    current_mode: str = 'tool'
    temperature: float = 0.0
    cookies: List[Dict[str, Any]] = []
    messages: List[MessageModel] = []


class Response(BaseModel):
    def __init__(
        self,
        thread: Optional[SessionThread] = None,
        stream: Optional[StreamingResponse] = None,
    ):
        super().__init__()
        self.thread = thread
        self.response = stream
