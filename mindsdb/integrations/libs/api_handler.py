from typing import Any
import ast as py_ast

import pandas as pd
from mindsdb_sql.parser.ast import ASTNode, Select, Insert, Update, Delete
from mindsdb_sql.parser.ast.select.identifier import Identifier

from mindsdb.integrations.libs.base import BaseHandler

from mindsdb.integrations.libs.response import (
    HandlerResponse as Response,
    RESPONSE_TYPE
)


class FuncParser:

    def from_string(self, query_string):

        body = py_ast.parse(query_string.strip(), mode='eval').body

        if not isinstance(body, py_ast.Call):
            raise RuntimeError(f'Api function not found {query_string}')

        fnc_name = body.func.id

        params = {}
        for keyword in body.keywords:
            name = keyword.arg
            value = self.process(keyword.value)

            params[name] = value

        return fnc_name, params

    def process(self, node):

        if isinstance(node, py_ast.List):
            elements = []
            for node2 in node.elts:
                elements.append(self.process(node2))
            return elements

        if isinstance(node, py_ast.Dict):

            keys = []
            for node2 in node.keys:
                if isinstance(node2, py_ast.Constant):
                    value = node2.value
                elif isinstance(node2, py_ast.Str):  # py37
                    value = node2.s
                else:
                    raise NotImplementedError(f'Unknown dict key {node2}')

                keys.append(value)

            values = []
            for node2 in node.values:
                values.append(self.process(node2))

            return dict(zip(keys, values))

        if isinstance(node, py_ast.Name):
            # special attributes
            name = node.id
            if name == 'true':
                return True
            elif name == 'false':
                return False
            elif name == 'null':
                return None

        if isinstance(node, py_ast.Constant):
            return node.value

        # ---- python 3.7 objects -----
        if isinstance(node, py_ast.Str):
            return node.s

        if isinstance(node, py_ast.Num):
            return node.n

        # -----------------------------

        if isinstance(node, py_ast.UnaryOp):
            if isinstance(node.op, py_ast.USub):
                value = self.process(node.operand)
                return -value

        raise NotImplementedError(f'Unknown node {node}')


class APITable():

    def __init__(self, handler):
        self.handler = handler

    def select(self, query: ASTNode) -> pd.DataFrame:
        """Receive query as AST (abstract syntax tree) and act upon it.

        Args:
            query (ASTNode): sql query represented as AST. Usually it should be ast.Select

        Returns:
            HandlerResponse
        """
        raise NotImplementedError()

    def insert(self, query: ASTNode) -> None:
        """Receive query as AST (abstract syntax tree) and act upon it somehow.

        Args:
            query (ASTNode): sql query represented as AST. Usually it should be ast.Insert

        Returns:
            None
        """
        raise NotImplementedError()

    def update(self, query: ASTNode) -> None:
        """Receive query as AST (abstract syntax tree) and act upon it somehow.

        Args:
            query (ASTNode): sql query represented as AST. Usually it should be ast.Update
        Returns:
            None
        """
        raise NotImplementedError()

    def delete(self, query: ASTNode) -> None:
        """Receive query as AST (abstract syntax tree) and act upon it somehow.

        Args:
            query (ASTNode): sql query represented as AST. Usually it should be ast.Delete

        Returns:
            None
        """
        raise NotImplementedError()

    def get_columns(self) -> list:
        """Maps the columns names from the API call resource

        Returns:
            List
        """
        raise NotImplementedError()


class APIHandler(BaseHandler):
    """
    Base class for handlers associated to the applications APIs (e.g. twitter, slack, discord  etc.)
    """

    def __init__(self, name: str):
        super().__init__(name)
        """ constructor
        Args:
            name (str): the handler name
        """

        self._tables = {}

    def _register_table(self, table_name: str, table_class: Any):
        """
        Register the data resource. For e.g if you are using Twitter API it registers the `tweets` resource from `/api/v2/tweets`.
        """
        self._tables[table_name] = table_class

    def _get_table(self, name: Identifier):
        """
        Check if the table name was added to the the _register_table
        Args:
            name (Identifier): the table name
        """
        name = name.parts[-1]
        if name not in self._tables:
            raise RuntimeError(f'Table not found: {name}')
        return self._tables[name]

    def query(self, query: ASTNode):

        if isinstance(query, Select):
            result = self._get_table(query.from_table).select(query)
        elif isinstance(query, Update):
            result = self._get_table(query.table).update(query)
        elif isinstance(query, Insert):
            result = self._get_table(query.table).insert(query)
        elif isinstance(query, Delete):
            result = self._get_table(query.table).delete(query)
        else:
            raise NotImplementedError

        if result is None:
            return Response(RESPONSE_TYPE.OK)
        elif isinstance(result, pd.DataFrame):
            return Response(RESPONSE_TYPE.TABLE, result)
        else:
            raise NotImplementedError

    def get_columns(self, table_name: str) -> Response:
        """
        Returns a list of entity columns
        Args:
            table_name (str): the table name
        Returns:
            RESPONSE_TYPE.TABLE
        """

        result = self._get_table(Identifier(table_name)).get_columns()

        df = pd.DataFrame(result, columns=['Field'])
        df['Type'] = 'str'

        return Response(RESPONSE_TYPE.TABLE, df)

    def get_tables(self) -> Response:
        """
        Return list of entities
        Returns:
            RESPONSE_TYPE.TABLE
        """
        result = list(self._tables.keys())

        df = pd.DataFrame(result, columns=['table_name'])
        df['table_type'] = 'BASE TABLE'

        return Response(RESPONSE_TYPE.TABLE, df)


class APIChatHandler(APIHandler):

    def get_chat_config(self):
        """Return configuration to connect to chatbot

        Returns:
            Dict
        """
        raise NotImplementedError()

    def get_my_user_name(self) -> list:
        """Return configuration to connect to chatbot

        Returns:
            Dict
        """
        raise NotImplementedError()
